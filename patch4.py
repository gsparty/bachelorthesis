with open("src/experiment_runner.py", "r", encoding="utf-8") as f:
    data = f.read()

data = data.replace("\"Meta-Llama-3-8B-Instruct\"", "\"meta-llama-3.1-8b-instruct\"")

with open("src/experiment_runner.py", "w", encoding="utf-8") as f:
    f.write(data)

with open("src/api_client.py", "r", encoding="utf-8") as f:
    data = f.read()

data = data.replace("\"Meta-Llama-3-8B-Instruct\"", "\"meta-llama-3.1-8b-instruct\"")

with open("src/api_client.py", "w", encoding="utf-8") as f:
    f.write(data)

print("GitHub Model String erfolgreich auf Llama 3.1 aktualisiert!")
