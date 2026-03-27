import re

with open("src/experiment_runner.py", "r", encoding="utf-8") as f:
    data = f.read()

# 1. Change repetitions to 30
data = re.sub(r"N_REPETITIONS:\s*int\s*=\s*\d+", "N_REPETITIONS: int = 30", data)

# 2. Update TARGET_MODELS to only include GitHub Llama-3.1
old_targets = r"TARGET_MODELS:\s*List\[Tuple\[Provider,\s*str\]\]\s*=\s*\[.*?\]"
new_targets = """TARGET_MODELS: List[Tuple[Provider, str]] = [
    (Provider.GITHUB, "meta-llama-3.1-8b-instruct"),
]"""
data = re.sub(old_targets, new_targets, data, flags=re.DOTALL)

with open("src/experiment_runner.py", "w", encoding="utf-8") as f:
    f.write(data)

print("Ready for the main run! N_REPETITIONS = 30, Target = GitHub Llama-3.1")
