import requests
import json
import random
import os
import time
import urllib.parse  # Necesario para el enlace de compartir profesional
from dotenv import load_dotenv
from datetime import datetime

# ==========================================
# CONFIGURATION & CONSTANTS
# ==========================================

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = "@testpromilitar" 

if not TOKEN:
    raise ValueError("[CRITICAL] No se encontró TELEGRAM_TOKEN en los Secrets de GitHub")

API_URL = f"https://api.telegram.org/bot{TOKEN}/sendPoll"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ÚNICA FUENTE DE DATOS: preguntas.json
FINAL_DB_PATH = os.path.join(BASE_DIR, 'preguntas.json')

BATCH_SIZE = 3      
DELAY_SECONDS = 3   

def load_question_ledger():
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

def obtener_saludo():
    # 1. Configuración de la fecha del examen: 25 de Febrero de 2026
    fecha_examen = datetime(2026, 2, 25) 
    hoy = datetime.now()
    dias_restantes = (fecha_examen - hoy).days
    
    # 2. Lógica de la hora (Madrid UTC+1)
    hora = (time.gmtime().tm_hour + 1) % 24 
    
    # 3. Frases de felicitación nocturna
    felicitaciones = [
        "¡Habéis demostrado una disciplina de hierro hoy! A dormir putos pollos. 🪖",



        "Un día más de estudio es un paso más hacia vuestro objetivo. ¡Grandes! A aguantar al tte.🏆",



        "La constancia es la llave del éxito. ¡Mañana más y mejor! A curtir a esos pollos 💪",



        "Descansad bien, guerreros. El deber de hoy está cumplido. Mañana toca semana de Cabo Cuartel... 🌙",



        "Orgulloso de ver a tantos aspirantes dándolo todo. ¡A por ello pistolos!🎯"
    ]
    
    # 4. Construcción del mensaje de Cuenta Atrás
    if dias_restantes > 0:
        base_saludo = f"⏳ **CUENTA ATRÁS: ¡Solo quedan {dias_restantes} días para el examen!** 🎯\n\n"
    elif dias_restantes == 0:
        base_saludo = "🔥 **¡HA LLEGADO EL DÍA! Hoy se decide todo. ¡Mucha fuerza, guerreros!** 🪖\n\n"
    else:
        base_saludo = "✅ **Ciclo de examen finalizado. ¡Esperamos vuestros aptos!** 🥂\n\n"
    
    # 5. Saludos por turnos
    if 6 <= hora < 13:
        return base_saludo + "🌅 **Turno de Mañana**: Aquí tenéis las preguntas de hoy."
    elif 13 <= hora < 16:
        return base_saludo + "☀️ **Turno de Mediodía**: ¡Aprovechad el descanso para repasar!"
    elif 16 <= hora < 20:
        return base_saludo + "🌆 **Turno de Tarde**: ¡Vamos con otra tanda de estudio!"
    elif 20 <= hora < 23:
        random.seed(time.strftime("%Y%m%d"))
        frase_hoy = random.choice(felicitaciones)
        
        # Reset de semilla para las preguntas siguientes
        semilla_unificada = time.strftime("%Y%m%d%H")
        random.seed(semilla_unificada)
        
        return (f"{base_saludo}🌙 **Turno de Noche**: ¡Último esfuerzo del día!\n\n"
                f"🏆 **CUADRO DE HONOR**\n"
                f"{frase_hoy}")
    else:
        return "🌙 **Turno de Madrugada**: Estudiando mientras otros duermen. Así se gana. 🪖"

def broadcast_batch():
    questions_pool = load_question_ledger()
    
    if not questions_pool:
        return

    # --- LÓGICA ANTI-REPETICIÓN ---
    semilla_unificada = time.strftime("%Y%m%d%H")
    random.seed(semilla_unificada)
    
    random.shuffle(questions_pool)
    selected_batch = questions_pool[:BATCH_SIZE]

    print(f"[INIT] Enviando lote real con semilla: {semilla_unificada}")

    # 1. CONFIGURACIÓN DEL BOTÓN PROFESIONAL DE COMPARTIR
    url_invitacion = "https://t.me/testpromilitar" 
    texto_compartir = "🪖 ¡Compañero! Estoy preparando el ascenso con este bot. Envía tests diarios y tiene cuenta atrás para el examen. ¡Únete aquí!"
    
    # Codificamos el texto para que funcione correctamente en la URL de Telegram
    texto_encoded = urllib.parse.quote(texto_compartir)
    link_final = f"https://t.me/share/url?url={url_invitacion}&text={texto_encoded}"

    keyboard = {
        "inline_keyboard": [[
            {
                "text": "📢 RECOMENDAR A UN COMPAÑERO",
                "url": link_final
            }
        ]]
    }

    # 2. ENVIAR SALUDO CON EL BOTÓN Y MODO SILENCIOSO EN NOCHE/MADRUGADA
    saludo = obtener_saludo()
    hora_actual = (time.gmtime().tm_hour + 1) % 24
    
    # Si es de noche (23h a 06h), enviamos sin notificación
    notificacion_desactivada = True if (hora_actual >= 23 or hora_actual < 6) else False

    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
            json={
                "chat_id": CHAT_ID, 
                "text": saludo, 
                "parse_mode": "Markdown",
                "reply_markup": keyboard,
                "disable_notification": notificacion_desactivada
            }
        )
    except Exception as e:
        print(f"[ERROR] No se pudo enviar el saludo: {e}")
    
    # 3. ENVIAR LAS ENCUESTAS
    for index, item in enumerate(selected_batch):
        payload = {
            "chat_id": CHAT_ID,
            "question": item["pregunta"],
            "options": json.dumps(item["opciones"]),
            "type": "quiz",
            "correct_option_id": item["correcta"],
            "explanation": item.get("explicacion", ""),
            "is_anonymous": True,
            "disable_notification": notificacion_desactivada
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

def enviar_informe_semanal():
    questions = load_question_ledger()
    total = len(questions)
    # 21 preguntas al día (3 preguntas x 7 turnos)
    mensaje = f"📊 **INFORME SEMANAL CABOBOT**\n\n✅ Tienes {total} preguntas en total.\n⏳ Al ritmo actual, tienes temario para {total // 21} días más."
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                      data={"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"})
    except Exception as e:
        print(f"[ERROR] No se pudo enviar el informe: {e}")

if __name__ == "__main__":
    broadcast_batch()