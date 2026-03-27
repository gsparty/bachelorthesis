import re

with open("src/experiment_runner.py", "r", encoding="utf-8") as f:
    data = f.read()

old_targets = r"TARGET_MODELS:\s*List\[Tuple\[Provider,\s*str\]\]\s*=\s*\[.*?\]"
new_targets = """TARGET_MODELS: List[Tuple[Provider, str]] = [
    (Provider.GEMINI, "gemini-2.5-flash"),
    (Provider.GITHUB, "Meta-Llama-3-8B-Instruct"),
]"""

data = re.sub(old_targets, new_targets, data, flags=re.DOTALL)

with open("src/experiment_runner.py", "w", encoding="utf-8") as f:
    f.write(data)

print("Target Models für Smoke Test (Gemini & GitHub Llama-3) konfiguriert!")
