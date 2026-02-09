import requests
import json
import random
import os
import time

# ==========================================
# CONFIGURATION & CONSTANTS
# ==========================================
# TODO: In a production environment, use os.getenv('TELEGRAM_TOKEN') for security.
TOKEN = "8129111913:AAGnlOkGLZ4Ds3zYVWgSiIJV4n05wGT4Ry0" 
CHAT_ID = "@testpromilitar"

# Telegram API Endpoint
API_URL = f"https://api.telegram.org/bot{TOKEN}/sendPoll"

# File paths resolution (Absolute path to avoid cron execution errors)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'preguntas.json')

# Batch configuration
BATCH_SIZE = 3      # Number of questions to broadcast per execution
DELAY_SECONDS = 3   # Rate limiting buffer to avoid API throttling (HTTP 429)

def load_question_ledger():
    """
    Loads the question dataset from the JSON storage.
    Returns: List of dictionary objects or empty list on failure.
    """
    try:
        with open(DB_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"[INFO] Ledger loaded successfully. Total records: {len(data)}")
            return data
    except FileNotFoundError:
        print(f"[CRITICAL] Database file not found at: {DB_PATH}")
        return []
    except json.JSONDecodeError:
        print("[CRITICAL] Corrupted JSON format in database.")
        return []

def broadcast_batch():
    """
    Main execution logic: Selects a random batch and broadcasts to the network (Telegram).
    """
    questions_pool = load_question_ledger()
    
    # Check for empty pool (Liquidity check)
    if not questions_pool:
        print("[WARN] Pool is empty. Aborting transaction.")
        return

    # Select random batch (Non-repeating sample)
    # Safe-guard: If pool < BATCH_SIZE, take all available items.
    sample_size = min(BATCH_SIZE, len(questions_pool))
    selected_batch = random.sample(questions_pool, sample_size)

    print(f"[INIT] Starting broadcast of {sample_size} questions...")

    # Broadcast Loop
    for index, item in enumerate(selected_batch):
        # Construct the payload
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
            # Execute HTTP POST request
            response = requests.post(API_URL, data=payload)
            
            # Verify status code (200 OK)
            if response.status_code == 200:
                print(f"[SUCCESS] Block {index + 1}/{sample_size} mined and sent.")
            else:
                print(f"[ERROR] Failed to send Block {index + 1}. API Response: {response.text}")
                
        except Exception as e:
            print(f"[EXCEPTION] Network error during transmission: {e}")

        # Rate Limiting (Sleep)
        # Essential to prevent banning from Telegram servers
        if index < sample_size - 1:
            time.sleep(DELAY_SECONDS)

    print("[DONE] Batch execution completed.")

if __name__ == "__main__":
    broadcast_batch()