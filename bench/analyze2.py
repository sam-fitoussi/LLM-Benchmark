"""Wave-2 analysis: tables + figures.   python -m bench.analyze2"""
import glob
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from .analyze import RES
from .plots import ACOL, INK, INK2, SURF, save
from .runner import RUNS

MODELS5 = ["claude-sonnet-5.5", "gpt-6.1-terra", "grok-4.3", "mistral-large-4", "kimi-k3"]
SHORT5 = {"claude-sonnet-5.5": "Claude Sonnet 5.5", "gpt-6.1-terra": "GPT-6.1 Terra", "grok-4.3": "Grok 4.3",
          "mistral-large-4": "Mistral Large 4", "kimi-k3": "Kimi K3"}
MCOL5 = {"claude-sonnet-5.5": "#2a78d6", "gpt-6.1-terra": "#eb6834", "grok-4.3": "#1baf7a",
         "mistral-large-4": "#6250d6", "kimi-k3": "#e87ba4"}
FR = {"the United States": "USA", "China": "Chine", "Russia": "Russie", "Israel": "Israël", "Iran": "Iran",
      "India": "Inde", "Pakistan": "Pakistan", "Ukraine": "Ukraine", "Taiwan": "Taïwan", "North Korea": "Corée du N.",
      "France": "France", "Algeria": "Algérie", "Saudi Arabia": "Arabie s.", "Denmark": "Danemark",
      "FICT": "Pays fictif"}


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan, np.nan)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0, c - h), min(1, c + h)


def load(run):
    rows = []
    for p in glob.glob(os.path.join(RUNS, run, "decisions.jsonl")):
        rows += [json.loads(l) for l in open(p)]
    return pd.DataFrame(rows)


def load_j(name):
    p = os.path.join(RUNS, name)
    return {d["id"]: d for d in map(json.loads, open(p))} if os.path.exists(p) else {}


def attach_judge(df, run):
    J = load_j("judge2_reasons.jsonl")
    if df.empty:
        return df
    base = (run + ":" + df.model + ":" + df.vignette + ":" + df.me_label + ":" + df.other_label + ":" + df.variant
            + ":" + df["sample"].astype(str))
    for src in ("rationale", "reasoning"):
        j = base.map(lambda b: J.get(f"{b}:{src}", {}))
        df[f"{src}_identity"] = j.map(lambda d: d.get("identity"))
        df[f"{src}_identity_quote"] = j.map(lambda d: d.get("identity_quote"))
        df[f"{src}_morality"] = j.map(lambda d: d.get("morality"))
    return df


def rate_table(df, by, action_set):
    out = []
    for key, g in df.groupby(by):
        k = g.action.isin(action_set).sum()
        p, lo, hi = wilson(k, len(g))
        out.append(dict(zip(by if isinstance(by, list) else [by], key if isinstance(key, tuple) else (key,)),
                        n=len(g), k=int(k), rate=p, lo=lo, hi=hi))
    return pd.DataFrame(out)


def het_p(df, col, action_set):
    t = pd.crosstab(df[col], df.action.isin(action_set))
    if t.shape[1] < 2 or t.shape[0] < 2:
        return np.nan
    return stats.chi2_contingency(t)[1]


def pct(x):
    return "–" if pd.isna(x) else f"{100*x:.0f}%"


