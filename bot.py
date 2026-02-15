import json
import random
import os
import logging
import urllib.parse
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
# 2. FRASES MILITARES Y TEXTOS CLÁSICOS
# ==========================================
MENSAJES_FALLO = [
    "¡Puto pollo, ponte a estudiar o te vas a enterar! 🐓",
    "Vas a fregar las letrinas con un cepillo de dientes. 🪥",
    "¡50 flexiones, ahora mismo! ¡Espabila, recluta! 💪",
    "¿Eso es todo lo que tienes? ¡Más te vale repasar el temario! 📚",
    "¡Negativo! Te veo de guardia todo el fin de semana. 🌙",
    "¡Error! ¡Dale caña que te quedas sin los galones! 🔥"
]

def obtener_saludo():
    hoy = datetime.now()
    dias_restantes = (FECHA_EXAMEN - hoy).days
    hora = hoy.hour
    dia_semana = hoy.weekday()
    
    # 1. Cuenta Atrás
    if dias_restantes > 0:
        base_saludo = f"⏳ **CUENTA ATRÁS: ¡Solo quedan {dias_restantes} días para el examen!** 🎯\n\n"
    elif dias_restantes == 0:
        base_saludo = "🔥 **¡HA LLEGADO EL DÍA! Hoy se decide todo. ¡Mucha fuerza, guerreros!** 🪖\n\n"
    else:
        base_saludo = "✅ **Ciclo de examen finalizado. ¡Esperamos vuestros aptos!** 🥂\n\n"

    # 2. Fin de semana
    if dia_semana >= 5:
        mensaje_finde = "🚀 **¡FIN DE SEMANA DE ESTUDIO!**\nMientras otros descansan, nosotros apretamos. ¡Sin piedad! 🔥\n\n"
    else:
        mensaje_finde = ""

    saludo_final = mensaje_finde + base_saludo

    # 3. Frases de felicitación nocturna
    felicitaciones = [
        "¡Habéis demostrado una disciplina de hierro hoy! A dormir putos pollos. 🪖",
        "Un día más de estudio es un paso más hacia vuestro objetivo. ¡Grandes! A aguantar al tte.🏆",
        "La constancia es la llave del éxito. ¡Mañana más y mejor! A curtir a esos pollos 💪",
        "Descansad bien, guerreros. El deber de hoy está cumplido. Mañana toca semana de Cabo Cuartel... 🌙",
        "Orgulloso de ver a tantos aspirantes dándolo todo. ¡A por ello pistolos!🎯"
    ]

    # 4. Turnos horarios
    if 6 <= hora < 13:
        return saludo_final + "🌅 **Turno de Mañana**: ¡Vamos a por todas!"
    elif 13 <= hora < 16:
        return saludo_final + "☀️ **Turno de Mediodía**: ¡Prohibido rendirse!"
    elif 16 <= hora < 20:
        return saludo_final + "🌆 **Turno de Tarde**: ¡Seguimos sumando!"
    elif 20 <= hora < 24:
        frase_hoy = random.choice(felicitaciones)
        return f"{saludo_final}🌙 **Turno de Noche**: ¡Último esfuerzo!\n\n🏆 **CUADRO DE HONOR**\n{frase_hoy}"
    else:
        return saludo_final + "🌙 **Turno de Madrugada**: Estudiando mientras otros duermen. Así se gana. 🪖"

# ==========================================
# 3. ENLACES DE COMPARTIR Y CIERRE
# ==========================================
url_invitacion = "https://t.me/testpromilitar" 
texto_compartir = "🪖 ¡Compañero! Estoy preparando el ascenso con este bot. Envía tests diarios y tiene cuenta atrás para el examen. ¡Únete aquí!"
texto_encoded = urllib.parse.quote(texto_compartir)
link_final = f"https://t.me/share/url?url={url_invitacion}&text={texto_encoded}"

MSG_CIERRE = (
    "🫡 **Objetivo cumplido por ahora.**\n\n"
    "Si te están sirviendo estos tests, no seas caimán y pásalo a tu binomio. "
    "¡Cuantos más seamos, mejor nivel habrá! 👇"
)

