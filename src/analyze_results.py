import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import kruskal
from pathlib import Path

# Pfade dynamisch setzen
ROOT_DIR = Path(__file__).parent.parent
SCORED_DATA = ROOT_DIR / "data" / "processed" / "scored_results.csv"
FIGURES_DIR = ROOT_DIR / "data" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# Plot-Styling fuer die Bachelorarbeit
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams.update({'font.size': 12, 'pdf.fonttype': 42})

def run_analysis():
    if not SCORED_DATA.exists():
        print(f"Fehler: Datensatz {SCORED_DATA} nicht gefunden.")
        return

    df = pd.read_csv(SCORED_DATA)
    
    print("=== STATISTISCHE ANALYSE (Kruskal-Wallis H-Test) ===")
    models = df['Model'].unique()
    for model in models:
        model_data = df[df['Model'] == model]
        
        # Gruppieren nach Stressor-Variante (V1, V2, V3, V4)
        groups = [group["Compliance_Score"].values for name, group in model_data.groupby("Variant")]
        
        # Kruskal-Wallis Test (da Likert-Skalen ordinal sind)
        if len(groups) > 1:
            stat, p_val = kruskal(*groups)
            print(f"Model: {model}")
            print(f"  -> H-Statistik: {stat:.2f} | p-Wert: {p_val:.4e}")
            if p_val < 0.05:
                print("  -> ERGEBNIS: Signifikanter Compliance Drift durch Stressoren bewiesen!\n")
            else:
                print("  -> ERGEBNIS: Keine signifikante Abweichung (Modell ist robust).\n")

    # === VISUALISIERUNG: Boxplot generieren ===
    print("=== VISUALISIERUNG ===")
    plt.figure(figsize=(12, 6))
    ax = sns.boxplot(
        data=df, 
        x="Variant", 
        y="Compliance_Score", 
        hue="Model",
        showmeans=True,
        meanprops={"marker":"D","markerfacecolor":"white", "markeredgecolor":"black"}
    )
    
    plt.title("Semantic Compliance Drift by Model and Psychological Stressor", fontsize=14, pad=15)
    plt.ylabel("Compliance Score (1=Hard Refusal, 5=Full Compliance)", fontsize=12)
    plt.xlabel("Prompt Variant (V1=Neutral, V2=Authority, V3=Time, V4=Combined)", fontsize=12)
    plt.legend(title="LLM Model", bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    plot_path = FIGURES_DIR / "compliance_drift_boxplot.png"
    plt.savefig(plot_path, dpi=300)
    print(f"Erfolg! Boxplot gespeichert unter: {plot_path}")

if __name__ == "__main__":
    run_analysis()