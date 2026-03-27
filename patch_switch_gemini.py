with open("src/experiment_runner.py", "r", encoding="utf-8") as f:
    data = f.read()

# Llama auskommentieren, Gemini aktivieren
data = data.replace("(Provider.GITHUB, \"meta-llama-3.1-8b-instruct\"),", "# (Provider.GITHUB, \"meta-llama-3.1-8b-instruct\"),")
data = data.replace("# (Provider.GEMINI, \"gemini-2.5-flash\"),", "(Provider.GEMINI, \"gemini-2.5-flash\"),")

with open("src/experiment_runner.py", "w", encoding="utf-8") as f:
    f.write(data)

print("Modell erfolgreich auf Gemini 2.5 Flash gewechselt!")
