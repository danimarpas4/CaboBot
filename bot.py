import requests
import json
import random
import os
import time
from dotenv import load_dotenv

# ==========================================
# CONFIGURATION & CONSTANTS
# ==========================================

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = "@testpromilitar" # Asegúrate de que este es tu canal real

if not TOKEN:
    raise ValueError("[CRITICAL] No se encontró TELEGRAM_TOKEN en los Secrets de GitHub")

API_URL = f"https://api.telegram.org/bot{TOKEN}/sendPoll"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ÚNICA FUENTE DE DATOS: preguntas.json
FINAL_DB_PATH = os.path.join(BASE_DIR, 'preguntas.json')

BATCH_SIZE = 3      # Número de preguntas por envío
DELAY_SECONDS = 3   # Pausa entre preguntas

def load_question_ledger():
    # Verificamos si existe el archivo real. Si no, cerramos.
    if not os.path.exists(FINAL_DB_PATH):
        print(f"[CRITICAL] No se encuentra el archivo {FINAL_DB_PATH}. El bot no enviará nada.")
        return []

    try:
        with open(FINAL_DB_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(f"[CRITICAL] Error leyendo el archivo JSON: {e}")
        return []

def broadcast_batch():
    questions_pool = load_question_ledger()
    
    if not questions_pool:
        return

    # --- LÓGICA ANTI-REPETICIÓN ---
    # Semilla basada en la fecha para que el orden cambie cada día
    dia_actual = time.strftime("%Y%m%d")
    random.seed(dia_actual)
    
    # Barajamos todo el temario real
    random.shuffle(questions_pool)

    # Seleccionamos el lote de hoy
    selected_batch = questions_pool[:BATCH_SIZE]

    print(f"[INIT] Enviando lote real del día: {dia_actual}")

    for index, item in enumerate(selected_batch):
        payload = {
            "chat_id": CHAT_ID,
            "question": item["pregunta"],
            "options": json.dumps(item["opciones"]),
            "type": "quiz",
            "correct_option_id": item["correcta"],
            "explanation": item.get("explicacion", ""),
            "is_anonymous": True 
        }

        try:
            response = requests.post(API_URL, data=payload)
            if response.status_code == 200:
                print(f"[SUCCESS] Pregunta {index + 1} enviada.")
            else:
                print(f"[ERROR] API de Telegram: {response.text}")
        except Exception as e:
            print(f"[EXCEPTION] Error de conexión: {e}")

        if index < len(selected_batch) - 1:
            time.sleep(DELAY_SECONDS)

    print("[DONE] Proceso finalizado.")

if __name__ == "__main__":
    broadcast_batch()