# Teclado que usaremos tanto en el saludo como en el cierre
keyboard_compartir = InlineKeyboardMarkup([[InlineKeyboardButton("📢 RECOMENDAR A UN COMPAÑERO", url=link_final)]])

# ==========================================
# 4. LANZADOR DE ENCUESTAS BLINDADO
# ==========================================
async def lanzar_tanda(bot, cantidad):
    # --- 1. MENSAJE INICIAL (CON BOTÓN DE COMPARTIR) ---
    await bot.send_message(
        chat_id=CHAT_ID, 
        text=obtener_saludo(), 
        reply_markup=keyboard_compartir, 
        parse_mode="Markdown"
    )
    
    # --- 2. ENCUESTAS (CON LÍMITES DE TELEGRAM CONTROLADOS) ---
    batch = random.sample(preguntas_oficiales, cantidad)
    for p in batch:
        try:
            tema = p.get("titulo_tema", "General")
            icono = "📜" 
            if "Constitución" in tema or "constitución" in tema.lower(): icono = "🇪🇸"
            elif "Penal" in tema or "penal" in tema.lower(): icono = "⚖️"
            elif "RROO" in tema or "Reales Ordenanzas" in tema or "rroo" in tema.lower(): icono = "🪖"
            elif "Ética" in tema or "ética" in tema.lower(): icono = "🧠"
            elif "Administrativo" in tema or "administrativo" in tema.lower(): icono = "📂"
            elif "Igualdad" in tema or "igualdad" in tema.lower(): icono = "🤝"
            elif "Internacional" in tema or "internacional" in tema.lower(): icono = "🌍"

            pregunta_formateada = f"{icono} [{tema.upper()}]\n\n{p['pregunta']}"
            pregunta_final = pregunta_formateada if len(pregunta_formateada) <= 300 else p['pregunta'][:300]

            bronca = random.choice(MENSAJES_FALLO)
            explicacion_base = p.get('explicacion', '')
            explicacion_completa = f"{explicacion_base}\n\n💡 Nota: {bronca}"
            
            if len(explicacion_completa) > 200:
                explicacion_completa = explicacion_completa[:197] + "..."

            opciones_seguras = [str(opt)[:100] for opt in p['opciones']]

            await bot.send_poll(
                chat_id=CHAT_ID,
                question=pregunta_final,
                options=opciones_seguras,
                type='quiz',
                correct_option_id=int(p['correcta']),
                explanation=explicacion_completa,
                is_anonymous=True
            )
        except Exception as e:
            logging.error(f"Error en encuesta: {e}")
            continue

    # --- 3. MENSAJE FINAL (TAMBIÉN CON EL BOTÓN) ---
    await bot.send_message(
        chat_id=CHAT_ID, 
        text=MSG_CIERRE, 
        reply_markup=keyboard_compartir, 
        parse_mode="Markdown"
    )

# ==========================================
# 5. AUTOMATISMOS Y COMANDOS
# ==========================================
async def enviar_batch_automatico(context: ContextTypes.DEFAULT_TYPE):
    ahora = datetime.now()
    dia_semana = ahora.weekday()
    hora_actual = ahora.hour

    if dia_semana >= 5: # Fines de semana (10 test)
        if hora_actual not in [10, 14, 18, 22]: 
            return
        await lanzar_tanda(context.bot, 10)
    else: # Diario (2 test)
        await lanzar_tanda(context.bot, 2)

async def disparar_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await lanzar_tanda(context.bot, 2)
    await update.message.reply_text("🚀 ¡Tanda enviada! A ver si no son muy caimanes.")

def main():
    app = Application.builder().token(TOKEN).build()
    app.job_queue.run_repeating(enviar_batch_automatico, interval=3600, first=10)
    app.add_handler(CommandHandler("disparar", disparar_manual))
    
    print("🚀 Bot Fusión Total (Blindado) en marcha.")
    app.run_polling()

if __name__ == '__main__':
    main()