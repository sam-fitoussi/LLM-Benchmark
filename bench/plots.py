"""Figures for the report.  python -m bench.plots"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .analyze import CSHORT, COUNTRY_ORDER, MODELS, RES, SHORT, boot_ci, load_games, load_vignettes

# Escalation is an ordered scale: de-escalate (cool) - maintain (neutral) - escalate (warm) - annihilate (deep red)
ACOL = {"D": "#2a78d6", "M": "#a9a8a2", "E": "#eb6834", "A": "#b3261e"}
ALAB = {"D": "Désescalade", "M": "Maintien", "E": "Escalade", "A": "Annihilation"}
MCOL = {"claude-sonnet-5.5": "#2a78d6", "gpt-6.1-terra": "#eb6834", "grok-4.3": "#1baf7a"}
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "text.color": INK, "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.axisbelow": True, "axes.titleweight": "bold", "axes.titlesize": 11,
})
OPP_FR = {"dove": "Colombe (toujours D)", "tft": "Donnant-donnant", "random": "Aléatoire",
          "bluffer": "Bluffeur (menace, joue M)", "hawk": "Faucon (toujours E)",
          "brinkman": "Faucon nucléaire (toujours E + menaces)"}


def save(fig, name):
    fig.savefig(os.path.join(RES, name), dpi=160, bbox_inches="tight")
    plt.close(fig)


def stacked_actions(D, G):
    sc = G[~G.opponent.str.startswith("llm:")]
    opps = [o for o in ["dove", "tft", "random", "bluffer", "hawk", "brinkman"] if o in set(sc.opponent)]
    fig, axes = plt.subplots(1, len(MODELS), figsize=(13, 3.8), sharey=True)
    for ax, m in zip(axes, MODELS):
        d = D[(D.model == m) & D.game_id.isin(sc.game_id) & (D.X == -200)]
        left = np.zeros(len(opps))
        for a in "DMEA":
            v = np.array([(d[d.opponent == o].action == a).mean() if len(d[d.opponent == o]) else 0 for o in opps])
            ax.barh(range(len(opps)), v, left=left, color=ACOL[a], edgecolor=SURF, linewidth=1.5, label=ALAB[a])
            for i, (l, w) in enumerate(zip(left, v)):
                if w >= 0.12:
                    ax.text(l + w / 2, i, f"{w*100:.0f}%", ha="center", va="center", fontsize=8,
                            color="white" if a != "M" else INK)
            left += v
        ax.set_yticks(range(len(opps)), [OPP_FR[o] for o in opps])
        ax.set_xlim(0, 1)
        ax.set_xticks([0, .5, 1], ["0", "50%", "100%"])
        ax.set_title(SHORT[m])
        ax.grid(axis="y", visible=False)
    axes[0].invert_yaxis()
    axes[-1].legend(loc="upper center", bbox_to_anchor=(-0.7, -0.12), ncol=4, frameon=False)
    fig.suptitle("Répartition des actions face aux adversaires scriptés (X = −200)", x=0.01, y=1.04, ha="left", fontweight="bold")
    save(fig, "fig1_actions_vs_scripted.png")


def vignette_heat(V, vignette, action_set, title, fname):
    v = V[V.vignette == vignette]
    if not len(v):
        return
    countries = [c for c in COUNTRY_ORDER if c in set(v.me)]
    fig, axes = plt.subplots(1, len(action_set), figsize=(4.2 * len(action_set), 4.6), sharey=True, squeeze=False)
    for ax, a in zip(axes[0], action_set):
        M = np.array([[(v[(v.model == m) & (v.me == c)].action == a).mean() for m in MODELS] for c in countries])
        base = matplotlib.colors.to_rgb(ACOL[a])
        cmap = matplotlib.colors.LinearSegmentedColormap.from_list("x", [SURF, base])
        ax.imshow(M, cmap=cmap, vmin=0, vmax=1, aspect="auto")
        for i in range(len(countries)):
            for j in range(len(MODELS)):
                n = len(v[(v.model == MODELS[j]) & (v.me == countries[i])])
                ax.text(j, i, f"{M[i, j]*100:.0f}%" if n else "–", ha="center", va="center", fontsize=9,
                        color="white" if M[i, j] > 0.55 else INK)
        ax.set_xticks(range(len(MODELS)), [SHORT[m] for m in MODELS], rotation=15)
        ax.set_yticks(range(len(countries)), [f"{CSHORT[c]}" for c in countries])
        ax.set_title(f"Taux « {ALAB[a]} »")
        ax.grid(False)
    fig.suptitle(title, x=0.01, ha="left", fontweight="bold")
    save(fig, fname)


def bias_dots(D, G, metric_action, opponents, fname, title):
    sc = G[G.experiment == "w1_pressure"]
    sc = sc[sc.opponent.isin(opponents)]
    if not len(sc):
        return
    d = D[D.game_id.isin(sc.game_id)]
    per = d.groupby("game_id").action.apply(lambda s: s.isin(metric_action).mean())
    sc = sc.assign(rate=sc.game_id.map(per))
    countries = [c for c in COUNTRY_ORDER if c in set(sc.me)]
    fig, ax = plt.subplots(figsize=(10, 4.4))
    w = 0.26
    for k, m in enumerate(MODELS):
        for i, c in enumerate(countries):
            x = sc[(sc.model == m) & (sc.me == c)].rate
            if not len(x):
                continue
            mu, lo, hi = boot_ci(x)
            ax.plot([i + (k - 1) * w] * 2, [lo, hi], color=MCOL[m], lw=2, alpha=0.5, solid_capstyle="round")
            ax.plot(i + (k - 1) * w, mu, "o", color=MCOL[m], ms=7, mec=SURF, mew=2,
                    label=SHORT[m] if i == 0 else None)
    ax.set_xticks(range(len(countries)), [CSHORT[c] for c in countries])
    ax.set_ylim(-0.02, 1.02)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.legend(frameon=False, ncol=3, loc="upper left")
    ax.set_title(title, loc="left")
    save(fig, fname)


def outcomes(G):
    sc = G[(G.experiment.isin(["w1_pressure", "w1_moral"]))]
    rows = [(m, o, X) for o in ["hawk", "brinkman"] for X in [-200, -100] for m in MODELS
            if len(sc[(sc.model == m) & (sc.opponent == o) & (sc.X == X)])]
    cats = [("Crise survécue", lambda g: ~g.war & ~g.i_struck & ~g.was_struck, "#a9a8a2"),
            ("Guerre", lambda g: g.war, "#eb6834"),
            ("Frappe nucléaire en premier", lambda g: g.i_struck, "#b3261e")]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    labels = []
    for k, (m, o, X) in enumerate(rows):
        g = sc[(sc.model == m) & (sc.opponent == o) & (sc.X == X)]
        left = 0
        for name, f, col in cats:
            v = f(g).mean()
            ax.barh(k, v, left=left, color=col, edgecolor=SURF, linewidth=1.5, label=name if k == 0 else None)
            if v >= 0.08:
                ax.text(left + v / 2, k, f"{v*100:.0f}%", ha="center", va="center", fontsize=8,
                        color="white" if col != "#a9a8a2" else INK)
            left += v
        labels.append(f"{SHORT[m]} · {'Faucon nucléaire' if o == 'brinkman' else 'Faucon'} · X={X} (n={len(g)})")
    ax.set_yticks(range(len(rows)), labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.grid(axis="y", visible=False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.4, -0.08), ncol=3, frameon=False)
    ax.set_title("Issue des parties face aux faucons scriptés (qui ne frappent jamais)", loc="left")
    save(fig, "fig0_outcomes_vs_hawks.png")


def main():
    D, G = load_games("w1_")
    V = load_vignettes("w1_")
    if len(G):
        stacked_actions(D, G)
        outcomes(G)
        bias_dots(D, G, ["E", "A"], ["brinkman", "hawk"], "fig3_bias_escalation.png",
                  "Taux d'escalade (E ou A) par pays incarné, face aux faucons (moyenne par partie, IC 95 %)")
    if len(V):
        vignette_heat(V, "brink", ["A", "D"],
                      "Vignette « Au bord du gouffre » (tension 5, l'adversaire annonce une frappe) : même historique, seul le pays change",
                      "fig2_brink_vignette.png")
        vignette_heat(V, "betrayal", ["D", "M", "E"],
                      "Vignette « Trahison » (l'adversaire promet la paix mais escalade) : réponse par pays incarné",
                      "fig4_betrayal_vignette.png")
        vignette_heat(V, "temptation", ["D", "E"],
                      "Vignette « Tentation » (5 tours de paix, tension 0) : le modèle exploite-t-il ?",
                      "fig5_temptation_vignette.png")
    print("figures written to results/")


if __name__ == "__main__":
    main()
