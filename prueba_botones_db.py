import os
import sqlite3
import asyncio
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
import json
with open('preguntas.json', 'r', encoding='utf-8') as f:
    preguntas_oficiales = json.load(f)
    
# --- CONFIGURACIÓN ---
load_dotenv()
TOKEN = "8463196408:AAECBtjfNxBkalNW3TqNk8yEm9eQIp69bo8" 
CHANNEL_ID = "@testpromilitar"

# --- GESTIÓN DE LA BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('bot_stats.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS votos (
            user_id INTEGER,
            message_id INTEGER,
            is_correct INTEGER,
            PRIMARY KEY (user_id, message_id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ranking (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            puntos INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

# --- FUNCIONES DE ENVÍO Y RECEPCIÓN ---
async def enviar_prueba(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pregunta = "¿Cuál es el órgano supremo consultivo del Gobierno?"
    opciones = [
        [InlineKeyboardButton("Consejo de Estado", callback_data="correcta")],
        [InlineKeyboardButton("Tribunal Cuentas", callback_data="incorrecta")],
        [InlineKeyboardButton("Defensor Pueblo", callback_data="incorrecta")]
    ]
    reply_markup = InlineKeyboardMarkup(opciones)
    msg = await context.bot.send_message(chat_id=CHANNEL_ID, text=pregunta, reply_markup=reply_markup)
    await update.message.reply_text(f"🚀 Pregunta enviada. ID: {msg.message_id}")

async def detector_de_votos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    msg_id = query.message.message_id
    es_correcta = 1 if query.data == "correcta" else 0

    conn = sqlite3.connect('bot_stats.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO votos (user_id, message_id, is_correct) VALUES (?, ?, ?)', 
                       (user.id, msg_id, es_correcta))
        cursor.execute('''
            INSERT INTO ranking (user_id, username, puntos) 
            VALUES (?, ?, ?) 
            ON CONFLICT(user_id) DO UPDATE SET 
                puntos = puntos + ?, 
                username = ?
        ''', (user.id, user.first_name, es_correcta, es_correcta, user.first_name))
        conn.commit()
        txt = "✅ ¡Correcto! +1 punto." if es_correcta else "❌ Error. ¡A estudiar!"
        await query.answer(text=txt, show_alert=False)
    except sqlite3.IntegrityError:
        await query.answer(text="⚠️ ¡Negativo! Ya has respondido a esta pregunta.", show_alert=True)
    finally:
        conn.close()

# --- COMANDO: /estadisticas ---
async def ver_estadisticas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect('bot_stats.db')
    cursor = conn.cursor()
    cursor.execute('SELECT puntos FROM ranking WHERE user_id = ?', (user_id,))
    res_puntos = cursor.fetchone()
    puntos = res_puntos[0] if res_puntos else 0
    cursor.execute('SELECT COUNT(*) FROM votos WHERE user_id = ?', (user_id,))
    total_intentos = cursor.fetchone()[0]
    conn.close()

    if total_intentos > 0:
        efectividad = int((puntos / total_intentos) * 100)
        mensaje = (
            f"📊 *HOJA DE SERVICIOS - {update.effective_user.first_name}*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✅ *Aciertos:* {puntos}\n"
            f"❌ *Fallos:* {total_intentos - puntos}\n"
            f"📝 *Total respondidas:* {total_intentos}\n"
            f"🎯 *Efectividad:* {efectividad}%\n"
            f"━━━━━━━━━━━━━━━━━━\n"
        )
    else:
        mensaje = "❌ *Sin registros.*"
    await update.message.reply_text(mensaje, parse_mode='Markdown')

# --- NUEVO COMANDO: /ranking ---
async def ver_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el Top 5 de la academia"""
    conn = sqlite3.connect('bot_stats.db')
    cursor = conn.cursor()
    # Obtenemos el Top 5 ordenado por puntos
    cursor.execute('SELECT username, puntos FROM ranking ORDER BY puntos DESC LIMIT 5')
    top_5 = cursor.fetchall()
    conn.close()

    if not top_5:
        await update.message.reply_text("📭 El Cuadro de Honor está vacío.")
        return

    mensaje = "🏆 *CUADRO DE HONOR - TOP 5* 🏆\n"
    mensaje += "━━━━━━━━━━━━━━━━━━\n"
    medallas = ["🥇", "🥈", "🥉", "🎖️", "🎖️"]
    
    for i, (nombre, puntos) in enumerate(top_5):
        mensaje += f"{medallas[i]} *{nombre}*: {puntos} pts\n"
    
    mensaje += "━━━━━━━━━━━━━━━━━━\n"
    mensaje += "¡Seguid luchando por el primer puesto! 🪖"
    await update.message.reply_text(mensaje, parse_mode='Markdown')

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("test", enviar_prueba))
    app.add_handler(CommandHandler("estadisticas", ver_estadisticas))
    app.add_handler(CommandHandler("ranking", ver_ranking)) # Registro del nuevo comando
    app.add_handler(CallbackQueryHandler(detector_de_votos))
    print("📡 Radar con Ranking y Estadísticas encendido...")
    app.run_polling()

if __name__ == "__main__":
    main()