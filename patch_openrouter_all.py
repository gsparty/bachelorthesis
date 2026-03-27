import re

with open("src/experiment_runner.py", "r", encoding="utf-8") as f:
    data = f.read()

new_targets = """TARGET_MODELS: List[Tuple[Provider, str]] = [
    # WICHTIG: Lass immer nur EIN Modell unkommentiert (ohne '#'). 
    # Wenn ein Lauf (600 Prompts) fertig ist, kommentierst du es aus und nimmst das naechste.

    # 1. Meta (Dein aktueller Lauf)
    (Provider.OPENROUTER, "meta-llama/llama-3.1-8b-instruct"),
    
    # 2. Microsoft (Klein, aber extrem auf Sicherheit trainiert)
    # (Provider.OPENROUTER, "microsoft/phi-3.5-mini-128k-instruct"),
    
    # 3. Google (Open-Weights Modell, super Vergleich zu Llama)
    # (Provider.OPENROUTER, "google/gemma-2-9b-it"),
    
    # 4. OpenAI (Der Industrie-Standard fuer Agenten)
    # (Provider.OPENROUTER, "openai/gpt-4o-mini"),
]"""
data = re.sub(r"TARGET_MODELS:\s*List\[Tuple\[Provider,\s*str\]\]\s*=\s*\[.*?\]", new_targets, data, flags=re.DOTALL)

with open("src/experiment_runner.py", "w", encoding="utf-8") as f:
    f.write(data)

print("OpenRouter Modell-Matrix erfolgreich in experiment_runner.py integriert!")
