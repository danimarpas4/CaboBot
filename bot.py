import requests
import json
import random
import os
import time
import urllib.parse
from dotenv import load_dotenv
from datetime import datetime

# ==========================================
# CONFIGURACIÓN
# ==========================================

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = "@testpromilitar" 

if not TOKEN:
    raise ValueError("[CRITICAL] No se encontró TELEGRAM_TOKEN en los Secrets de GitHub")

API_URL = f"https://api.telegram.org/bot{TOKEN}/sendPoll"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FINAL_DB_PATH = os.path.join(BASE_DIR, 'preguntas.json')

# --- CONFIGURACIÓN DE INTENSIDAD ---
# 2 preguntas cada hora = 36 al día.
BATCH_SIZE = 2      
DELAY_SECONDS = 3   

def load_question_ledger():
    if not os.path.exists(FINAL_DB_PATH):
        return []
    try:
        with open(FINAL_DB_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[CRITICAL] Error JSON: {e}")
        return []

def obtener_saludo():
    # 1. Configuración de fechas
    fecha_examen = datetime(2026, 2, 25) 
    hoy = datetime.now()
    dias_restantes = (fecha_examen - hoy).days
    
    # 2. Datos temporales
    hora = (time.gmtime().tm_hour + 1) % 24 
    dia_semana = hoy.weekday() # 0=Lunes, 6=Domingo
    
    # 3. Frases de felicitación nocturna
    felicitaciones = [
        "¡Habéis demostrado una disciplina de hierro hoy! A dormir putos pollos. 🪖",
        "Un día más de estudio es un paso más hacia vuestro objetivo. ¡Grandes! A aguantar al tte.🏆",
        "La constancia es la llave del éxito. ¡Mañana más y mejor! A curtir a esos pollos 💪",
        "Descansad bien, guerreros. El deber de hoy está cumplido. Mañana toca semana de Cabo Cuartel... 🌙",
        "Orgulloso de ver a tantos aspirantes dándolo todo. ¡A por ello pistolos!🎯"
    ]
    
    # 4. Construcción del mensaje BASE (Cuenta Atrás)
    if dias_restantes > 0:
        base_saludo = f"⏳ **CUENTA ATRÁS: ¡Solo quedan {dias_restantes} días para el examen!** 🎯\n\n"
    elif dias_restantes == 0:
        base_saludo = "🔥 **¡HA LLEGADO EL DÍA! Hoy se decide todo. ¡Mucha fuerza, guerreros!** 🪖\n\n"
    else:
        base_saludo = "✅ **Ciclo de examen finalizado. ¡Esperamos vuestros aptos!** 🥂\n\n"
    
    # 5. DETECTAR SI ES FIN DE SEMANA (AÑADIDO NUEVO)
    # Si es Sábado (5) o Domingo (6), añadimos mensaje de motivación extra
    if dia_semana >= 5:
        mensaje_finde = "🚀 **¡FIN DE SEMANA PRE-EXAMEN!**\nMientras otros descansan, nosotros apretamos más, así que ahí va una buena tanda. ¡Sin piedad! 🔥\n\n"
    else:
        mensaje_finde = "" # Entre semana no ponemos nada extra

    # Unimos el mensaje de finde al principio del saludo
    saludo_final = mensaje_finde + base_saludo

    # 6. Saludos por turnos horarios
    if 6 <= hora < 13:
        return saludo_final + "🌅 **Turno de Mañana**: ¡Vamos a por todas!"
    elif 13 <= hora < 16:
        return saludo_final + "☀️ **Turno de Mediodía**: ¡Prohibido rendirse!"
    elif 16 <= hora < 20:
        return saludo_final + "🌆 **Turno de Tarde**: ¡Seguimos sumando!"
    elif 20 <= hora < 23:
        random.seed(time.strftime("%Y%m%d"))
        frase_hoy = random.choice(felicitaciones)
        semilla_unificada = time.strftime("%Y%m%d%H")
        random.seed(semilla_unificada)
        return (f"{saludo_final}🌙 **Turno de Noche**: ¡Último esfuerzo!\n\n"
                f"🏆 **CUADRO DE HONOR**\n"
                f"{frase_hoy}")
    else:
        return "🌙 **Turno de Madrugada**: Estudiando mientras otros duermen. Así se gana. 🪖"

def broadcast_batch():
    questions_pool = load_question_ledger()
    if not questions_pool: return

    # --- NUEVA LÓGICA DE INTENSIDAD (FIN DE SEMANA) ---
    dia_semana = datetime.now().weekday() # 0=Lunes, 6=Domingo
    if dia_semana >= 5:
        lote_actual = 10  # Munición pesada en fin de semana
    else:
        lote_actual = 2   # Munición estándar entre semana

    semilla_unificada = time.strftime("%Y%m%d%H")
    random.seed(semilla_unificada)
    random.shuffle(questions_pool)
    
    # Usamos lote_actual en lugar de BATCH_SIZE
    selected_batch = questions_pool[:lote_actual]

    print(f"[INIT] Enviando lote de {lote_actual} preguntas. Semilla: {semilla_unificada}")
    # ... (el resto de tu código sigue igual)

    # 1. BOTÓN DE COMPARTIR (SALUDO)
    url_invitacion = "https://t.me/testpromilitar" 
    texto_compartir = "🪖 ¡Compañero! Estoy preparando el ascenso con este bot. Envía tests diarios y tiene cuenta atrás para el examen. ¡Únete aquí!"
    texto_encoded = urllib.parse.quote(texto_compartir)
    link_final = f"https://t.me/share/url?url={url_invitacion}&text={texto_encoded}"

    keyboard_saludo = {
        "inline_keyboard": [[{"text": "📢 RECOMENDAR A UN COMPAÑERO", "url": link_final}]]
    }

    # 2. ENVIAR SALUDO
    saludo = obtener_saludo()
    hora_actual = (time.gmtime().tm_hour + 1) % 24
    es_noche = True if (hora_actual >= 23 or hora_actual < 6) else False

    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
            json={
                "chat_id": CHAT_ID, 
                "text": saludo, 
                "parse_mode": "Markdown",
                "reply_markup": keyboard_saludo,
                "disable_notification": es_noche 
            }
        )
    except Exception as e:
        print(f"[ERROR] No se pudo enviar el saludo: {e}")
    
    # 3. ENVIAR LAS ENCUESTAS
    for index, item in enumerate(selected_batch):
        tema = item.get("titulo_tema", "General")
        icono = "📜" 
        if "Constitución" in tema: icono = "🇪🇸"
        elif "Penal" in tema: icono = "⚖️"
        elif "RROO" in tema or "Reales Ordenanzas" in tema: icono = "🪖"
        elif "Ética" in tema: icono = "🧠"
        elif "Administrativo" in tema: icono = "📂"
        elif "Igualdad" in tema: icono = "🤝"
        elif "Internacional" in tema: icono = "🌍"

        pregunta_formateada = f"{icono} [{tema.upper()}]\n\n{item['pregunta']}"
        pregunta_final = item["pregunta"] if len(pregunta_formateada) > 300 else pregunta_formateada

        payload = {
            "chat_id": CHAT_ID,
            "question": pregunta_final, 
            "options": json.dumps(item["opciones"]),
            "type": "quiz",
            "correct_option_id": item["correcta"],
            "explanation": item.get("explicacion", ""),
            "is_anonymous": True,
            "disable_notification": True
        }

        try:
            requests.post(API_URL, data=payload)
        except Exception: pass
        if index < len(selected_batch) - 1: time.sleep(DELAY_SECONDS)

    # 4. MENSAJE DE CIERRE (1 SOLO BOTÓN)
    time.sleep(DELAY_SECONDS)
    texto_cierre = (
        "🫡 **Objetivo cumplido por esta hora.**\n\n"
        "Si te están sirviendo estos tests, no seas caimán y pásalo a tu binomio. "
        "¡Cuantos más seamos, mejor nivel habrá! 👇"
    )

    keyboard_cierre = {
        "inline_keyboard": [[
            {"text": "📤 COMPARTIR AHORA MISMO", "url": link_final}
        ]]
    }

    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
            json={
                "chat_id": CHAT_ID, 
                "text": texto_cierre, 
                "parse_mode": "Markdown",
                "reply_markup": keyboard_cierre,
                "disable_notification": True 
            }
        )
    except Exception: pass

if __name__ == "__main__":
    broadcast_batch()