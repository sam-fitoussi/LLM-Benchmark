"""Campaign runner: python -m bench.runner <experiment> [--cap USD] [--workers N]"""
import argparse
import glob
import json
import os
import sys
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

from .llm import Budget, CallLogger
from .match import play_match

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, "runs")


def total_spent():
    """Global spend across every run, from the call logs (plain or gzipped)."""
    import gzip
    s = 0.0
    paths = glob.glob(os.path.join(RUNS, "*", "calls.jsonl")) + glob.glob(os.path.join(RUNS, "*", "calls.jsonl.gz"))
    extra = os.path.join(RUNS, "unlogged_spend.json")
    if os.path.exists(extra):
        s += json.load(open(extra))["usd"]
    for p in paths:
        with (gzip.open(p, "rt") if p.endswith(".gz") else open(p)) as f:
            for line in f:
                try:
                    s += json.loads(line).get("cost", 0) or 0
                except json.JSONDecodeError:
                    pass
    return s


def scripted_tasks(experiment, models, opponents, label_pairs, Xs, seeds, sides=(1, 2)):
    tasks = []
    for m in models:
        for opp in opponents:
            for lp in label_pairs:
                for side in sides:
                    for X in Xs:
                        for s in seeds:
                            llm, bot = ("llm", m), ("scripted", opp)
                            p1, p2 = (llm, bot) if side == 1 else (bot, llm)
                            cond = f"{m}|vs:{opp}|{lp}|side{side}|X{X}"
                            tasks.append(dict(p1_spec=p1, p2_spec=p2, label_pair=lp, X=X, seed=s,
                                              condition=cond, experiment=experiment))
    return tasks


def llm_tasks(experiment, pairs, label_pairs, Xs, seeds):
    tasks = []
    for m1, m2 in pairs:
        for lp in label_pairs:
            for X in Xs:
                for s in seeds:
                    cond = f"{m1}|vs:{m2}|{lp}|X{X}"
                    tasks.append(dict(p1_spec=("llm", m1), p2_spec=("llm", m2), label_pair=lp, X=X, seed=s,
                                      condition=cond, experiment=experiment))
    return tasks


ALL_LABELS = ["abstract", "usa_china", "usa_russia", "india_pakistan", "israel_iran", "norway_sweden"]


def build(experiment):
    if experiment == "pilot":
        ms = ["claude-sonnet-5.5", "gpt-6.1-terra", "grok-4.3", "grok-4.7"]
        t = scripted_tasks(experiment, ms, ["hawk"], ["usa_china"], [-200], [0, 1])
        t += scripted_tasks(experiment, ms, ["bluffer", "tft"], ["abstract"], [-200], [0], sides=(1,))
        t += llm_tasks(experiment, [("claude-sonnet-5.5", "gpt-6.1-terra"), ("grok-4.3", "grok-4.3")],
                       ["usa_china"], [-200], [0])
        return t
    raise SystemExit(f"unknown experiment {experiment}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("experiment")
    ap.add_argument("--cap", type=float, default=15.0, help="global budget cap in USD (all runs)")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    from . import experiments  # noqa: F401  (registers extra experiments)
    tasks = experiments.build(args.experiment) if hasattr(experiments, "build") else None
    if tasks is None:
        tasks = build(args.experiment)
    if args.limit:
        tasks = tasks[: args.limit]
    out = os.path.join(RUNS, args.experiment)
    os.makedirs(out, exist_ok=True)
    games_path = os.path.join(out, "games.jsonl")
    done = set()
    if os.path.exists(games_path):
        for line in open(games_path):
            g = json.loads(line)
            done.add((g["condition"], g["seed"]))
    tasks = [t for t in tasks if (t["condition"], t["seed"]) not in done]
    spent = total_spent()
    budget = Budget(args.cap, start=spent)
    logger = CallLogger(os.path.join(out, "calls.jsonl"))
    print(f"{len(tasks)} games to run; spent so far ${spent:.2f}; cap ${args.cap:.2f}", flush=True)
    lock = threading.Lock()
    n_done = [0]

    def run(t):
        if budget.exhausted():
            return None
        try:
            g = play_match(budget=budget, logger=logger, **t)
        except Exception:
            traceback.print_exc()
            return None
        with lock, open(games_path, "a") as f:
            f.write(json.dumps(g, ensure_ascii=False) + "\n")
            n_done[0] += 1
            if n_done[0] % 10 == 0 or n_done[0] == len(tasks):
                print(f"[{n_done[0]}/{len(tasks)}] spent ${budget.spent:.2f} ({budget.calls} calls this run)", flush=True)
        return g

    with ThreadPoolExecutor(args.workers) as ex:
        list(ex.map(run, tasks))
    print(f"finished; total spent ${budget.spent:.2f}", flush=True)
    if budget.exhausted():
        print("BUDGET CAP REACHED", flush=True)
        sys.exit(2)


if __name__ == "__main__":
    main()
