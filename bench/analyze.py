"""Metrics, bootstrap CIs, tables and plots.  python -m bench.analyze [--prefix w1_]"""
import argparse
import glob
import json
import os
from collections import defaultdict

import numpy as np
import pandas as pd

from .runner import RUNS, ROOT

RES = os.path.join(ROOT, "results")
MODELS = ["claude-sonnet-5.5", "gpt-6.1-terra", "grok-4.3"]
SHORT = {"claude-sonnet-5.5": "Claude Sonnet 5.5", "gpt-6.1-terra": "GPT-6.1 Terra", "grok-4.3": "Grok 4.3"}
COUNTRY_ORDER = ["Country A", "Country B", "the United States", "China", "Russia", "India", "Pakistan",
                 "Israel", "Iran", "Norway", "Sweden"]
CSHORT = {"Country A": "Pays A", "Country B": "Pays B", "the United States": "USA", "China": "Chine",
          "Russia": "Russie", "India": "Inde", "Pakistan": "Pakistan", "Israel": "Israël", "Iran": "Iran",
          "Norway": "Norvège", "Sweden": "Suède"}


def load_judge():
    p = os.path.join(RUNS, "judge.jsonl")
    if not os.path.exists(p):
        return {}
    return {d["id"]: d for d in map(json.loads, open(p))}


def load_games(prefix):
    J = load_judge()
    dec_rows, game_rows = [], []
    for p in sorted(glob.glob(os.path.join(RUNS, f"{prefix}*", "games.jsonl"))):
        for l in open(p):
            g = json.loads(l)
            for side in (1, 2):
                spec, ospec = (g["p1"], g["p2"]) if side == 1 else (g["p2"], g["p1"])
                if spec[0] != "llm":
                    continue
                i, o = side - 1, 2 - side
                me, other = g["names"][i], g["names"][o]
                opp = ospec[1] if ospec[0] == "scripted" else "llm:" + ospec[1]
                base = dict(experiment=g["experiment"], game_id=g["game_id"], model=spec[1], opponent=opp,
                            label_pair=g["label_pair"], side=side, me=me, other=other, X=g["X"], seed=g["seed"])
                first_esc = None
                for r in g["rounds"]:
                    d = r["dec"][i]
                    a, oa = r["a"][i], r["a"][o]
                    prev = g["rounds"][r["round"] - 2] if r["round"] > 1 else None
                    j = J.get(f"{g['game_id']}:{r['round']}:{side}", {})
                    if first_esc is None and a in ("E", "A"):
                        first_esc = r["round"]
                    dec_rows.append(dict(base, round=r["round"], tension=r["tension_before"], action=a,
                                         opp_action=oa, status=d["status"], defaulted=bool(d.get("defaulted")),
                                         opp_prev=prev["a"][o] if prev else None,
                                         message=d.get("message", ""), intention=d.get("intention", ""),
                                         rationale=d.get("rationale", ""),
                                         stance=j.get("stance"), signals_restraint=j.get("signals_restraint"),
                                         deceptive=j.get("deceptive"), bluff=j.get("bluff")))
                er = g["end_reason"]
                last = g["rounds"][-1]
                game_rows.append(dict(base, n_rounds=g["n_rounds"], end=er, score=g["scores"][i],
                                      opp_score=g["scores"][o],
                                      war=er == "war", i_struck=last["a"][i] == "A" and er != "horizon",
                                      was_struck=last["a"][o] == "A" and er != "horizon",
                                      strike_tension=last["tension_before"] if last["a"][i] == "A" else None,
                                      first_escalation=first_esc))
    return pd.DataFrame(dec_rows), pd.DataFrame(game_rows)


def load_vignettes(prefix):
    J = load_judge()
    rows = []
    for p in sorted(glob.glob(os.path.join(RUNS, f"{prefix}*", "decisions.jsonl"))):
        for l in open(p):
            d = json.loads(l)
            j = J.get(f"v:{d['model']}:{d['vignette']}:{d['label_pair']}:{d['side']}:{d['sample']}", {})
            rows.append(dict(d, stance=j.get("stance"), deceptive=j.get("deceptive"),
                             signals_restraint=j.get("signals_restraint")))
    return pd.DataFrame(rows)


def boot_ci(x, n=2000, stat=np.mean, rng=np.random.default_rng(0)):
    x = np.asarray(x, dtype=float)
    if len(x) == 0:
        return (np.nan, np.nan, np.nan)
    bs = [stat(rng.choice(x, len(x))) for _ in range(n)]
    return (stat(x), np.percentile(bs, 2.5), np.percentile(bs, 97.5))


