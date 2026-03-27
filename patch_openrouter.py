with open("src/experiment_runner.py", "r", encoding="utf-8") as f:
    data = f.read()

# Gemma auskommentieren, OpenRouter aktivieren
data = data.replace("(Provider.GEMINI, \"gemma-2-9b-it\"),", "# (Provider.GEMINI, \"gemma-2-9b-it\"),")
data = data.replace("# (Provider.OPENROUTER, \"meta-llama/llama-3.1-8b-instruct:free\"),", "(Provider.OPENROUTER, \"meta-llama/llama-3.1-8b-instruct:free\"),")

with open("src/experiment_runner.py", "w", encoding="utf-8") as f:
    f.write(data)

print("Modell erfolgreich auf OpenRouter (Llama 3.1 Free) gewechselt!")
