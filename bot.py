import requests
import json
import random
import os

# --- TU CONFIGURACIÓN ---
TOKEN = "8129111913:AAGnlOkGLZ4Ds3zYVWgSiIJV4n05wGT4Ry0" # ¡Asegúrate de que es el correcto!
CHAT_ID = "@testpromilitar" # O el ID numérico si es privado

# Obtener la ruta absoluta del archivo JSON (para evitar errores al ejecutar con cron)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_JSON = os.path.join(BASE_DIR, 'preguntas.json')

def cargar_preguntas():
    try:
        with open(RUTA_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ Error: No encuentro el archivo preguntas.json")
        return []

def enviar_pregunta_aleatoria():
    lista_preguntas = cargar_preguntas()
    
    if not lista_preguntas:
        return

    # Elegimos una al azar
    pregunta_elegida = random.choice(lista_preguntas)
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendPoll"
    
    payload = {
        "chat_id": CHAT_ID,
        "question": pregunta_elegida["pregunta"],
        "options": json.dumps(pregunta_elegida["opciones"]),
        "type": "quiz",
        "correct_option_id": pregunta_elegida["correcta"],
        "explanation": pregunta_elegida["explicacion"],
        "is_anonymous": True
    }

    print(f"Enviando pregunta: {pregunta_elegida['pregunta']}...")
    
    response = requests.post(url, data=payload)
    
    if response.status_code == 200:
        print("✅ ¡Enviada con éxito!")
    else:
        print(f"❌ Error: {response.text}")

if __name__ == "__main__":
    enviar_pregunta_aleatoria()