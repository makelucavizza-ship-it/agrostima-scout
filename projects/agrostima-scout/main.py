import sys
import os
import asyncio
import logging
import threading
from datetime import datetime
from pathlib import Path

# Path setup — aggiunge la root del monorepo a sys.path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / '.env')

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr

from apscheduler.schedulers.background import BackgroundScheduler

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes,
)

from core.db import (
    init_db, salva_atto, salva_classificazione,
    atto_gia_classificato, notifica_gia_inviata, salva_notifica, log_run,
    salva_utente, attiva_utente, get_utente_by_email, aggiorna_chat_id,
)
from core.classifier import classifica_atto
from core.notifier import invia_telegram, invia_errore_admin
from core.config import passa_prefiltro, categorie_probabili

from crawler.pvp import PvpCrawler
from crawler.asteweb import AstewebCrawler
from crawler.albo_pretorio_fc import AlboPretorioFcCrawler
from crawler.agrea import AgreaCrawler
from crawler.bonifica import BonificaCrawler

PROGETTO = os.getenv('PROGETTO', 'agrostima')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
ADMIN_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID_ADMIN', '')
LANDING_URL = os.getenv('LANDING_URL', '')
PORT = int(os.getenv('PORT', 8000))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s — %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('agrostima.main')

# ── FastAPI ──────────────────────────────────────────────────────────────────

app = FastAPI(title='AgroStima Scout', docs_url=None, redoc_url=None)

LANDING_DIR = Path(__file__).parent / 'landing'
if LANDING_DIR.exists():
    app.mount('/static', StaticFiles(directory=str(LANDING_DIR)), name='static')


@app.get('/')
async def index():
    html = LANDING_DIR / 'index.html'
    if html.exists():
        return FileResponse(str(html))
    return {'status': 'ok', 'service': 'agrostima-scout'}


@app.get('/grazie')
async def grazie():
    html = LANDING_DIR / 'grazie.html'
    if html.exists():
        return FileResponse(str(html))
    return {'status': 'ok'}


class IscrizioneForm(BaseModel):
    nome: str
    cognome: str
    email: str
    provincia: str
    specializzazione: str


@app.post('/iscrizione')
async def iscrizione(form: IscrizioneForm):
    utente_id = salva_utente(
        nome=form.nome,
        cognome=form.cognome,
        email=form.email,
        progetto=PROGETTO,
        province=[form.provincia],
        categorie=[form.specializzazione],
    )
    if utente_id is None:
        raise HTTPException(status_code=400, detail='Email già registrata')

    # Notifica admin via requests diretti (thread-safe, no bot object)
    _notifica_admin_nuova_iscrizione(form.nome, form.cognome, form.email, form.provincia)

    return {'ok': True}


def _notifica_admin_nuova_iscrizione(nome, cognome, email, provincia):
    import requests as req
    if not BOT_TOKEN or not ADMIN_CHAT_ID:
        logger.info(f"Nuova iscrizione (no Telegram): {email}")
        return
    testo = (
        f"📋 NUOVA ISCRIZIONE BETA — AgroStima\n\n"
        f"👤 {nome} {cognome}\n"
        f"📧 {email}\n"
        f"📍 {provincia}\n\n"
        f"Approva con: /approva {email}\n"
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    try:
        req.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={'chat_id': ADMIN_CHAT_ID, 'text': testo},
            timeout=10,
        )
    except Exception as e:
        logger.warning(f"Notifica admin fallita: {e}")


# ── Telegram bot ─────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['attende_email'] = True
    await update.message.reply_text(
        "👋 Benvenuto su AgroStima Scout!\n\n"
        "Inserisci l'email con cui ti sei iscritto per ricevere gli alert."
    )


async def cmd_approva(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != ADMIN_CHAT_ID:
        return
    if not context.args:
        await update.message.reply_text("Uso: /approva email@esempio.it")
        return
    email = context.args[0].lower().strip()
    ok = attiva_utente(email)
    if not ok:
        await update.message.reply_text(f"❌ Utente non trovato: {email}")
        return

    await update.message.reply_text(f"✅ {email} attivato")
    _invia_email_benvenuto(email)


def _invia_email_benvenuto(email: str):
    resend_key = os.getenv('RESEND_API_KEY', '')
    if not resend_key:
        logger.info(f"Benvenuto loggato (no Resend): {email}")
        return
    try:
        import resend
        resend.api_key = resend_key
        resend.Emails.send({
            'from': os.getenv('RESEND_FROM', 'noreply@agrostima.it'),
            'to': email,
            'subject': 'Accesso approvato — AgroStima Scout',
            'text': (
                "La tua iscrizione beta è stata approvata.\n\n"
                "Apri il bot Telegram e digita /start per attivare gli alert.\n\n"
                "— Team AgroStima Scout"
            ),
        })
    except Exception as e:
        logger.warning(f"Email benvenuto fallita per {email}: {e}")


async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('attende_email'):
        return

    email = update.message.text.strip().lower()
    utente = get_utente_by_email(email)

    if utente is None:
        link = f" Iscriviti su: {LANDING_URL}" if LANDING_URL else ''
        await update.message.reply_text(
            f"❌ Email non trovata.{link}"
        )
        return

    if not utente['attivo']:
        await update.message.reply_text(
            "⏳ Iscrizione ricevuta — in attesa di approvazione.\n"
            "Riceverai una notifica quando sarà attiva."
        )
        return

    chat_id = str(update.effective_chat.id)
    aggiorna_chat_id(email, chat_id)
    context.user_data.pop('attende_email', None)
    await update.message.reply_text(
        "✅ Tutto pronto! Riceverai qui gli alert sulle nuove opportunità."
    )


def run_telegram_bot():
    if not BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN non configurato — bot non avviato")
        return
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler('start', cmd_start))
    application.add_handler(CommandHandler('approva', cmd_approva))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email)
    )
    logger.info("Bot Telegram avviato (polling)")
    application.run_polling(stop_signals=None)


