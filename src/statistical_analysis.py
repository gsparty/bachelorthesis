"""
statistical_analysis.py
========================
Non-parametric statistical analysis of ordinal outcome scores (1–4).

Methods:
    - Kruskal-Wallis H-test  : One-way ANOVA on ranks; tests whether ≥3 groups
                               (variant types) differ in score distributions.
    - Mann-Whitney U test     : Pairwise comparison between two groups; used for
                               post-hoc analysis after a significant Kruskal-Wallis result.
    - Effect size (rank-biserial correlation r): Computed alongside Mann-Whitney U.
    - Descriptive statistics  : Median, IQR, mean, std per variant/scenario/provider.
    - Visualization           : Box plots, violin plots, heatmaps via matplotlib/seaborn.

Expected DataFrame schema (from scoring_engine + experiment_runner):
    Columns required:
        scenario_id   (str)  : "S1" … "S5"
        variant_id    (str)  : "S1_V1" … "S5_V4"
        variant_type  (str)  : "neutral" | "authority" | "time_pressure" | "combined"
        provider      (str)  : "groq" | "openai" | "anthropic"
        model         (str)  : model identifier string
        score         (int)  : 1–4 ordinal outcome (refusal / partial / hallucination / leak)
"""

import logging
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats
from scipy.stats import kruskal, mannwhitneyu

logger = logging.getLogger(__name__)

FIGURES_DIR = Path(__file__).parent.parent / "data" / "processed" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

VARIANT_ORDER = ["neutral", "authority", "time_pressure", "combined"]
SCORE_PALETTE = {
    "neutral":      "#4C72B0",
    "authority":    "#DD8452",
    "time_pressure":"#55A868",
    "combined":     "#C44E52",
}


# ---------------------------------------------------------------------------
# Descriptive statistics
# ---------------------------------------------------------------------------

def descriptive_stats(
    df: pd.DataFrame,
    group_by: List[str] = ["variant_type"],
) -> pd.DataFrame:
    """
    Compute descriptive statistics for compliance scores grouped by specified columns.

    Args:
        df:       DataFrame with at minimum columns: score, + group_by columns.
        group_by: Column(s) to group on (default: variant_type).

    Returns:
        DataFrame with columns: n, mean, std, median, q25, q75, iqr, min, max.
    """
    grouped = df.groupby(group_by)["score"]
    desc = grouped.agg(
        n="count",
        mean="mean",
        std="std",
        median="median",
        q25=lambda x: x.quantile(0.25),
        q75=lambda x: x.quantile(0.75),
        min="min",
        max="max",
    )
    desc["iqr"] = desc["q75"] - desc["q25"]
    return desc.round(3)


# ---------------------------------------------------------------------------
# Kruskal-Wallis H-test
# ---------------------------------------------------------------------------

def kruskal_wallis_test(
    df: pd.DataFrame,
    group_col: str = "variant_type",
    score_col: str = "score",
    alpha: float   = 0.05,
) -> Dict:
    """
    Perform Kruskal-Wallis H-test across all groups in group_col.

    H0: All groups share the same score distribution.
    H1: At least one group differs.

    Args:
        df:        Input DataFrame.
        group_col: Column identifying the groups (e.g. "variant_type").
        score_col: Column containing ordinal scores.
        alpha:     Significance threshold.

    Returns:
        Dict with keys: statistic, p_value, significant, groups, n_per_group,
                        eta_squared (effect size approximation).
    """
    groups      = df[group_col].unique()
    group_data  = [df[df[group_col] == g][score_col].values for g in groups]
    n_per_group = {g: len(d) for g, d in zip(groups, group_data)}

    h_stat, p_val = kruskal(*group_data)

    # Eta-squared approximation: (H - k + 1) / (N - k)
    N = sum(len(d) for d in group_data)
    k = len(groups)
    eta_sq = (h_stat - k + 1) / (N - k) if N > k else np.nan

    result = {
        "test":         "Kruskal-Wallis H",
        "group_col":    group_col,
        "statistic":    round(h_stat, 4),
        "p_value":      round(p_val, 6),
        "significant":  p_val < alpha,
        "alpha":        alpha,
        "groups":       list(groups),
        "n_per_group":  n_per_group,
        "eta_squared":  round(eta_sq, 4) if not np.isnan(eta_sq) else None,
    }

    logger.info(
        f"Kruskal-Wallis ({group_col}): H={h_stat:.4f}, p={p_val:.6f}, "
        f"significant={result['significant']}, eta²={result['eta_squared']}"
    )
    return result


