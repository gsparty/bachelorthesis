import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Pfade
ROOT_DIR = Path(__file__).parent.parent
SCORED_DATA = ROOT_DIR / "data" / "processed" / "scored_results.csv"
FIGURES_DIR = ROOT_DIR / "data" / "figures"
FORENSICS_FILE = ROOT_DIR / "data" / "processed" / "jailbreak_forensics.txt"

def run_deep_analysis():
    df = pd.read_csv(SCORED_DATA)
    
    # 1. HEATMAP: Modell vs. Szenario (Wo sind die Schwachstellen?)
    print("=== Generiere Schwachstellen-Heatmap ===")
    
    # Durchschnittlichen Score pro Modell und Szenario berechnen
    pivot_df = df.pivot_table(
        values="score",
        index="model",
        columns="scenario_id",
        aggfunc="mean",
    )
    
    plt.figure(figsize=(10, 6))
    sns.heatmap(pivot_df, annot=True, cmap="YlOrRd", vmin=1, vmax=4, fmt=".2f")
    plt.title("Vulnerability Heatmap: Models vs. Scenarios (mean outcome score)")
    plt.ylabel("LLM Model")
    plt.xlabel("Scenario (S1=M&A, S2=HR, S3=Cyber, S4=AML, S5=Legal)")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    heatmap_path = FIGURES_DIR / "vulnerability_heatmap.png"
    plt.savefig(heatmap_path, dpi=300)
    print(f"Heatmap gespeichert unter: {heatmap_path}\n")

    # 2. FORENSIK: Daten-Lecks (Score 4)
    print("=== Extrahiere Data-Leak-Fälle (score == 4) ===")
    jailbreaks = df[df["score"] == 4]
    
    with open(FORENSICS_FILE, "w", encoding="utf-8") as f:
        f.write(f"=== DATA LEAK FORENSICS (Total: {len(jailbreaks)}) ===\n\n")
        
        for model in jailbreaks["model"].unique():
            f.write(f"=========================================\n")
            f.write(f"MODEL: {model}\n")
            f.write(f"=========================================\n")
            
            model_jbs = jailbreaks[jailbreaks["model"] == model].head(5)
            for _, row in model_jbs.iterrows():
                f.write(f"SCENARIO: {row['scenario_id']} | VARIANT: {row['variant_id']}\n")
                f.write(f"PROMPT:\n{row['prompt']}\n")
                f.write(f"RESPONSE:\n{row['response']}\n")
                f.write("-" * 40 + "\n")

    print(f"Forensik-Daten gespeichert unter: {FORENSICS_FILE}")
    print("-> LIES DIR DIESE DATEI DURCH, UM DIE VERHALTENSMUSTER ZU VERSTEHEN!")

if __name__ == "__main__":
    run_deep_analysis()