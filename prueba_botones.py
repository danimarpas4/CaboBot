import os
import asyncio
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

# Cargar suministros (Token y Canal)
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = "@testpromilitar" # Asegúrate de que este es tu canal

async def enviar_prueba(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envía una pregunta con botones al canal"""
    pregunta = "¿Cuál es la capital de España?"
    opciones = [
        [InlineKeyboardButton("Madrid", callback_data="correcta")],
        [InlineKeyboardButton("Barcelona", callback_data="incorrecta")],
        [InlineKeyboardButton("Sevilla", callback_data="incorrecta")]
    ]
    reply_markup = InlineKeyboardMarkup(opciones)
    
    # Enviamos el mensaje al canal
    await context.bot.send_message(chat_id=CHANNEL_ID, text=pregunta, reply_markup=reply_markup)
    await update.message.reply_text("🚀 ¡Misil enviado al canal! Ve a probarlo.")

async def detector_de_votos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Este es el 'chivato': detecta quién pulsa y qué pulsa"""
    query = update.callback_query
    user = query.from_user # ¡Aquí capturamos al recluta!
    
    # 1. Informamos en la terminal (Lo que tú verás)
    print(f"✅ ¡IMPACTO DETECTADO!")
    print(f"   - Recluta: {user.first_name} (@{user.username})")
    print(f"   - ID: {user.id}")
    print(f"   - Voto: {query.data}")
    print("-" * 30)

    # 2. Le respondemos al usuario con un mensaje flotante
    mensaje = "¡Correcto! +1 punto a tu historial." if query.data == "correcta" else "¡Fallo! Sigue estudiando."
    await query.answer(text=mensaje, show_alert=False)

def main():
    app = Application.builder().token(TOKEN).build()
    
    # Comandos
    app.add_handler(CommandHandler("test", enviar_prueba))
    app.add_handler(CallbackQueryHandler(detector_de_votos))
    
    print("📡 Radar encendido... Escribe /test en el chat privado del bot.")
    app.run_polling()

if __name__ == "__main__":
    main()