import json, random, os, logging, sqlite3, urllib.parse, asyncio
from datetime import datetime, time
from zoneinfo import ZoneInfo
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Poll
from telegram.ext import Application, CommandHandler, ContextTypes, PollHandler
from dotenv import load_dotenv

# Carga de variables de entorno
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = "@testpromilitar" 
ZONA_ESP = ZoneInfo("Europe/Madrid")
FECHA_EXAMEN = datetime(2026, 2, 25, tzinfo=ZONA_ESP)

# Configuración de Logs
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('stats.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS encuestas 
                      (poll_id TEXT PRIMARY KEY, tema TEXT, aciertos INTEGER, 
                       total INTEGER, fecha TEXT, pregunta_texto TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- CARGA DE PREGUNTAS ---
with open('preguntas.json', 'r', encoding='utf-8') as f:
    preguntas_oficiales = json.load(f)

# --- CONFIGURACIÓN DE COMPARTIR ---
url_privada = "https://t.me/+c0fMDCCvFs42YWVk"
texto_compartir = (
    "¡Compañero! Te paso este canal de test gratuitos para preparar al ascenso a Cabo. "
    "Envían preguntas cada hora, tiene cuenta atrás para el examen y estadísticas diarias de nuestros resultados. "
    "Únete aquí! 👇\n\n"
    f"{url_privada}"
)
link_viral = f"https://t.me/share/url?url=&text={urllib.parse.quote(texto_compartir)}"
keyboard_viral = InlineKeyboardMarkup([[InlineKeyboardButton("🚀 RECOMENDAR A UN COMPAÑERO", url=link_viral)]])

# --- MENSAJE ESPECIAL DÍA DEL EXAMEN ---
async def enviar_mensaje_examen(context):
    mensaje = (
        "🎯 **MENSAJE DE MISIÓN: DÍA DEL EXAMEN** 🎯\n\n"
        "Confía en el proceso. Has estudiado, trabajado y preparado todo de la mejor manera posible. "
        "Hoy es un simulacro más. ¡Confía, el trabajo está hecho! 🪖🚀"
    )
    await context.bot.send_message(chat_id=CHAT_ID, text=mensaje, parse_mode="Markdown")

# --- FUNCIONES DE APOYO ---
def obtener_saludo():
    hoy = datetime.now(ZONA_ESP)
    dias = (FECHA_EXAMEN - hoy).days
    if dias > 0:
        return f"⏳ **CUENTA ATRÁS: Quedan {dias} días para el examen** 🎯\n\n🌅 **¡A por la jornada, aspirante!**"
    elif dias == 0:
        return f"🎯 **¡LLEGÓ EL DÍA!** 🎯\n\nEs el momento de demostrarlo todo. ¡A por ello!"
    return "🚀 **NUEVA CONVOCATORIA EN PREPARACIÓN** 🚀"

async def track_poll_results(update, context):
    poll = update.poll
    if poll.type != Poll.QUIZ or poll.correct_option_id is None: return
    conn = sqlite3.connect('stats.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE encuestas SET aciertos = ?, total = ? WHERE poll_id = ?", 
                   (poll.options[poll.correct_option_id].voter_count, poll.total_voter_count, poll.id))
    conn.commit()
    conn.close()

def preparar_texto_informe():
    hoy_str = datetime.now(ZONA_ESP).strftime('%Y-%m-%d')
    conn = sqlite3.connect('stats.db')
    cursor = conn.cursor()
    cursor.execute("SELECT tema, SUM(aciertos), SUM(total) FROM encuestas WHERE fecha = ? GROUP BY tema", (hoy_str,))
    rows = cursor.fetchall()
    conn.close()
    if not rows or sum(row[2] for row in rows) == 0: return None
    
    informe = f"📊 **PARTE DE NOVEDADES DIARIO ({datetime.now(ZONA_ESP).strftime('%d/%m')})** 📊\n"
    informe += "------------------------------------------\n"
    t_aciertos, t_votos = 0, 0
    for tema, aciertos, total in rows:
        if total > 0:
            porc = (aciertos / total) * 100
            t_aciertos += aciertos
            t_votos += total
            emoji = "✅" if porc > 70 else "⚠️" if porc > 40 else "❌"
            informe += f"{emoji} *{tema}*: {porc:.1f}% éxito\n"
            
    media = (t_aciertos / t_votos * 100) if t_votos > 0 else 0
    informe += "------------------------------------------\n"
    informe += f"🎖️ **Rendimiento Global**: {media:.1f}%\n\n"
    informe += "🫡 **Mañana más y mejor. ¡Descansen!**"
    return informe

# --- ACCIÓN DE LANZAR PREGUNTAS ---
async def lanzar_tanda(bot, cantidad):
    hoy_str = datetime.now(ZONA_ESP).strftime('%Y-%m-%d')
    conn = sqlite3.connect('stats.db')
    cursor = conn.cursor()
    cursor.execute("SELECT pregunta_texto FROM encuestas WHERE fecha = ?", (hoy_str,))
    enviadas_hoy = [row[0] for row in cursor.fetchall()]
    pool_disponible = [p for p in preguntas_oficiales if p['pregunta'] not in enviadas_hoy]
    
    if len(pool_disponible) < cantidad:
        pool_disponible = preguntas_oficiales

    await bot.send_message(chat_id=CHAT_ID, text=obtener_saludo(), reply_markup=keyboard_viral, parse_mode="Markdown")

    for p in random.sample(pool_disponible, min(cantidad, len(pool_disponible))):
        try:
            msg = await bot.send_poll(
                CHAT_ID, 
                question=f"📜 [{p.get('titulo_tema','').upper()}]\n\n{p['pregunta']}"[:300], 
                options=[str(o)[:100] for o in p['opciones']], 
                type='quiz', 
                correct_option_id=int(p['correcta']), 
                explanation=f"{p.get('explicacion','')}"[:190], 
                is_anonymous=True
            )
            cursor.execute("INSERT INTO encuestas VALUES (?, ?, ?, ?, ?, ?)", 
                           (msg.poll.id, p.get('titulo_tema','').upper(), 0, 0, hoy_str, p['pregunta']))
            conn.commit()
        except: continue
    conn.close()
    
    # MENSAJE DE CIERRE RESTAURADO A SU VERSIÓN ORIGINAL
    msg_cierre = "✅ **ENTRENAMIENTO FINALIZADO**\n\nNo dejes a tus compañeros atrás. Comparte el canal para ayudarnos entre nosotros. 👇"
    await bot.send_message(chat_id=CHAT_ID, text=msg_cierre, reply_markup=keyboard_viral, parse_mode="Markdown")

# --- PROGRAMACIÓN DE TAREAS ---
async def enviar_batch_automatico(context):
    ahora = datetime.now(ZONA_ESP)
    if ahora.date() == FECHA_EXAMEN.date(): return
    if not (6 <= ahora.hour <= 22): return 
    
    cantidad = 10 if ahora.weekday() >= 5 else 2
    await lanzar_tanda(context.bot, cantidad)

async def cierre_jornada(context):
    ahora = datetime.now(ZONA_ESP)
    if ahora.date() == FECHA_EXAMEN.date(): return
    
    # 1. Lanzar la última tanda
    await lanzar_tanda(context.bot, 10 if ahora.weekday() >= 5 else 2)
    
    # 2. Esperar un momento para asegurar el orden y enviar estadísticas
    await asyncio.sleep(2)
    informe = preparar_texto_informe()
    await context.bot.send_message(chat_id=CHAT_ID, text=informe or "Hoy no ha habido actividad registrada.", parse_mode="Markdown")

def main():
    app = Application.builder().token(TOKEN).build()
    ahora = datetime.now(ZONA_ESP)
    
    segundos_hasta_en_punto = 3600 - (ahora.minute * 60 + ahora.second)
    app.job_queue.run_repeating(enviar_batch_automatico, interval=3600, first=segundos_hasta_en_punto)
    
    # Tanda final + Estadísticas a las 23:00
    app.job_queue.run_daily(cierre_jornada, time=time(23, 0, tzinfo=ZONA_ESP))

    # Mensaje motivación día examen
    fecha_motivacion = datetime(2026, 2, 25, 7, 0, tzinfo=ZONA_ESP)
    if ahora < fecha_motivacion:
        app.job_queue.run_once(enviar_mensaje_examen, when=fecha_motivacion)
    
    app.add_handler(CommandHandler("disparar", lambda u, c: lanzar_tanda(c.bot, 2)))
    app.add_handler(CommandHandler("test_cierre", lambda u, c: cierre_jornada(c)))
    app.add_handler(PollHandler(track_poll_results))
    
    print("🚀 Bot en guardia. Mensaje de cierre restaurado.")
    app.run_polling()

if __name__ == '__main__': main()