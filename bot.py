import requests
import json
import random
import os
import time
from dotenv import load_dotenv

# ==========================================
# CONFIGURATION & CONSTANTS
# ==========================================

# Cargamos variables de entorno desde el archivo .env
load_dotenv()

# Recuperamos el TOKEN del .env para máxima seguridad
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = "@testpromilitar"

# Si no hay token, el bot no arranca (evita errores silenciosos)
if not TOKEN:
    raise ValueError("[CRITICAL] No se encontró TELEGRAM_TOKEN en el archivo .env")

# Telegram API Endpoint
API_URL = f"https://api.telegram.org/bot{TOKEN}/sendPoll"

# Resolución de rutas (Ruta absoluta para evitar errores con GitHub Actions o Cron)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Selección inteligente de base de datos:
# Si existe preguntas.json lo usa; si no, usa la demo pública.
DB_PATH = os.path.join(BASE_DIR, 'preguntas.json')
DEMO_PATH = os.path.join(BASE_DIR, 'preguntas_demo.json')

FINAL_DB_PATH = DB_PATH if os.path.exists(DB_PATH) else DEMO_PATH

# Configuración del lote
BATCH_SIZE = 3      # Número de preguntas a enviar por ejecución
DELAY_SECONDS = 3   # Buffer para evitar el baneo por flood (HTTP 429)

def load_question_ledger():
    """
    Carga el conjunto de datos de preguntas desde el almacenamiento JSON.
    """
    try:
        with open(FINAL_DB_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            db_name = os.path.basename(FINAL_DB_PATH)
            print(f"[INFO] Ledger '{db_name}' cargado. Registros totales: {len(data)}")
            return data
    except FileNotFoundError:
        print(f"[CRITICAL] No se encontró base de datos en: {FINAL_DB_PATH}")
        return []
    except json.JSONDecodeError:
        print("[CRITICAL] Formato JSON corrupto en la base de datos.")
        return []

def broadcast_batch():
    """
    Lógica principal: Selecciona un lote aleatorio y lo envía al canal.
    """
    questions_pool = load_question_ledger()
    
    # Comprobación de liquidez del pool
    if not questions_pool:
        print("[WARN] El pool está vacío. Abortando misión.")
        return

    # Selección aleatoria sin repetición en el mismo lote
    sample_size = min(BATCH_SIZE, len(questions_pool))
    selected_batch = random.sample(questions_pool, sample_size)

    print(f"[INIT] Iniciando envío de {sample_size} preguntas...")

    # Bucle de envío
    for index, item in enumerate(selected_batch):
        # Construcción del Payload para la API de Telegram
        payload = {
            "chat_id": CHAT_ID,
            "question": item["pregunta"],
            "options": json.dumps(item["opciones"]),
            "type": "quiz",
            "correct_option_id": item["correcta"],
            "explanation": item["explicacion"],
            "is_anonymous": True 
        }

        try:
            # Ejecución de la petición HTTP POST
            response = requests.post(API_URL, data=payload)
            
            # Verificación de éxito (HTTP 200 OK)
            if response.status_code == 200:
                print(f"[SUCCESS] Pregunta {index + 1}/{sample_size} enviada con éxito.")
            else:
                print(f"[ERROR] Error al enviar bloque {index + 1}. Respuesta API: {response.text}")
                
        except Exception as e:
            print(f"[EXCEPTION] Error de red durante la transmisión: {e}")

        # Control de flujo (Rate Limiting)
        # Esencial para no saturar los servidores de Telegram
        if index < sample_size - 1:
            time.sleep(DELAY_SECONDS)

    print("[DONE] Ejecución del lote completada.")

if __name__ == "__main__":
    broadcast_batch()