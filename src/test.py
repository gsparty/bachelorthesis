import requests

def fetch_all_openrouter_models():
    response = requests.get("https://openrouter.ai/api/v1/models")
    if response.status_code == 200:
        models = response.json().get("data", [])
        
        # Save to a text file for easy searching
        with open("available_models.txt", "w", encoding="utf-8") as f:
            for model in models:
                f.write(f"{model['id']}\n")
                
        print(f"Successfully saved {len(models)} active model IDs to 'available_models.txt'!")
    else:
        print(f"Failed to fetch models. HTTP Status: {response.status_code}")

fetch_all_openrouter_models()