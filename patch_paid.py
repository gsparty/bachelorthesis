import re

with open("src/experiment_runner.py", "r", encoding="utf-8") as f:
    data = f.read()

# 1. Das Paid-Modell bei OpenRouter aktivieren (ohne :free)
data = re.sub(r"TARGET_MODELS:\s*List\[Tuple\[Provider,\s*str\]\]\s*=\s*\[.*?\]", """TARGET_MODELS: List[Tuple[Provider, str]] = [
    (Provider.OPENROUTER, "meta-llama/llama-3.1-8b-instruct"),
]""", data, flags=re.DOTALL)

# 2. Die langsame Bremse entfernen (Paid Tiers vertragen Vollgas)
old_finally = """                finally:
                    import asyncio
                    await asyncio.sleep(4.1) # Diese Bremse greift IMMER, auch bei Fehlern!"""
data = data.replace(old_finally, "")

with open("src/experiment_runner.py", "w", encoding="utf-8") as f:
    f.write(data)

print("Skript ist nun auf den schnellen Paid-Tier von OpenRouter konfiguriert!")
