import json
import random
import os
import logging
import sqlite3
import urllib.parse
from datetime import datetime, time
from zoneinfo import ZoneInfo
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Poll
from telegram.ext import Application, CommandHandler, ContextTypes, PollHandler

# ==========================================
# 1. CONFIGURACIÓN Y BASE DE DATOS
# ==========================================
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = "@testpromilitar" 
ZONA_ESP = ZoneInfo("Europe/Madrid")
FECHA_EXAMEN = datetime(2026, 2, 25, tzinfo=ZONA_ESP)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def init_db():
    conn = sqlite3.connect('stats.db')
    cursor = conn.cursor()
    # Añadimos la columna 'fecha' para filtrar solo lo del día
    cursor.execute('''CREATE TABLE IF NOT EXISTS encuestas 
                      (poll_id TEXT PRIMARY KEY, tema TEXT, aciertos INTEGER, total INTEGER, fecha TEXT)''')
    conn.commit()
    conn.close()

init_db()

with open('preguntas.json', 'r', encoding='utf-8') as f:
    preguntas_oficiales = json.load(f)

# ==========================================
# 2. FRASES Y TEXTOS
# ==========================================
MENSAJES_FALLO = [
    "¡Puto pollo, ponte a estudiar! 🐓",
    "Vas a fregar letrinas con un cepillo de dientes. 🪥",
    "¡Espabila, puto polo!¡50 flexiones, ahora!💪",
    "¿Eso es todo? ¡Repasa el temario! 📚",
    "¡Negativo! Te veo de guardia el finde. 🌙"
]

def obtener_saludo():
    hoy = datetime.now(ZONA_ESP)
    dias = (FECHA_EXAMEN - hoy).days
    hora = hoy.hour
    dia_semana = hoy.weekday()
    
    base = f"⏳ **CUENTA ATRÁS: {dias} días para el examen** 🎯\n\n"
    if dia_semana >= 5:
        mensaje = "🚀 **¡FIN DE SEMANA DE ESTUDIO! (Ráfaga de 10 test)**\n¡Sin piedad! 🔥\n\n"
    else:
        mensaje = ""

    saludo_final = mensaje + base
    if 6 <= hora < 13: return saludo_final + "🌅 **Turno de Mañana**: ¡A por todas!"
    elif 13 <= hora < 20: return saludo_final + "☀️ **Turno de Tarde**: ¡Prohibido rendirse!"
    else: return saludo_final + "🌙 **Turno de Noche**: ¡Último esfuerzo!"

# ==========================================
# 3. LÓGICA DE INTELIGENCIA DIARIA
# ==========================================