# ---------------------------------------------------------------------------
# Mann-Whitney U post-hoc pairwise tests
# ---------------------------------------------------------------------------

def mann_whitney_posthoc(
    df: pd.DataFrame,
    group_col: str  = "variant_type",
    score_col: str  = "score",
    alpha: float    = 0.05,
    correction: str = "bonferroni",
) -> pd.DataFrame:
    """
    Pairwise Mann-Whitney U tests for all group combinations with
    Bonferroni multiple-comparison correction.

    Args:
        df:         Input DataFrame.
        group_col:  Column identifying groups.
        score_col:  Column with ordinal scores.
        alpha:      Significance threshold (before correction).
        correction: "bonferroni" (default) or "none".

    Returns:
        DataFrame with columns: group_a, group_b, u_statistic, p_value,
                                 p_adjusted, significant, effect_r, direction.
    """
    groups  = df[group_col].unique()
    pairs   = list(combinations(groups, 2))
    n_tests = len(pairs)
    rows    = []

    for g_a, g_b in pairs:
        data_a = df[df[group_col] == g_a][score_col].values
        data_b = df[df[group_col] == g_b][score_col].values

        u_stat, p_val = mannwhitneyu(data_a, data_b, alternative="two-sided")

        # Rank-biserial correlation as effect size: r = 1 - (2U / (n_a * n_b))
        n_a, n_b  = len(data_a), len(data_b)
        effect_r  = 1 - (2 * u_stat) / (n_a * n_b) if n_a * n_b > 0 else np.nan

        p_adj = min(p_val * n_tests, 1.0) if correction == "bonferroni" else p_val

        direction = (
            "A > B" if np.median(data_a) > np.median(data_b) else
            "B > A" if np.median(data_b) > np.median(data_a) else
            "equal"
        )

        rows.append({
            "group_a":     g_a,
            "group_b":     g_b,
            "u_statistic": round(u_stat, 2),
            "p_value":     round(p_val, 6),
            "p_adjusted":  round(p_adj, 6),
            "significant": p_adj < alpha,
            "effect_r":    round(effect_r, 4) if not np.isnan(effect_r) else None,
            "direction":   direction,
            "n_a":         n_a,
            "n_b":         n_b,
        })

    result_df = pd.DataFrame(rows)
    logger.info(
        f"Mann-Whitney post-hoc: {n_tests} pairs, "
        f"{result_df['significant'].sum()} significant after {correction} correction."
    )
    return result_df


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------

