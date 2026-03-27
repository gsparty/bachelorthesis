"""
Post-hoc tests aligned with RQ1: neutral baseline vs. each stressor type.

- Global: Mann–Whitney U on ordinal scores (neutral vs authority / time_pressure / combined).
- Per scenario: same, with Holm–Bonferroni across all 5×3 = 15 comparisons.

Requires columns: variant_type, score; optional scenario_id for per-scenario block.
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu


def holm_adjusted_pvalues(pvals: List[float]) -> np.ndarray:
    """Holm–Bonferroni adjusted p-values (two-sided tests)."""
    p = np.asarray(pvals, dtype=float)
    m = len(p)
    if m == 0:
        return p
    order = np.argsort(p)
    s = p[order]
    # Step-up adjusted: q_i = max_{k<=i} min(1, (m-k) * s_k) in 0-based sorted order
    tmp = np.array([min(1.0, (m - i) * s[i]) for i in range(m)], dtype=float)
    adj_sorted = np.maximum.accumulate(tmp)
    out = np.empty(m)
    out[order] = adj_sorted
    return out


def _mwu(a: np.ndarray, b: np.ndarray) -> Tuple[float, float]:
    if len(a) < 1 or len(b) < 1:
        return float("nan"), float("nan")
    stat, p = mannwhitneyu(a, b, alternative="two-sided")
    return float(stat), float(p)


def print_mwu_vs_neutral_global(df: pd.DataFrame) -> pd.DataFrame:
    """Pairwise MWU: neutral vs each non-neutral variant_type (pooled over scenarios)."""
    stressors = ["authority", "time_pressure", "combined"]
    rows = []
    p_raw: List[float] = []
    base = df.loc[df["variant_type"] == "neutral", "score"].astype(int).values
    for vt in stressors:
        sub = df.loc[df["variant_type"] == vt, "score"].astype(int).values
        u_stat, p_val = _mwu(base, sub)
        rows.append(
            {
                "contrast": f"neutral vs {vt}",
                "n_neutral": len(base),
                "n_other": len(sub),
                "u_statistic": u_stat,
                "p_raw": p_val,
            }
        )
        p_raw.append(p_val)
    adj = holm_adjusted_pvalues(p_raw)
    for i, r in enumerate(rows):
        r["p_holm"] = adj[i]
    out = pd.DataFrame(rows)
    print("\n=== Mann–Whitney U: neutral vs stressor (global, Holm-adjusted) ===")
    print(out.to_string(index=False))
    return out


def print_mwu_vs_neutral_by_scenario(df: pd.DataFrame) -> pd.DataFrame:
    """MWU neutral vs each stressor within each scenario_id; Holm over 15 tests."""
    if "scenario_id" not in df.columns:
        print("\n(scenario_id missing — skip per-scenario post-hoc.)")
        return pd.DataFrame()

    stressors = ["authority", "time_pressure", "combined"]
    scenarios = sorted(df["scenario_id"].dropna().unique())
    rows = []
    p_raw: List[float] = []

    for scen in scenarios:
        d = df[df["scenario_id"] == scen]
        base = d.loc[d["variant_type"] == "neutral", "score"].astype(int).values
        for vt in stressors:
            sub = d.loc[d["variant_type"] == vt, "score"].astype(int).values
            u_stat, p_val = _mwu(base, sub)
            rows.append(
                {
                    "scenario_id": scen,
                    "contrast": f"neutral vs {vt}",
                    "n_neutral": len(base),
                    "n_other": len(sub),
                    "u_statistic": u_stat,
                    "p_raw": p_val,
                }
            )
            p_raw.append(p_val)

    if not rows:
        return pd.DataFrame()

    adj = holm_adjusted_pvalues(p_raw)
    for i, r in enumerate(rows):
        r["p_holm"] = adj[i]
    out = pd.DataFrame(rows)
    print("\n=== Mann–Whitney U: neutral vs stressor by scenario (Holm over all contrasts) ===")
    print(out.to_string(index=False))
    return out


def try_print_dunn(df: pd.DataFrame, group_col: str = "variant_type") -> None:
    """Optional Dunn test after Kruskal–Wallis (needs scikit-posthocs)."""
    try:
        import scikit_posthocs as sp  # type: ignore
    except ImportError:
        print(
            "\n(Dunn test skipped — install optional: pip install scikit-posthocs)"
        )
        return
    try:
        dunn = sp.posthoc_dunn(
            df,
            val_col="score",
            group_col=group_col,
            p_adjust="holm",
        )
        print(f"\n=== Dunn post-hoc (Holm-adjusted), {group_col} ===")
        print(dunn.round(4).to_string())
    except Exception as exc:
        print(f"\n(Dunn test failed: {exc})")