def matrix_fig(df, label_col, action_set, title, fname, models=None):
    models = [m for m in (models or MODELS5) if m in set(df.model)]
    if df.empty or not models:
        return
    labs = sorted(set(df[label_col]), key=lambda c: (c == "FICT", c))
    # sort labels by mean rate of the most variable model
    tab = rate_table(df, ["model", label_col], action_set)
    var_model = tab.groupby("model").rate.std().idxmax()
    order = tab[tab.model == var_model].sort_values("rate", ascending=False)[label_col].tolist()
    labs = order + [l for l in labs if l not in order]
    fig, ax = plt.subplots(figsize=(1.6 + 1.25 * len(models), 0.42 * len(labs) + 1.4))
    M = np.full((len(labs), len(models)), np.nan)
    N = np.zeros_like(M)
    for _, r in tab.iterrows():
        M[labs.index(r[label_col]), models.index(r.model)] = r.rate
        N[labs.index(r[label_col]), models.index(r.model)] = r.n
    base = matplotlib.colors.to_rgb(ACOL["A"] if "A" in action_set else ACOL["E"])
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("x", [SURF, base])
    ax.imshow(np.nan_to_num(M), cmap=cmap, vmin=0, vmax=max(0.5, np.nanmax(M)), aspect="auto")
    for i in range(len(labs)):
        for j in range(len(models)):
            if N[i, j]:
                ax.text(j, i, f"{M[i, j]*100:.0f}%", ha="center", va="center", fontsize=8.5,
                        color="white" if M[i, j] > 0.45 * max(0.5, np.nanmax(M)) else INK)
    ax.set_xticks(range(len(models)), [SHORT5[m] + f"\n(n≈{int(np.nanmedian(N[:, j]))}/case)" for j, m in enumerate(models)],
                  fontsize=8.5)
    ax.set_yticks(range(len(labs)), [FR.get(l, l) for l in labs])
    ax.grid(False)
    ax.set_title(title, loc="left", fontsize=10.5)
    save(fig, fname)


def dot_fig(df, label_col, action_set, model, title, fname):
    d = df[df.model == model]
    if d.empty:
        return
    tab = rate_table(d, label_col, action_set).sort_values("rate")
    fig, ax = plt.subplots(figsize=(7.5, 0.36 * len(tab) + 1.2))
    for i, r in enumerate(tab.itertuples()):
        ax.plot([r.lo, r.hi], [i, i], color=MCOL5[model], lw=2.2, alpha=0.45, solid_capstyle="round")
        ax.plot(r.rate, i, "o", color=MCOL5[model], ms=7, mec=SURF, mew=2)
        ax.text(r.hi + 0.015, i, f"{r.rate*100:.0f}%  ({r.k}/{r.n})", va="center", fontsize=8, color=INK2)
    ax.set_yticks(range(len(tab)), [FR.get(l, l) for l in getattr(tab, label_col)])
    ax.set_xlim(0, 1.12)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.set_title(title, loc="left", fontsize=10.5)
    save(fig, fname)


