import json
import sqlite3
import random
import os
import logging
import urllib.parse
from datetime import datetime, time as dt_time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ==========================================
# 1. CONFIGURACIÓN (MANTENIDA)
# ==========================================
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = "@testpromilitar" 
FECHA_EXAMEN = datetime(2026, 2, 25)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

with open('preguntas.json', 'r', encoding='utf-8') as f:
    preguntas_oficiales = json.load(f)

# ==========================================
# 2. BASE DE DATOS (ESTADÍSTICAS)
# ==========================================
def init_db():
    conn = sqlite3.connect('ranking.db')
    cursor = conn.cursor()
    # Tabla histórica
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios 
                      (user_id INTEGER PRIMARY KEY, nombre TEXT, puntos_totales INTEGER DEFAULT 0)''')
    # Tabla para el resumen diario
    cursor.execute('''CREATE TABLE IF NOT EXISTS diario 
                      (user_id INTEGER PRIMARY KEY, nombre TEXT, aciertos_hoy INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

def registrar_acierto(user_id, nombre):
    conn = sqlite3.connect('ranking.db')
    cursor = conn.cursor()
    # Puntos totales
    cursor.execute('''INSERT INTO usuarios (user_id, nombre, puntos_totales) VALUES (?, ?, 1) 
                      ON CONFLICT(user_id) DO UPDATE SET puntos_totales = puntos_totales + 1, nombre = ?''', (user_id, nombre, nombre))
    # Aciertos del día
    cursor.execute('''INSERT INTO diario (user_id, nombre, aciertos_hoy) VALUES (?, ?, 1) 
                      ON CONFLICT(user_id) DO UPDATE SET aciertos_hoy = aciertos_hoy + 1, nombre = ?''', (user_id, nombre, nombre))
    conn.commit()
    conn.close()

# ==========================================
# 3. LÓGICA ORIGINAL (SALUDOS E ICONOS)
# ==========================================
def obtener_saludo():
    hoy = datetime.now()
    dias_restantes = (FECHA_EXAMEN - hoy).days
    hora = hoy.hour
    dia_semana = hoy.weekday()
    
    base_saludo = f"⏳ **CUENTA ATRÁS: ¡Solo quedan {dias_restantes} días!** 🎯\n\n"
    mensaje_finde = "🚀 **¡FIN DE SEMANA PRE-EXAMEN!**\n" if dia_semana >= 5 else ""
    
    if 6 <= hora < 13: turno = "🌅 Turno de Mañana"
    elif 13 <= hora < 20: turno = "☀️ Turno de Tarde"
    else: turno = "🌙 Turno de Noche"
    
    return f"{mensaje_finde}{base_saludo}{turno}"

def get_icono(tema):
    tema = tema.lower()
    if "constitución" in tema: return "🇪🇸"
    if "penal" in tema: return "⚖️"
    if "rroo" in tema or "reales" in tema: return "🪖"
    if "ética" in tema: return "🧠"
    return "📜"

# ==========================================
# 4. ENVÍO AUTOMÁTICO (HORARIOS MANTENIDOS)
# ==========================================
async def enviar_batch_automatico(context: ContextTypes.DEFAULT_TYPE):
    ahora = datetime.now()
    dia_semana = ahora.weekday()
    hora_actual = ahora.hour

    # Lógica de intensidad original
    if dia_semana >= 5: # Sábado o Domingo
        if hora_actual not in [10, 14, 18, 22]: return
        lote_actual = 10
    else: # Lunes a Viernes
        lote_actual = 2

    batch = random.sample(preguntas_oficiales, lote_actual)
    
    # Enviar saludo al canal
    await context.bot.send_message(chat_id=CHAT_ID, text=obtener_saludo(), parse_mode="Markdown")

    for p in batch:
        # Generar botones para rastrear estadísticas (en lugar de encuestas anónimas)
        keyboard = []
        for i, opt in enumerate(p['opciones']):
            es_correcta = "SI" if i == p['correcta'] else "NO"
            # Guardamos la info del acierto y el índice de la pregunta
            callback_data = f"v|{es_correcta}|{p.get('id', 'x')}"
            keyboard.append([InlineKeyboardButton(opt, callback_data=callback_data)])

        icono = get_icono(p.get("titulo_tema", ""))
        texto = f"{icono} *{p.get('titulo_tema', 'TEMA')}*\n\n❓ {p['pregunta']}"
        
        await context.bot.send_message(
            chat_id=CHAT_ID, 
            text=texto, 
            reply_markup=InlineKeyboardMarkup(keyboard), 
            parse_mode="Markdown"
        )

    # Mensaje de cierre con link de compartir (Original)
    texto_cierre = "🫡 **Objetivo cumplido por esta hora.**\nSi te sirven estos tests, ¡pásalo a tu binomio!"
    kb_cierre = [[InlineKeyboardButton("📤 COMPARTIR", url="https://t.me/share/url?url=t.me/testpromilitar")]]
    await context.bot.send_message(chat_id=CHAT_ID, text=texto_cierre, reply_markup=InlineKeyboardMarkup(kb_cierre), parse_mode="Markdown")

# ==========================================
# 5. GESTIÓN DE VOTOS Y RANKING
# ==========================================
async def manejar_voto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("|")
    
    if data[0] == "v":
        es_correcta = data[1]
        user_id = query.from_user.id
        nombre = query.from_user.first_name

        if es_correcta == "SI":
            registrar_acierto(user_id, nombre)
            await query.answer(f"✅ ¡Correcto, {nombre}! +1 punto.")
        else:
            await query.answer(f"❌ Fallo. ¡Sigue dándole caña!", show_alert=False)

async def enviar_resumen_diario(context: ContextTypes.DEFAULT_TYPE):
    """Envía el Top 5 del día a las 23:59 y resetea"""
    conn = sqlite3.connect('ranking.db')
    cursor = conn.cursor()
    cursor.execute('SELECT nombre, aciertos_hoy FROM diario ORDER BY aciertos_hoy DESC LIMIT 5')
    top = cursor.fetchall()
    
    if top:
        mensaje = "📊 **RESUMEN DE OPERACIONES (HOY)** 📊\n\n"
        medallas = ["🥇", "🥈", "🥉", "🎖️", "🎖️"]
        for i, (nom, pts) in enumerate(top):
            mensaje += f"{medallas[i]} {nom}: {pts} aciertos\n"
        
        await context.bot.send_message(chat_id=CHAT_ID, text=mensaje, parse_mode="Markdown")
        cursor.execute('DELETE FROM diario') # Reset diario
        conn.commit()
    conn.close()

async def ver_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /ranking para ver el histórico"""
    conn = sqlite3.connect('ranking.db')
    cursor = conn.cursor()
    cursor.execute('SELECT nombre, puntos_totales FROM usuarios ORDER BY puntos_totales DESC LIMIT 10')
    rows = cursor.fetchall()
    conn.close()

    texto = "🏆 **CUADRO DE HONOR HISTÓRICO** 🏆\n\n"
    for i, (nom, pts) in enumerate(rows):
        texto += f"{i+1}. {nom} — {pts} pts\n"
    await update.message.reply_text(texto, parse_mode="Markdown")

# ==========================================
# 6. ARRANQUE
# ==========================================
def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    # Tarea 1: Preguntas cada hora (3600 seg)
    app.job_queue.run_repeating(enviar_batch_automatico, interval=3600, first=10)
    
    # Tarea 2: Resumen diario a las 23:59
    app.job_queue.run_daily(enviar_resumen_diario, time=dt_time(23, 59, 0))

    # Handlers
    app.add_handler(CallbackQueryHandler(manejar_voto))
    app.add_handler(CommandHandler("ranking", ver_ranking))

    print("📡 Bot Promilitar. Todo verificado.")
    app.run_polling()

if __name__ == '__main__':
    main()