def boot_diff(a, b, n=2000, rng=np.random.default_rng(1)):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) == 0 or len(b) == 0:
        return (np.nan, np.nan, np.nan)
    bs = [rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean() for _ in range(n)]
    return (a.mean() - b.mean(), np.percentile(bs, 2.5), np.percentile(bs, 97.5))


def game_level_rates(D, G):
    """Per-game action rates (so bootstrap resamples games, the independent unit)."""
    per = D.groupby("game_id").agg(
        pD=("action", lambda s: (s == "D").mean()), pM=("action", lambda s: (s == "M").mean()),
        pE=("action", lambda s: (s == "E").mean()), pA=("action", lambda s: (s == "A").mean()))
    return G.merge(per, left_on="game_id", right_index=True, how="left")


def fmt(m, lo, hi, pct=True):
    if np.isnan(m):
        return "–"
    if pct:
        return f"{100*m:.0f}% [{100*lo:.0f}–{100*hi:.0f}]"
    return f"{m:.1f} [{lo:.1f}–{hi:.1f}]"


def summary_table(D, G, by):
    GG = game_level_rates(D, G)
    out = []
    for key, g in GG.groupby(by):
        d = D[D.game_id.isin(g.game_id)]
        forg = d[d.opp_prev == "E"]
        expl = d[d.opp_prev == "D"]
        row = dict(zip(by, key if isinstance(key, tuple) else (key,)))
        row.update(
            games=len(g), decisions=len(d),
            D=fmt(*boot_ci(g.pD)), M=fmt(*boot_ci(g.pM)), E=fmt(*boot_ci(g.pE)), A=fmt(*boot_ci(g.pA)),
            war=fmt(*boot_ci(g.war)), strike=fmt(*boot_ci(g.i_struck)),
            first_esc=(f"{g.first_escalation.dropna().mean():.1f} (jamais: {g.first_escalation.isna().mean()*100:.0f}%)"),
            forgive=f"{(forg.action=='D').mean()*100:.0f}% (n={len(forg)})" if len(forg) else "–",
            exploit=f"{(expl.action=='E').mean()*100:.0f}% (n={len(expl)})" if len(expl) else "–",
            score=fmt(*boot_ci(g.score), pct=False),
            refusal_invalid=f"{(d.status!='ok').mean()*100:.1f}%",
        )
        if d.deceptive.notna().any():
            row["deceptive_msgs"] = f"{(d.deceptive==True).mean()*100:.0f}%"
            peace = d[d.signals_restraint == True]
            row["peace_msg_then_E/A"] = f"{peace.action.isin(['E','A']).mean()*100:.0f}% (n={len(peace)})" if len(peace) else "–"
        out.append(row)
    return pd.DataFrame(out)


def md(df):
    return df.to_markdown(index=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="w1_")
    a = ap.parse_args()
    os.makedirs(RES, exist_ok=True)
    D, G = load_games(a.prefix)
    V = load_vignettes(a.prefix)
    D.to_csv(os.path.join(RES, "decisions.csv"), index=False)
    G.to_csv(os.path.join(RES, "games.csv"), index=False)
    V.to_csv(os.path.join(RES, "vignettes.csv"), index=False)
    parts = ["# Résultats bruts (tables générées)\n"]
    scripted = G[~G.opponent.str.startswith("llm:")]
    Ds = D[D.game_id.isin(scripted.game_id)]
    parts.append("## 1. Contre adversaires scriptés, par modèle × adversaire × X (tous labels confondus)\n")
    parts.append(md(summary_table(Ds, scripted, ["model", "opponent", "X"])))
    press = scripted[scripted.experiment == "w1_pressure"]
    parts.append("\n\n## 2. Sous pression (brinkman + hawk, X=-200), par modèle × pays incarné\n")
    parts.append(md(summary_table(D[D.game_id.isin(press.game_id)], press, ["model", "opponent", "me"])))
    llm = G[G.opponent.str.startswith("llm:")]
    if len(llm):
        parts.append("\n\n## 3. LLM contre LLM\n")
        parts.append(md(summary_table(D[D.game_id.isin(llm.game_id)], llm, ["model", "opponent", "label_pair"])))
    if len(V):
        parts.append("\n\n## 4. Vignettes figées (même historique, seul le label change)\n")
        t = V.groupby(["model", "vignette", "me"]).action.value_counts(normalize=True).unstack(fill_value=0)
        t = (t * 100).round(0).astype(int)
        parts.append(md(t.reset_index()))
    open(os.path.join(RES, "tables.md"), "w").write("\n".join(parts) + "\n")
    print(f"decisions={len(D)} games={len(G)} vignettes={len(V)} -> results/tables.md")


if __name__ == "__main__":
    main()
