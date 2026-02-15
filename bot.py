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

with open('preguntas.json', 'r', encoding='utf-8') as f:
    preguntas_oficiales = json.load(f)

# ==========================================
# 2. LOGICA DE TEXTOS Y TURNOS
# ==========================================
def obtener_saludo():
    hoy = datetime.now()
    dias = (FECHA_EXAMEN - hoy).days
    hora = hoy.hour
    dia_semana = hoy.weekday()
    
    if 6 <= hora < 13: turno = "🌅 Turno de Mañana"
    elif 13 <= hora < 20: turno = "☀️ Turno de Tarde"
    else: turno = "🌙 Turno de Noche"
    
    saludo = f"⏳ **CUENTA ATRÁS: ¡Solo quedan {dias} días!** 🎯\n\n"
    
    # Aviso explícito de la ráfaga los fines de semana
    if dia_semana >= 5: 
        saludo = "🚀 **¡FIN DE SEMANA PRE-EXAMEN!** (Ráfaga de 10 test)\n\n" + saludo
    
    return f"{saludo}{turno}\n--------------------------------"

MSG_CIERRE = (
    "✅ **OBJETIVO CUMPLIDO POR HOY**\n\n"
    "📈 Si te están sirviendo los test y quieres apoyar el proyecto, "
    "¡comparte el canal ahora mismo con tus compañeros! 🚀"
)

# ==========================================
# 3. LANZADOR DE ENCUESTAS NATIVAS
# ==========================================
async def lanzar_tanda(bot, cantidad):
    # 1. Saludo
    await bot.send_message(chat_id=CHAT_ID, text=obtener_saludo(), parse_mode="Markdown")
    
    # 2. Encuestas (Quiz)
    batch = random.sample(preguntas_oficiales, cantidad)
    for p in batch:
        tema = p.get('titulo_tema', '').lower()
        icono = "🇪🇸" if "constitución" in tema else "⚖️" if "penal" in tema else "🪖" if "rroo" in tema else "🧠" if "ética" in tema else "📜"
        titulo = f"{icono} TEMA {p.get('tema', '?')}: {p.get('titulo_tema', 'General')}"
        
        await bot.send_poll(
            chat_id=CHAT_ID,
            question=f"{titulo}\n\n{p['pregunta']}",
            options=p['opciones'],
            type='quiz',
            correct_option_id=p['correcta'],
            explanation=p['explicacion'], # La bombilla
            is_anonymous=True # Encuestas nativas anónimas
        )

    # 3. Cierre y botón
    share_url = "https://t.me/share/url?url=https://t.me/testpromilitar&text=¡Echa un vistazo a este canal para preparar el examen de Cabo! 🪖🎖️"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📢 COMPARTIR CANAL", url=share_url)]])
    await bot.send_message(chat_id=CHAT_ID, text=MSG_CIERRE, reply_markup=keyboard, parse_mode="Markdown")

# ==========================================
# 4. HORARIOS Y COMANDOS
# ==========================================
async def enviar_batch_automatico(context: ContextTypes.DEFAULT_TYPE):
    ahora = datetime.now()
    dia_semana = ahora.weekday()
    hora_actual = ahora.hour

    if dia_semana >= 5: # Sábado y Domingo
        if hora_actual not in [10, 14, 18, 22]: 
            return # Si no es esta hora, no hace nada
        await lanzar_tanda(context.bot, 10)
    else: # Lunes a Viernes
        await lanzar_tanda(context.bot, 2)

async def disparar_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando para enviar 2 preguntas al instante y probar que funciona"""
    await lanzar_tanda(context.bot, 2)
    await update.message.reply_text("🚀 ¡Tanda enviada al canal!")

def main():
    app = Application.builder().token(TOKEN).build()
    
    # Tarea automática cada hora
    app.job_queue.run_repeating(enviar_batch_automatico, interval=3600, first=10)
    
    # Comandos
    app.add_handler(CommandHandler("disparar", disparar_manual))
    
    print("🚀 Bot en Modo Encuestas Nativas con Horarios activado.")
    app.run_polling()

if __name__ == '__main__':
    main()