# Handoff: optimaler Studienlauf & was außerhalb des Codes bleibt

## Bereits im Code (automatisch nutzbar)

| Thema | Umsetzung |
|--------|-----------|
| Weniger Rauschen | `EXPERIMENT_TEMPERATURE = 0.2` in `experiment_runner.py` |
| Nachvollziehbarkeit | `run_id`, `temperature`, `user_prompt_chars`, `system_prompt_chars`, `response_chars`, Token-Zähler in JSONL → CSV (`scoring_engine`) |
| Ein Run isolieren | `$env:SCORING_RUN_ID="<8-stellig>"` vor `scoring_engine.py` |
| Paraphrase-Leaks (optional) | `$env:LEAK_JUDGE="1"` + API-Key |
| Post-hoc zu RQ1 | `plot_scored_results.py` ruft **Mann–Whitney neutral vs. authority/time/combined** auf (global + **pro Szenario**, **Holm** über 15 Tests) |
| Dunn (optional) | Nach signifikantem Kruskal–Wallis, wenn `scikit-posthocs` installiert (`requirements.txt`) |
| Prompt-Längen-Transparenz | `cd src` → `python prompt_audit.py` (Tabelle + Warnung bei >15 % Abweichung der User-Prompt-Länge von neutral) |

## Checkliste vor dem Großlauf

1. **`pip install -r requirements.txt`** (neu: `scikit-posthocs` für Dunn).
2. **`.env`** mit gültigem Key (z. B. `OPENROUTER_API_KEY`).
3. **`experiment_runner.py`**: `TARGET_MODELS` wie geplant setzen (ein Modell nach dem anderen oder parallel, je nach Budget).
4. **Smoke**: `$env:BENCHMARK_SMOKE="1"; python experiment_runner.py` → dann Scoring ohne Filter testen.
5. **Pilot**: optional `LEAK_JUDGE` auf Stichprobe; Kosten beachten.
6. **Produktiv**: `BENCHMARK_SMOKE` **nicht** setzen, vollen Lauf starten, `run_id` aus Log/Manifest notieren.
7. **Scoring**: `$env:SCORING_RUN_ID="<id>"; python scoring_engine.py` (empfohlen, damit die CSV nur dieser Lauf ist).
8. **Figuren + Tests**: `python plot_scored_results.py`.
9. **Längen-Audit**: `python prompt_audit.py` → bei großen Abweichungen im **Methoden-Text** ehrlich diskutieren oder Prompts in `prompts_config.py` anpassen (manuell/inhaltlich).

## Muss außerhalb des Repos / manuell passieren (nicht automatisierbar)

| Aufgabe | Warum |
|---------|--------|
| **Stichprobe (~100 Antworten) manuell gegen Rubrik prüfen** | Schätzung von False Positives/Negatives beim Regex-/Judge-Scoring; Pflicht für starke Aussagen zur Validität. |
| **Längen-äquivalente Baseline** | Code liefert nur **Metriken** (`prompt_audit`, Spalten in CSV); inhaltliches Angleichen der Neutral-Prompts an Stressor-Länge ist **fachliche** Entscheidung + Textarbeit. |
| **Begriffe RQ ↔ Code** | z. B. „partial compliance“ in der Fragestellung vs. „partial refusal“ im Code — im Text explizit verknüpfen. |
| **Modellvergleich fair darstellen** | Herstellerangaben, Kontextfenster, Kosten; keine reine „OS vs. proprietary“-Story ohne Limitationen. |
| **Pre-Registration / Ethik** | falls von der Hochschule gefordert. |
| **Diskussion Limitationen** | synthetische Szenarien ≠ Produktiv-RAG; Generalisierung vorsichtig formulieren. |

## Kurz-Befehle (PowerShell, aus `src`)

```powershell
pip install -r ..\requirements.txt
python prompt_audit.py
# Voll lauf:
python experiment_runner.py
$env:SCORING_RUN_ID="xxxxxxxx"
python scoring_engine.py
python plot_scored_results.py
```

Optional Leak-Judge beim Scoring:

```powershell
$env:LEAK_JUDGE="1"
python scoring_engine.py
```