# ── Crawling pipeline ────────────────────────────────────────────────────────

def e_rilevante_per_agrostima(classificazione: dict) -> bool:
    professionisti = classificazione.get('professionisti_interessati', [])
    return (
        'perito_agrario' in professionisti
        and classificazione.get('rilevante', False)
    )


def _formatta_notifica(atto: dict, classificazione: dict, fonte: str) -> str:
    scadenza = classificazione.get('scadenza') or 'non specificata'
    importo = classificazione.get('importo') or 'non disponibile'
    return (
        f"🌾 NUOVA OPPORTUNITÀ — {fonte}\n\n"
        f"📋 {atto['titolo']}\n"
        f"📍 {atto.get('comune', '')} (FC)\n"
        f"🏷️ {classificazione.get('categoria', '')}\n"
        f"📅 Scadenza: {scadenza}\n"
        f"💶 Valore: {importo}\n\n"
        f"🔗 {atto['url']}\n\n"
        f"— AgroStima Scout • {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )


def _processa_atti(atti: list[dict], fonte: str) -> dict:
    stats = {'scaricati': len(atti), 'nuovi': 0, 'filtrati': 0, 'classificati': 0}

    for atto in atti:
        testo_completo = f"{atto.get('titolo', '')} {atto.get('testo', '')}"

        if not passa_prefiltro(testo_completo):
            stats['filtrati'] += 1
            continue

        atto_id = salva_atto(
            fonte=fonte,
            progetto=PROGETTO,
            titolo=atto.get('titolo', ''),
            testo=atto.get('testo', ''),
            url=atto['url'],
            comune=atto.get('comune'),
            provincia=atto.get('provincia', 'FC'),
            data_pubblicazione=atto.get('data_pubblicazione'),
        )

        if atto_id is None:
            continue

        stats['nuovi'] += 1

        if atto_gia_classificato(atto_id):
            continue

        categorie = categorie_probabili(testo_completo)
        classificazione = classifica_atto(testo_completo, categorie)
        salva_classificazione(atto_id, classificazione)
        stats['classificati'] += 1

        if e_rilevante_per_agrostima(classificazione):
            if not notifica_gia_inviata(atto_id, PROGETTO, 'telegram'):
                messaggio = _formatta_notifica(atto, classificazione, fonte)
                invia_telegram(messaggio)
                salva_notifica(atto_id, PROGETTO, 'telegram')

    return stats


def _crawl(crawler_cls, fonte_label: str):
    start = datetime.now()
    errori = None
    stats = {'scaricati': 0, 'nuovi': 0, 'filtrati': 0, 'classificati': 0}
    try:
        crawler = crawler_cls(progetto=PROGETTO)
        atti = crawler.scrape()
        stats = _processa_atti(atti, fonte_label)
        logger.info(f"[{fonte_label}] {stats}")
    except Exception as e:
        errori = str(e)
        logger.error(f"[{fonte_label}] Errore: {e}")
        invia_errore_admin(fonte_label, str(e), 'AgroStima')
    finally:
        durata = (datetime.now() - start).total_seconds()
        log_run(
            fonte=fonte_label,
            progetto=PROGETTO,
            atti_scaricati=stats['scaricati'],
            nuovi_inseriti=stats['nuovi'],
            filtrati_regex=stats['filtrati'],
            classificati_ai=stats['classificati'],
            errori=errori,
            durata_secondi=durata,
        )


def crawl_pvp(): _crawl(PvpCrawler, 'pvp')
def crawl_asteweb(): _crawl(AstewebCrawler, 'asteweb')
def crawl_albo_pretorio(): _crawl(AlboPretorioFcCrawler, 'albo_pretorio_fc')
def crawl_agrea(): _crawl(AgreaCrawler, 'agrea')
def crawl_bonifica(): _crawl(BonificaCrawler, 'bonifica')


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    logger.info("DB inizializzato — %s", os.getenv('DB_PATH', 'path da .env non trovato'))

    # BackgroundScheduler: non blocca il main thread
    scheduler = BackgroundScheduler(timezone='Europe/Rome')
    scheduler.add_job(crawl_pvp, 'interval', hours=6, id='pvp')
    scheduler.add_job(crawl_asteweb, 'interval', hours=6, id='asteweb')
    scheduler.add_job(crawl_albo_pretorio, 'cron', hour=7, id='albo')
    scheduler.add_job(crawl_agrea, 'cron', hour=8, id='agrea')
    scheduler.add_job(crawl_bonifica, 'cron', hour=8, minute=30, id='bonifica')

    # Crawl immediato al primo avvio
    logger.info("Avvio crawl iniziale...")
    crawl_pvp()
    crawl_asteweb()

    scheduler.start()
    logger.info("Scheduler avviato")

    # Bot Telegram in thread separato con proprio event loop
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()

    # FastAPI/uvicorn blocca il main thread
    logger.info(f"API avviata su 0.0.0.0:{PORT}")
    uvicorn.run(app, host='0.0.0.0', port=PORT, log_level='warning')