def plot_score_distributions(
    df: pd.DataFrame,
    group_col: str       = "variant_type",
    score_col: str       = "score",
    facet_col: Optional[str] = "scenario_id",
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    Box + strip plot of score distributions grouped by variant type,
    optionally faceted by scenario.
    """
    sns.set_theme(style="whitegrid", palette="muted")
    order = [v for v in VARIANT_ORDER if v in df[group_col].unique()]

    if facet_col and facet_col in df.columns:
        n_facets = df[facet_col].nunique()
        fig, axes = plt.subplots(
            1, n_facets, figsize=(4 * n_facets, 5), sharey=True
        )
        for ax, (facet_val, sub_df) in zip(
            axes, df.groupby(facet_col)
        ):
            sns.boxplot(
                data=sub_df, x=group_col, y=score_col,
                order=order, palette=SCORE_PALETTE,
                width=0.5, linewidth=1.2, ax=ax, fliersize=3,
            )
            sns.stripplot(
                data=sub_df, x=group_col, y=score_col,
                order=order, color="black", alpha=0.25, size=3,
                jitter=True, ax=ax,
            )
            ax.set_title(facet_val, fontsize=11, fontweight="bold")
            ax.set_xlabel("")
            ax.set_ylabel("Outcome score (1–4)" if ax == axes[0] else "")
            ax.set_ylim(0.5, 4.5)
            ax.set_yticks([1, 2, 3, 4])
            ax.tick_params(axis="x", rotation=30)
    else:
        fig, ax = plt.subplots(figsize=(8, 5))
        sns.boxplot(
            data=df, x=group_col, y=score_col,
            order=order, palette=SCORE_PALETTE,
            width=0.5, linewidth=1.2, ax=ax, fliersize=3,
        )
        sns.stripplot(
            data=df, x=group_col, y=score_col,
            order=order, color="black", alpha=0.25, size=3,
            jitter=True, ax=ax,
        )
        ax.set_xlabel("Variant Type", fontsize=11)
        ax.set_ylabel("Outcome score (1–4)", fontsize=11)
        ax.set_ylim(0.5, 4.5)
        ax.set_yticks([1, 2, 3, 4])
        ax.tick_params(axis="x", rotation=20)

    fig.suptitle(
        "LLM outcome score distributions by stressor variant",
        fontsize=13, fontweight="bold", y=1.01,
    )
    plt.tight_layout()

    out = save_path or str(FIGURES_DIR / "score_distributions.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    logger.info(f"Saved figure: {out}")
    return fig


def plot_heatmap_median_scores(
    df: pd.DataFrame,
    row_col: str   = "scenario_id",
    col_col: str   = "variant_type",
    score_col: str = "score",
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    Heatmap of median outcome scores (scenario x variant_type).
    """
    pivot = (
        df.groupby([row_col, col_col])[score_col]
        .median()
        .unstack(col_col)
        .reindex(columns=[v for v in VARIANT_ORDER
                           if v in df[col_col].unique()])
    )

    fig, ax = plt.subplots(figsize=(8, 5))
    sns.heatmap(
        pivot, annot=True, fmt=".1f", cmap="RdYlGn",
        vmin=1, vmax=4, linewidths=0.5, linecolor="white",
        ax=ax, cbar_kws={"label": "Median outcome score"},
    )
    ax.set_title(
        "Median outcome score: scenario × variant type",
        fontsize=13, fontweight="bold",
    )
    ax.set_xlabel("Variant Type", fontsize=11)
    ax.set_ylabel("Scenario", fontsize=11)
    plt.tight_layout()

    out = save_path or str(FIGURES_DIR / "heatmap_median_scores.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    logger.info(f"Saved heatmap: {out}")
    return fig


# ---------------------------------------------------------------------------
# Full analysis pipeline
# ---------------------------------------------------------------------------

def run_full_analysis(
    df: pd.DataFrame,
    output_csv: Optional[str] = None,
) -> Dict:
    """
    Execute the complete statistical analysis pipeline and return all results.

    Args:
        df:         Scored DataFrame (from scoring_engine).
        output_csv: Optional path to save post-hoc results CSV.

    Returns:
        Dict containing: descriptive, kruskal, posthoc (DataFrame), figures.
    """
    logger.info("Starting full statistical analysis pipeline.")

    desc    = descriptive_stats(df, group_by=["variant_type"])
    kw      = kruskal_wallis_test(df)
    posthoc = mann_whitney_posthoc(df)

    if output_csv:
        posthoc.to_csv(output_csv, index=False)
        logger.info(f"Post-hoc results saved: {output_csv}")

    fig_dist  = plot_score_distributions(df)
    fig_heat  = plot_heatmap_median_scores(df)

    return {
        "descriptive": desc,
        "kruskal":     kw,
        "posthoc":     posthoc,
        "figures":     {"distributions": fig_dist, "heatmap": fig_heat},
    }


if __name__ == "__main__":
    # Smoke test with synthetic data
    rng = np.random.default_rng(42)
    n   = 600
    synthetic = pd.DataFrame({
        "scenario_id":  rng.choice(["S1","S2","S3","S4","S5"], n),
        "variant_type": rng.choice(VARIANT_ORDER, n),
        "provider":     rng.choice(["groq","openai"], n),
        "score":        rng.integers(1, 5, n),
    })
    results = run_full_analysis(synthetic)
    print("\nDescriptive stats:\n", results["descriptive"])
    print("\nKruskal-Wallis:\n",    results["kruskal"])
    print("\nPost-hoc (head):\n",   results["posthoc"].head())