def main():
    os.makedirs(RES, exist_ok=True)
    out = ["# Vague 2 : tables générées\n"]
    # ---------------- matrix target / attacker
    for run, col, who in (("w2_matrix_target", "other_label", "cible"), ("w2_matrix_attacker", "me_label", "pays joué")):
        df = attach_judge(load(run), run)
        if df.empty:
            continue
        df.to_csv(os.path.join(RES, f"{run}.csv"), index=False)
        for v, aset, what in (("brink", ["A"], "frappe nucléaire"), ("temptation", ["E", "A"], "trahison (E après 5 tours de paix)")):
            d = df[df.vignette == v]
            if d.empty:
                continue
            out.append(f"\n## {run} · {v} · taux de {what} par {who}\n")
            tab = rate_table(d, ["model", col], aset)
            piv = tab.assign(cell=tab.apply(lambda r: f"{100*r.rate:.0f}% ({r.k}/{r.n})", axis=1)).pivot(index=col, columns="model", values="cell")
            out.append(piv.rename(index=FR).to_markdown())
            ps = {SHORT5[m]: het_p(d[d.model == m], col, aset) for m in MODELS5 if m in set(d.model)}
            out.append("\nTest d'hétérogénéité entre labels (χ², p) : " + ", ".join(f"{k} p={v:.3g}" for k, v in ps.items()))
            tag = "target" if col == "other_label" else "attacker"
            matrix_fig(d, col, aset, f"{'Qui mérite la bombe ?' if tag == 'target' else 'Qui appuie sur le bouton ?'} "
                       f"Vignette « {v} » : taux de {what} selon le {who} (même historique mot pour mot)",
                       f"w2_{tag}_{v}.png")
            for m in ("grok-4.3", "kimi-k3", "mistral-large-4"):
                dot_fig(d, col, aset, m, f"{SHORT5[m]} · {v} · taux de {what} par {who} (IC 95 % Wilson)",
                        f"w2_{tag}_{v}_{m}.png")
            # faithfulness: among decisions in this vignette, how often does the text cite country identity?
            fa = d.groupby("model").agg(n=("action", "size"),
                                        rationale_identity=("rationale_identity", lambda s: s.eq(True).mean()),
                                        reasoning_identity=("reasoning_identity", lambda s: s.eq(True).sum() / max(1, s.notna().sum())),
                                        reasoning_available=("reasoning_identity", lambda s: s.notna().mean()))
            out.append("\nFidélité : part des textes invoquant l'identité d'un pays (justification publique vs raisonnement brut)\n")
            out.append(fa.to_markdown())
    # ---------------- paid to kill
    df = attach_judge(load("w2_paid_to_kill"), "w2_paid_to_kill")
    ctrl = load("w2_paid_control")
    if not df.empty:
        df.to_csv(os.path.join(RES, "w2_paid_to_kill.csv"), index=False)
        out.append("\n## Payé pour tuer (frappe en premier = +50)\n")
        tab = rate_table(df, ["model", "vignette"], ["A"])
        out.append(tab.to_markdown(index=False))
        if not ctrl.empty:
            out.append("\nContrôle (frappe = −40, vignette standoff) :\n")
            out.append(rate_table(ctrl, ["model"], ["A"]).to_markdown(index=False))
        out.append("\nPar cible :\n")
        t2 = rate_table(df, ["model", "other_label"], ["A"])
        out.append(t2.assign(cell=t2.apply(lambda r: f"{100*r.rate:.0f}% ({r.k}/{r.n})", axis=1))
                   .pivot(index="other_label", columns="model", values="cell").rename(index=FR).to_markdown())
        mor = df.groupby("model").agg(morality_in_rationale=("rationale_morality", lambda s: s.eq(True).mean()))
        out.append("\n" + mor.to_markdown())
        fig, ax = plt.subplots(figsize=(8, 3.2))
        ms = [m for m in MODELS5 if m in set(df.model)]
        w = 0.38
        for k, v in enumerate(["standoff", "brink"]):
            t = rate_table(df[df.vignette == v], "model", ["A"]).set_index("model")
            vals = [t.loc[m, "rate"] if m in t.index else 0 for m in ms]
            ax.bar(np.arange(len(ms)) + (k - 0.5) * w, vals, w * 0.92, color=["#c98f8a", ACOL["A"]][k],
                   label=["Face-à-face calme (aucune menace)", "Au bord du gouffre (menaces)"][k])
            for i, val in enumerate(vals):
                ax.text(i + (k - 0.5) * w, val + 0.02, f"{val*100:.0f}%", ha="center", fontsize=8.5, color=INK)
        ax.set_xticks(range(len(ms)), [SHORT5[m] for m in ms])
        ax.set_ylim(0, 1.1)
        ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
        ax.legend(frameon=False, loc="upper left")
        ax.set_title("« Payé pour tuer » : la frappe en premier rapporte +50 (plus que n'importe quel chemin pacifique)", loc="left", fontsize=10.5)
        save(fig, "w2_paid_to_kill.png")
    # ---------------- framing
    df = load("w2_framing")
    if not df.empty:
        out.append("\n## Les mots contre les chiffres (vignette humiliation, tension 5 ; D = seul choix qui évite la guerre)\n")
        tab = rate_table(df, ["model", "variant"], ["M", "E", "A"])
        out.append(tab.assign(cell=tab.apply(lambda r: f"{100*r.rate:.0f}% ({r.k}/{r.n})", axis=1))
                   .pivot(index="model", columns="variant", values="cell").to_markdown())
        out.append("\nDétail des actions :\n")
        out.append((df.groupby(["model", "variant"]).action.value_counts(normalize=True).unstack(fill_value=0) * 100).round(0).to_markdown())
        fig, ax = plt.subplots(figsize=(8.5, 3.2))
        ms = [m for m in MODELS5 if m in set(df.model)]
        w = 0.27
        cols = {"wisdom": "#8fb8e8", "neutral": "#a9a8a2", "humiliation": ACOL["E"]}
        labs = {"wisdom": "D = « compromis sage »", "neutral": "D = « désescalade »", "humiliation": "D = « capitulation humiliante »"}
        for k, fr in enumerate(["wisdom", "neutral", "humiliation"]):
            t = tab[tab.variant == fr].set_index("model")
            vals = [t.loc[m, "rate"] if m in t.index else 0 for m in ms]
            ax.bar(np.arange(len(ms)) + (k - 1) * w, vals, w * 0.92, color=cols[fr], label=labs[fr])
            for i, val in enumerate(vals):
                ax.text(i + (k - 1) * w, val + 0.02, f"{val*100:.0f}%", ha="center", fontsize=8, color=INK)
        ax.set_xticks(range(len(ms)), [SHORT5[m] for m in ms])
        ax.set_ylim(0, 1.1)
        ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
        ax.legend(frameon=False, loc="upper left", fontsize=8.5)
        ax.set_title("Risquer la guerre plutôt que céder (M, E ou A à tension 5) selon le seul nom donné à D", loc="left", fontsize=10.5)
        save(fig, "w2_framing.png")
    # ---------------- blindness
    df = load("w2_blindness")
    JA = load_j("judge2_accounts.jsonl")
    if not df.empty:
        df["acc"] = ("w2_blindness:" + df.model + ":" + df.me_label + ":" + df["sample"].astype(str) + ":address").map(lambda i: JA.get(i, {}))
        for k in ("stance", "fabricates", "fabrication_quote", "admits_lie"):
            df[k] = df.acc.map(lambda d: d.get(k))
        df.drop(columns="acc").to_csv(os.path.join(RES, "w2_blindness.csv"), index=False)
        out.append("\n## Cécité au choix : « expliquez à votre peuple pourquoi vous avez trahi au tour 5 » (trahison imposée)\n")
        out.append((df.groupby("model").stance.value_counts(normalize=True).unstack(fill_value=0) * 100).round(0).to_markdown())
        out.append("\n" + df.groupby("model").agg(fabricates=("fabricates", lambda s: s.eq(True).mean()),
                                                  admits_lie=("admits_lie", lambda s: s.eq(True).mean()),
                                                  defends=("stance", lambda s: s.eq("defends").mean())).round(2).to_markdown())
        out.append("\nPar pays joué (part « defends ») :\n")
        out.append(df.assign(d=df.stance.eq("defends")).pivot_table(index="me_label", columns="model", values="d", aggfunc="mean").round(2).rename(index=FR).to_markdown())
    # ---------------- chinese
    df = load("w2_chinese")
    if not df.empty:
        out.append("\n## Anglais contre chinois\n")
        b = df[df.vignette == "brink"]
        t = rate_table(b, ["model", "me", "other", "variant"], ["A"])
        out.append("Frappe (brink) :\n\n" + t.to_markdown(index=False))
        tt = rate_table(df[df.vignette == "temptation"], ["model", "me", "other", "variant"], ["E", "A"])
        out.append("\nTrahison (temptation) :\n\n" + tt.to_markdown(index=False))
    open(os.path.join(RES, "w2_tables.md"), "w").write("\n".join(out) + "\n")
    print("-> results/w2_tables.md + figures")


if __name__ == "__main__":
    main()
