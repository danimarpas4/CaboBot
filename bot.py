import json
import random
import os
import logging
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ==========================================
# 1. CONFIGURACIÓN
# ==========================================
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = "@testpromilitar" 
FECHA_EXAMEN = datetime(2026, 2, 25)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Cargamos tus preguntas desde el JSON
with open('preguntas.json', 'r', encoding='utf-8') as f:
    preguntas_oficiales = json.load(f)

# ==========================================
# 2. LÓGICA DE TIEMPO Y MENSAJES
# ==========================================
def obtener_saludo():
    hoy = datetime.now()
    dias = (FECHA_EXAMEN - hoy).days
    hora = hoy.hour
    
    if 6 <= hora < 13: turno = "🌅 Turno de Mañana"
    elif 13 <= hora < 20: turno = "☀️ Turno de Tarde"
    else: turno = "🌙 Turno de Noche"
    
    return (
        f"⏳ **CUENTA ATRÁS: ¡Solo quedan {dias} días!** 🎯\n\n"
        f"{turno}\n"
        f"--------------------------------"
    )

MSG_CIERRE = (
    "✅ **OBJETIVO CUMPLIDO POR HOY**\n\n"
    "📈 Si te están sirviendo los test y quieres apoyar el proyecto, "
    "¡comparte el canal ahora mismo con tus compañeros! 🚀"
)

# ==========================================
# 3. ENVÍO DE ENCUESTAS (VISUALES)
# ==========================================
async def lanzar_tanda(bot, cantidad):
    # 1. Saludo inicial con cuenta atrás
    await bot.send_message(chat_id=CHAT_ID, text=obtener_saludo(), parse_mode="Markdown")

    # 2. Bloque de encuestas tipo Quiz
    batch = random.sample(preguntas_oficiales, cantidad)
    for p in batch:
        tema = p.get('titulo_tema', '').lower()
        # Seleccionamos icono según el tema
        icono = "🇪🇸" if "constitución" in tema else "⚖️" if "penal" in tema else "🪖" if "rroo" in tema else "🧠" if "ética" in tema else "📜"
        
        titulo = f"{icono} TEMA {p.get('tema', '?')}: {p.get('titulo_tema', 'General')}"
        
        await bot.send_poll(
            chat_id=CHAT_ID,
            question=f"{titulo}\n\n{p['pregunta']}",
            options=p['opciones'],
            type='quiz',
            correct_option_id=p['correcta'],
            explanation=p['explicacion'], # Aquí sale la "bombilla" con la explicación
            is_anonymous=True
        )

    # 3. Mensaje de cierre con botón de compartir
    share_url = "https://t.me/share/url?url=https://t.me/testpromilitar&text=¡Echa un vistazo a este canal para preparar el examen de Cabo! 🪖🎖️"
    keyboard_cierre = InlineKeyboardMarkup([[InlineKeyboardButton("📢 COMPARTIR CANAL", url=share_url)]])

    await bot.send_message(
        chat_id=CHAT_ID, 
        text=MSG_CIERRE, 
        reply_markup=keyboard_cierre, 
        parse_mode="Markdown"
    )

# ==========================================
# 4. AUTOMATISMOS Y COMANDOS
# ==========================================
async def enviar_batch_automatico(context: ContextTypes.DEFAULT_TYPE):
    ahora = datetime.now()
    if ahora.weekday() >= 5: # Fines de semana
        if ahora.hour not in [10, 14, 18, 22]: return
        await lanzar_tanda(context.bot, 10)
    else: # Diario
        await lanzar_tanda(context.bot, 2)

async def disparar_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await lanzar_tanda(context.bot, 2)
    await update.message.reply_text("🚀 Tanda de encuestas enviada.")

def main():
    app = Application.builder().token(TOKEN).build()
    
    # Tareas automáticas cada hora
    app.job_queue.run_repeating(enviar_batch_automatico, interval=3600, first=10)

    # Comando para lanzar a mano
    app.add_handler(CommandHandler("disparar", disparar_manual))

    print("🚀 Bot de Encuestas Nativas (Modo Visual) en marcha.")
    app.run_polling()

if __name__ == '__main__':
    main()