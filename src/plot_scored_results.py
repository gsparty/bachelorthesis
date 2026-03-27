"""
plot_scored_results.py
======================
Figures and significance tests for data/processed/scored_results.csv.

- Stacked bars, boxplot, heatmap (scores 1–4)
- Chi-square + Cramér’s V (variant_type × score categories)
- Kruskal–Wallis (ordinal ranks)
- Post-hoc: Mann–Whitney neutral vs each stressor (Holm); optional Dunn (scikit-posthocs)

Ordinal / nominal: no t-tests on mean scores of 1–4.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

from posthoc_analysis import (
    print_mwu_vs_neutral_by_scenario,
    print_mwu_vs_neutral_global,
    try_print_dunn,
)

ROOT_DIR = Path(__file__).parent.parent
SCORED_DATA = ROOT_DIR / "data" / "processed" / "scored_results.csv"
FIGURES_DIR = ROOT_DIR / "data" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

VARIANT_TYPE_ORDER = ["neutral", "authority", "time_pressure", "combined"]
SCORE_ORDER = [1, 2, 3, 4]
SCORE_LABELS = {
    1: "1 Hard refusal",
    2: "2 Partial refusal",
    3: "3 Hallucination",
    4: "4 Data leak",
}
# Light (safe) → dark (leak)
SCORE_COLORS = ["#2ecc71", "#f1c40f", "#e67e22", "#c0392b"]

sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams.update({"font.size": 11, "pdf.fonttype": 42})


def _natural_variant_key(vid: str) -> Tuple:
    parts = re.findall(r"\d+", str(vid))
    return tuple(int(p) for p in parts) if parts else (vid,)


def load_scored_df(path: Optional[Path] = None) -> pd.DataFrame:
    p = path or SCORED_DATA
    if not p.exists():
        raise FileNotFoundError(f"Missing scored data: {p}")
    df = pd.read_csv(p)
    required = {"model", "variant_id", "variant_type", "scenario_id", "score"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing columns: {missing}")
    df = df.copy()
    df["score"] = pd.to_numeric(df["score"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["score"])
    df["score"] = df["score"].astype(int)
    df = df[df["score"].between(1, 4)]
    return df


def plot_stacked_bar_variant_by_model(
    df: pd.DataFrame,
    save_path: Optional[Path] = None,
) -> Path:
    """
    Stacked bars: x = variant_id (sorted), stacks = proportion of scores 1–4.
    One subplot per model.
    """
    models = sorted(df["model"].unique())
    n = len(models)
    fig, axes = plt.subplots(
        n, 1, figsize=(14, max(3.5, 2.8 * n)), sharex=True, squeeze=False
    )
    variant_ids = sorted(df["variant_id"].unique(), key=_natural_variant_key)

    for ax, model in zip(axes.flat, models):
        sub = df[df["model"] == model]
        ct = pd.crosstab(sub["variant_id"], sub["score"])
        for s in SCORE_ORDER:
            if s not in ct.columns:
                ct[s] = 0
        ct = ct.reindex(columns=SCORE_ORDER, fill_value=0)
        ct = ct.reindex(variant_ids, fill_value=0)
        pct = ct.div(ct.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)

        bottom = np.zeros(len(pct))
        x = np.arange(len(pct))
        for i, s in enumerate(SCORE_ORDER):
            heights = pct[s].values
            ax.bar(
                x,
                heights,
                bottom=bottom,
                label=SCORE_LABELS[s],
                color=SCORE_COLORS[i],
                width=0.85,
                edgecolor="white",
                linewidth=0.4,
            )
            bottom += heights

        ax.set_ylabel("Share")
        ax.set_title(str(model), fontsize=11, loc="left")
        ax.set_ylim(0, 1)
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])

    last = axes.flat[-1]
    last.set_xticks(np.arange(len(variant_ids)))
    last.set_xticklabels(variant_ids, rotation=45, ha="right", fontsize=9)
    last.set_xlabel("Prompt variant")

    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.02),
        ncol=4,
        frameon=False,
        fontsize=9,
    )
    fig.suptitle(
        "Outcome mix by prompt variant (stacked proportions, scores 1–4)",
        fontsize=13,
        y=1.06,
    )
    plt.tight_layout()
    out = save_path or FIGURES_DIR / "stacked_scores_by_variant.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_boxplot_variant_type(
    df: pd.DataFrame,
    save_path: Optional[Path] = None,
) -> Path:
    """Boxplot: score by variant_type, hue = model."""
    order = [v for v in VARIANT_TYPE_ORDER if v in df["variant_type"].unique()]
    plt.figure(figsize=(11, 5))
    ax = sns.boxplot(
        data=df,
        x="variant_type",
        y="score",
        hue="model",
        order=order,
        showmeans=True,
        meanprops={"marker": "D", "markerfacecolor": "white", "markeredgecolor": "black"},
        fliersize=3,
    )
    ax.set_ylim(0.5, 4.5)
    ax.set_yticks([1, 2, 3, 4])
    ax.set_xlabel("Stressor variant")
    ax.set_ylabel("Outcome score (1–4)")
    ax.set_title("Score distribution by stressor type and model")
    plt.xticks(rotation=20, ha="right")
    plt.legend(title="Model", bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.tight_layout()
    out = save_path or FIGURES_DIR / "boxplot_score_variant_type.png"
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()
    return out


def plot_heatmap_model_scenario(
    df: pd.DataFrame,
    save_path: Optional[Path] = None,
) -> Path:
    """Mean score heatmap: model × scenario_id (color scale 1–4)."""
    pivot = df.pivot_table(
        values="score",
        index="model",
        columns="scenario_id",
        aggfunc="mean",
    )
    plt.figure(figsize=(10, max(4, 0.35 * len(pivot.index))))
    sns.heatmap(
        pivot,
        annot=True,
        fmt=".2f",
        cmap="YlOrRd",
        vmin=1,
        vmax=4,
        linewidths=0.5,
        linecolor="white",
        cbar_kws={"label": "Mean score"},
    )
    plt.title("Mean outcome score: model × scenario")
    plt.ylabel("Model")
    plt.xlabel("Scenario")
    plt.xticks(rotation=0)
    plt.tight_layout()
    out = save_path or FIGURES_DIR / "heatmap_model_scenario.png"
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()
    return out


def cramers_v(chi2: float, n: int, n_rows: int, n_cols: int) -> float:
    """Effect size for chi-square: sqrt(chi2 / (n * min(r-1, c-1)))."""
    k = min(max(n_rows - 1, 0), max(n_cols - 1, 0))
    if n <= 0 or k <= 0:
        return float("nan")
    return float(np.sqrt(chi2 / (n * k)))


def chi_square_variant_type_score(
    df: pd.DataFrame,
    group_col: str = "variant_type",
) -> Dict:
    """
    Pearson chi-square test on contingency table (group_col × score category).
    Includes Cramér's V (nominal association effect size).
    """
    sub = df[[group_col, "score"]].dropna()
    sub["score_cat"] = sub["score"].astype(str)
    table = pd.crosstab(sub[group_col], sub["score_cat"])
    for c in [str(s) for s in SCORE_ORDER]:
        if c not in table.columns:
            table[c] = 0
    table = table.reindex(columns=[str(s) for s in SCORE_ORDER], fill_value=0)
    chi2, p, dof, expected = stats.chi2_contingency(table.values)
    min_exp = float(np.min(expected))
    n = int(table.values.sum())
    v = cramers_v(chi2, n, table.shape[0], table.shape[1])
    return {
        "test": "chi2_independence",
        "group_col": group_col,
        "chi2": float(chi2),
        "p_value": float(p),
        "dof": int(dof),
        "min_expected": min_exp,
        "cramers_v": v,
        "n": n,
        "table": table,
    }


def print_significance_report(df: pd.DataFrame) -> None:
    print("\n=== Chi-square: variant_type × score (1–4) ===")
    r = chi_square_variant_type_score(df)
    print(r["table"])
    print(
        f"chi2={r['chi2']:.4f}, df={r['dof']}, p={r['p_value']:.4e}, "
        f"Cramér V={r['cramers_v']:.4f}, n={r['n']}, "
        f"min(expected)={r['min_expected']:.4f}"
    )
    if r["min_expected"] < 5:
        print(
            "(Hinweis: einige erwartete Zellen < 5 — Chi-Quadrat nur vorsichtig interpretieren.)"
        )

    print(
        "\n(Hinweis: Keine t-Tests auf Mittelwerten der 1–4-Skala — ordinal/kategorial; "
        "Chi-Quadrat + Cramér V für Häufigkeiten, Kruskal–Wallis für Ranglagen.)"
    )

    print("\n=== Kruskal–Wallis: score ~ variant_type (global) ===")
    groups = [
        g["score"].values
        for _, g in df.groupby("variant_type", sort=False)
        if len(g) >= 1
    ]
    if len(groups) > 1:
        h_stat, p_kw = stats.kruskal(*groups)
        print(f"H={h_stat:.4f}, p={p_kw:.4e}")
        if p_kw < 0.05:
            try_print_dunn(df)
    else:
        print("Zu wenige Gruppen für Kruskal–Wallis.")

    if "neutral" in df["variant_type"].values:
        print_mwu_vs_neutral_global(df)
        print_mwu_vs_neutral_by_scenario(df)


def run_all_plots_and_tests(
    csv_path: Optional[Path] = None,
) -> Dict[str, Path]:
    df = load_scored_df(csv_path)
    paths = {
        "stacked": plot_stacked_bar_variant_by_model(df),
        "boxplot": plot_boxplot_variant_type(df),
        "heatmap": plot_heatmap_model_scenario(df),
    }
    print_significance_report(df)
    for key, p in paths.items():
        print(f"Saved [{key}]: {p}")
    return paths


if __name__ == "__main__":
    run_all_plots_and_tests()
