"""
analyze_results.py
==================
Console summary per model (Kruskal–Wallis across prompt variants) plus full figure pipeline
(stacked bars, boxplot, heatmap, chi-square & Welch t-tests) via plot_scored_results.
"""

from pathlib import Path

from scipy.stats import kruskal

from plot_scored_results import SCORED_DATA, load_scored_df, run_all_plots_and_tests


def run_analysis():
    if not SCORED_DATA.exists():
        print(f"Fehler: Datensatz {SCORED_DATA} nicht gefunden.")
        return

    df = load_scored_df()

    print("=== Kruskal–Wallis: je Modell über variant_id ===")
    for model in sorted(df["model"].unique()):
        model_data = df[df["model"] == model]
        groups = [
            g["score"].values
            for _, g in model_data.groupby("variant_id")
            if len(g) > 0
        ]
        if len(groups) > 1:
            stat, p_val = kruskal(*groups)
            print(f"Model: {model}")
            print(f"  -> H={stat:.2f}, p={p_val:.4e}")
            if p_val < 0.05:
                print("  -> Signifikant: Verteilungen über Prompt-Varianten unterscheiden sich.\n")
            else:
                print("  -> Nicht signifikant (robust über Varianten).\n")

    print("=== Abbildungen & Tests (stacked bar, boxplot, heatmap, chi2, t-Tests) ===")
    run_all_plots_and_tests()


if __name__ == "__main__":
    run_analysis()
