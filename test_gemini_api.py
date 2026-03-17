import json
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

# 1. Chemin vers le fichier JSON
SERVICE_ACCOUNT_FILE = "gen-lang-client-0690325988-81883e510a60.json"

# 2. Charger le JSON depuis le fichier
try:
    with open(SERVICE_ACCOUNT_FILE, "r") as f:
        service_account_info = json.load(f)
    print(f"✅ Fichier JSON chargé: {service_account_info['project_id']}")
except FileNotFoundError:
    print(f"❌ Fichier {SERVICE_ACCOUNT_FILE} introuvable. Place-le dans le même dossier.")
    exit(1)

# 3. Créer les credentials
SCOPES = ["https://www.googleapis.com/auth/generative-language"]
credentials = service_account.Credentials.from_service_account_info(
    service_account_info, 
    scopes=SCOPES
)

# 4. Récupérer l'access token
request = Request()
credentials.refresh(request)
print(f"✅ Credentials créées: {credentials}")
exit()
access_token = credentials.token
print(f"✅ Access token obtenu: {access_token[:20]}...")

# 5. Tester Gemini 2.5 Flash
MODEL = "gemini-2.5-flash"
url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

payload = {
    "contents": [{
        "role": "user",
        "parts": [{"text": "Test connexion : une blague sur les data engineers en français."}]
    }]
}

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

response = requests.post(url, headers=headers, json=payload)

print(f"\n📡 Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print("✅ Réponse Gemini 2.0 Flash:")
    print(result["candidates"][0]["content"]["parts"][0]["text"])
else:
    print("❌ Erreur:", response.text)
