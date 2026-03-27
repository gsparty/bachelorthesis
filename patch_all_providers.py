import re

# 1. Update api_client.py
with open("src/api_client.py", "r", encoding="utf-8") as f:
    data = f.read()

if "TOGETHER" not in data:
    # Provider Enum erweitern
    data = re.sub(r'class Provider\(str, Enum\):(.*?)GITHUB = "github"', r'class Provider(str, Enum):\1GITHUB = "github"\n    TOGETHER = "together"\n    OPENROUTER = "openrouter"', data, flags=re.DOTALL)
    
    # Provider Config erweitern
    config_addition = """
    Provider.TOGETHER: {
        "base_url": "https://api.together.xyz/v1/chat/completions",
        "api_key_env": "TOGETHER_API_KEY",
        "default_model": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        "requests_per_minute": 60,
    },
    Provider.OPENROUTER: {
        "base_url": "https://openrouter.ai/api/v1/chat/completions",
        "api_key_env": "OPENROUTER_API_KEY",
        "default_model": "meta-llama/llama-3.1-8b-instruct:free",
        "requests_per_minute": 20,
    },"""
    data = re.sub(r'PROVIDER_CONFIG: Dict\[Provider, Dict\[str, Any\]\] = \{', 'PROVIDER_CONFIG: Dict[Provider, Dict[str, Any]] = {' + config_addition, data)

    with open("src/api_client.py", "w", encoding="utf-8") as f:
        f.write(data)

# 2. Update experiment_runner.py
with open("src/experiment_runner.py", "r", encoding="utf-8") as f:
    data = f.read()

new_targets = """TARGET_MODELS: List[Tuple[Provider, str]] = [
    # Wähle IMMER NUR EIN Modell aus (entferne das '#' davor). Sequenzielles Testen ist die sicherste Methode!
    
    # --- ALTERNATIVE B: Together AI (Extrem zuverlässig, 5$ Startguthaben) ---
    (Provider.TOGETHER, "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"),
    # (Provider.TOGETHER, "mistralai/Mistral-Nemo-Instruct-2407"),
    
    # --- ALTERNATIVE C: OpenRouter (Kostenlose Modelle) ---
    # (Provider.OPENROUTER, "meta-llama/llama-3.1-8b-instruct:free"),
    # (Provider.OPENROUTER, "microsoft/phi-3-mini-128k-instruct:free"),
    
    # --- ALTERNATIVE A: Google Gemma 2 (Via Google Key, falls das Limit resetet wurde) ---
    # (Provider.GEMINI, "gemma-2-9b-it"),
]"""
data = re.sub(r"TARGET_MODELS:\s*List\[Tuple\[Provider,\s*str\]\]\s*=\s*\[.*?\]", new_targets, data, flags=re.DOTALL)

with open("src/experiment_runner.py", "w", encoding="utf-8") as f:
    f.write(data)

print("Alle Alternativen (Together, OpenRouter, Gemma) erfolgreich integriert!")