async def track_poll_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    poll = update.poll
    if poll.type != Poll.QUIZ: return
    
    aciertos = poll.options[poll.correct_option_id].voter_count
    total = poll.total_voter_count

    conn = sqlite3.connect('stats.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE encuestas SET aciertos = ?, total = ? WHERE poll_id = ?", (aciertos, total, poll.id))
    conn.commit()
    conn.close()

def preparar_texto_informe():
    """Genera el informe filtrando SOLO por la fecha de HOY."""
    hoy_str = datetime.now(ZONA_ESP).strftime('%Y-%m-%d')
    
    conn = sqlite3.connect('stats.db')
    cursor = conn.cursor()
    # Filtramos por fecha
    cursor.execute("SELECT tema, SUM(aciertos), SUM(total) FROM encuestas WHERE fecha = ? GROUP BY tema", (hoy_str,))
    rows = cursor.fetchall()
    conn.close()

    if not rows or sum(row[2] for row in rows) == 0:
        return None # No hay votos hoy

    informe = f"📊 **RESULTADOS DE HOY ({datetime.now(ZONA_ESP).strftime('%d/%m')})** 📊\n"
    informe += "------------------------------------------\n"
    
    t_aciertos, t_votos = 0, 0

    for tema, aciertos, total in rows:
        if total > 0:
            porcentaje = (aciertos / total) * 100
            t_aciertos += aciertos
            t_votos += total
            emoji = "✅" if porcentaje > 70 else "⚠️" if porcentaje > 40 else "❌"
            informe += f"{emoji} *{tema}*: {porcentaje:.1f}% acierto\n"

    media = (t_aciertos / t_votos * 100) if t_votos > 0 else 0
    informe += "------------------------------------------\n"
    informe += f"🎖️ **Rendimiento hoy**: {media:.1f}%\n\n"
    
    if media < 50: informe += "📢 **INSTRUCTOR**: Nivel diario insuficiente. ¡Mañana más disciplina! 🪖"
    else: informe += "📢 **INSTRUCTOR**: Buen trabajo hoy. Rompan filas y a descansar. 🫡"
    
    return informe

async def publicar_resumen_diario(context: ContextTypes.DEFAULT_TYPE):
    texto = preparar_texto_informe()
    if texto:
        await context.bot.send_message(chat_id=CHAT_ID, text=texto, parse_mode="Markdown")

# ==========================================
# 4. LANZADOR DE ENCUESTAS
# ==========================================
url_invitacion = "https://t.me/testpromilitar" 
texto_encoded = urllib.parse.quote("🪖 ¡Compañero! Prepara el ascenso con este bot. Envía tests diarios gratuitos y la cuenta atrás del examen. ¡Únete!")
link_final = f"https://t.me/share/url?url={url_invitacion}&text={texto_encoded}"
keyboard_compartir = InlineKeyboardMarkup([[InlineKeyboardButton("📢 RECOMENDAR A UN COMPAÑERO", url=link_final)]])

async def lanzar_tanda(bot, cantidad):
    await bot.send_message(chat_id=CHAT_ID, text=obtener_saludo(), reply_markup=keyboard_compartir, parse_mode="Markdown")
    
    hoy_str = datetime.now(ZONA_ESP).strftime('%Y-%m-%d')
    batch = random.sample(preguntas_oficiales, cantidad)
    
    for p in batch:
        try:
            tema = p.get("titulo_tema", "General").upper()
            pregunta = f"📜 [{tema}]\n\n{p['pregunta']}"
            if len(pregunta) > 300: pregunta = p['pregunta'][:300]

            explicacion = f"{p.get('explicacion', '')}\n\n⚠️ Si has fallado: {random.choice(MENSAJES_FALLO)}"
            if len(explicacion) > 200: explicacion = explicacion[:197] + "..."

            msg = await bot.send_poll(
                chat_id=CHAT_ID, question=pregunta, options=[str(opt)[:100] for opt in p['opciones']],
                type='quiz', correct_option_id=int(p['correcta']), explanation=explicacion, is_anonymous=True
            )
            
            # GUARDAMOS LA FECHA ACTUAL
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO encuestas VALUES (?, ?, ?, ?, ?)", (msg.poll.id, tema, 0, 0, hoy_str))
            conn.commit()
            conn.close()
        except Exception: continue

    await bot.send_message(chat_id=CHAT_ID, text="🫡 **Objetivo cumplido.**", reply_markup=keyboard_compartir, parse_mode="Markdown")

# ==========================================
# 5. AUTOMATISMOS Y MAIN
# ==========================================
async def enviar_batch_automatico(context: ContextTypes.DEFAULT_TYPE):
    ahora = datetime.now(ZONA_ESP)
    if ahora.weekday() >= 5:
        if ahora.hour not in [10, 14, 18, 22]: return
        await lanzar_tanda(context.bot, 10)
    else:
        await lanzar_tanda(context.bot, 2)

def main():
    app = Application.builder().token(TOKEN).build()
    
    ahora = datetime.now(ZONA_ESP)
    segundos_hasta_en_punto = 3600 - (ahora.minute * 60 + ahora.second)
    app.job_queue.run_repeating(enviar_batch_automatico, interval=3600, first=segundos_hasta_en_punto)
    
    # Resumen diario a las 23:00
    app.job_queue.run_daily(publicar_resumen_diario, time=time(23, 0, tzinfo=ZONA_ESP))
    
    app.add_handler(CommandHandler("disparar", lambda u, c: lanzar_tanda(c.bot, 2)))
    app.add_handler(CommandHandler("informe", lambda u, c: u.message.reply_text(preparar_texto_informe() or "Aún no hay votos hoy.", parse_mode="Markdown")))
    app.add_handler(PollHandler(track_poll_results))
    
    print(f"🚀 Informe DIARIO (23:00) activo. Sincronizado en {segundos_hasta_en_punto // 60} min.")
    app.run_polling()

if __name__ == '__main__':
    main()