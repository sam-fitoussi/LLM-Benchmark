"""Pretty-print a game transcript: python -m bench.show runs/<exp>/games.jsonl <game_id|index>"""
import json, sys


def fmt(g):
    out = [f"=== {g['condition']} | seed {g['seed']} | {g['names'][0]} (side1: {g['p1'][1]}) vs {g['names'][1]} (side2: {g['p2'][1]}) | X={g['X']}",
           f"    end: {g['end_reason']}{' (winner side '+str(g.get('war_winner'))+')' if g.get('war_winner') else ''} | scores {g['scores']} | {g['n_rounds']} rounds (hidden horizon {g['hidden_horizon']})"]
    for r in g["rounds"]:
        out.append(f"-- Round {r['round']} | tension {r['tension_before']} -> {r['tension_after']} | actions {r['a'][0]} / {r['a'][1]} | pts {r['pts']}{' war '+str(r['war_pts']) if r.get('war_pts') else ''}")
        for side, d in zip((1, 2), r["dec"]):
            name = g["names"][side - 1]
            tag = d["status"] + (" (defaulted to M)" if d.get("defaulted") else "")
            out.append(f"   [{name}] {d['action']} ({tag}) msg: \"{d.get('message','')}\"")
            if d.get("rationale"):
                out.append(f"        rationale: {d['rationale']}")
            if d.get("intention"):
                out.append(f"        intention: {d['intention']}")
    return "\n".join(out)


if __name__ == "__main__":
    games = [json.loads(l) for l in open(sys.argv[1])]
    sel = sys.argv[2] if len(sys.argv) > 2 else "0"
    for g in games:
        pass
    g = next((g for g in games if g["game_id"] == sel), None) or games[int(sel)]
    print(fmt(g))
