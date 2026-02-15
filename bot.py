import json
import sqlite3
import random
import os
import logging
from datetime import datetime, time as dt_time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ==========================================
# 1. CONFIGURACIÓN (TOKEN ORIGINAL)
# ==========================================
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN") # Asegúrate de poner el real en el .env
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
    # Tabla histórica y Tabla diaria (para el resumen nocturno)
    cursor.execute('CREATE TABLE IF NOT EXISTS usuarios (user_id INTEGER PRIMARY KEY, nombre TEXT, puntos INTEGER DEFAULT 0)')
    cursor.execute('CREATE TABLE IF NOT EXISTS diario (user_id INTEGER PRIMARY KEY, nombre TEXT, puntos_hoy INTEGER DEFAULT 0)')
    conn.commit()
    conn.close()

def registrar_punto(user_id, nombre):
    conn = sqlite3.connect('ranking.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO usuarios (user_id, nombre, puntos) VALUES (?, ?, 1) ON CONFLICT(user_id) DO UPDATE SET puntos = puntos + 1, nombre = ?', (user_id, nombre, nombre))
    cursor.execute('INSERT INTO diario (user_id, nombre, puntos_hoy) VALUES (?, ?, 1) ON CONFLICT(user_id) DO UPDATE SET puntos_hoy = puntos_hoy + 1, nombre = ?', (user_id, nombre, nombre))
    conn.commit()
    conn.close()

# ==========================================
# 3. LÓGICA DE SALUDOS E ICONOS (MANTENIDA)
# ==========================================
def obtener_saludo():
    hoy = datetime.now()
    dias_restantes = (FECHA_EXAMEN - hoy).days
    hora = hoy.hour
    dia_semana = hoy.weekday()
    
    saludo = f"⏳ **CUENTA ATRÁS: ¡Solo quedan {dias_restantes} días!** 🎯\n\n"
    if dia_semana >= 5: saludo = "🚀 **¡FIN DE SEMANA PRE-EXAMEN!**\n" + saludo
    
    if 6 <= hora < 13: turno = "🌅 Turno de Mañana"
    elif 13 <= hora < 20: turno = "☀️ Turno de Tarde"
    else: turno = "🌙 Turno de Noche"
    
    return f"{saludo}{turno}"

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

    # Lógica de intensidad (2/hora o 10 en horas clave de finde)
    if dia_semana >= 5:
        if hora_actual not in [10, 14, 18, 22]: return
        lote_actual = 10
    else:
        lote_actual = 2

    batch = random.sample(preguntas_oficiales, lote_actual)
    await context.bot.send_message(chat_id=CHAT_ID, text=obtener_saludo(), parse_mode="Markdown")

    for item in batch:
        # Usamos botones para poder trackear quién acierta
        keyboard = []
        for i, opt in enumerate(item['opciones']):
            # callback_data: SI/NO | ID_PREGUNTA
            es_correcta = "S" if i == item['correcta'] else "N"
            keyboard.append([InlineKeyboardButton(opt, callback_data=f"v|{es_correcta}")])

        icono = get_icono(item.get("titulo_tema", ""))
        texto = f"{icono} *{item.get('titulo_tema', 'TEMA')}*\n\n❓ {item['pregunta']}"
        await context.bot.send_message(chat_id=CHAT_ID, text=texto, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ==========================================
# 5. GESTIÓN DE VOTOS Y RESUMEN DIARIO
# ==========================================
async def manejar_voto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("|")
    if data[0] == "v":
        es_correcta = data[1]
        if es_correcta == "S":
            registrar_punto(query.from_user.id, query.from_user.first_name)
            await query.answer("✅ ¡Correcto! +1 punto.")
        else:
            await query.answer("❌ Error. ¡Sigue estudiando!")

async def resumen_diario(context: ContextTypes.DEFAULT_TYPE):
    """Envía el podio del día a las 23:59"""
    conn = sqlite3.connect('ranking.db')
    cursor = conn.cursor()
    cursor.execute('SELECT nombre, puntos_hoy FROM diario ORDER BY puntos_hoy DESC LIMIT 5')
    top = cursor.fetchall()
    
    if top:
        mensaje = "📊 **OPERACIONES DEL DÍA: CUADRO DE HONOR** 📊\n\n"
        medallas = ["🥇", "🥈", "🥉", "🎖️", "🎖️"]
        for i, (nom, pts) in enumerate(top):
            mensaje += f"{medallas[i]} {nom}: {pts} aciertos\n"
        await context.bot.send_message(chat_id=CHAT_ID, text=mensaje, parse_mode="Markdown")
        cursor.execute('DELETE FROM diario') # Limpiar para mañana
        conn.commit()
    conn.close()

async def ranking_total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /ranking para ver el histórico total"""
    conn = sqlite3.connect('ranking.db')
    cursor = conn.cursor()
    cursor.execute('SELECT nombre, puntos FROM usuarios ORDER BY puntos DESC LIMIT 10')
    top = cursor.fetchall()
    conn.close()
    
    txt = "🏆 **RANKING HISTÓRICO PROMILITAR** 🏆\n\n"
    for i, (nom, pts) in enumerate(top):
        txt += f"{i+1}. {nom} — {pts} pts\n"
    await update.message.reply_text(txt, parse_mode="Markdown")

# ==========================================
# 6. ARRANQUE
# ==========================================
def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    
    # Tareas automáticas
    app.job_queue.run_repeating(enviar_batch_automatico, interval=3600, first=10)
    app.job_queue.run_daily(resumen_diario, time=dt_time(23, 59, 0))

    # Handlers
    app.add_handler(CallbackQueryHandler(manejar_voto))
    app.add_handler(CommandHandler("ranking", ranking_total))

    print("🚀 Bot Maestro en marcha. VPS configurado.")
    app.run_polling()

if __name__ == '__main__':
    main()