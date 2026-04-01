import sys
import os
import logging
from datetime import datetime
from pathlib import Path

# Path setup — aggiunge la root del monorepo a sys.path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / '.env')

from apscheduler.schedulers.blocking import BlockingScheduler

from core.db import (
    init_db, salva_atto, salva_classificazione,
    atto_gia_classificato, notifica_gia_inviata, salva_notifica, log_run,
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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s — %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('agrostima.main')


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
            # URL già presente — duplicato ignorato
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


if __name__ == '__main__':
    init_db()
    logger.info("DB inizializzato — %s", os.getenv('DB_PATH', 'path da .env non trovato'))

    scheduler = BlockingScheduler(timezone='Europe/Rome')

    scheduler.add_job(crawl_pvp, 'interval', hours=6, id='pvp')
    scheduler.add_job(crawl_asteweb, 'interval', hours=6, id='asteweb')
    scheduler.add_job(crawl_albo_pretorio, 'cron', hour=7, id='albo')
    scheduler.add_job(crawl_agrea, 'cron', hour=8, id='agrea')
    scheduler.add_job(crawl_bonifica, 'cron', hour=8, minute=30, id='bonifica')

    # Crawl immediato al primo avvio (fonti priorità 1)
    logger.info("Avvio crawl iniziale...")
    crawl_pvp()
    crawl_asteweb()

    logger.info("Scheduler avviato")
    scheduler.start()
