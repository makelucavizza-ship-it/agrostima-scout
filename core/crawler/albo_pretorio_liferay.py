"""
Classe base per albi pretori su trasparenza-valutazione-merito.it (Liferay).

Workflow:
  1. GET /{page_path} → estrai formDate hidden
  2. POST eseguiOrdinamentoLista → stabilisce sessione con lista completa
  3. GET exportList → scarica CSV degli atti

Usata da: AlboPretorioFcCrawler, AlboPretorioRnCrawler, AlboPretorioRaCrawler.
"""

import csv
import io
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.crawler.base import BaseCrawler

import logging

logger = logging.getLogger(__name__)

_PAGE_PATH = '/web/trasparenza/albo-pretorio'
_PORTLET = 'jcitygovalbopubblicazioni_WAR_jcitygovalbiportlet'


class AlboPretorioLiferayCrawler(BaseCrawler):
    """
    Crawler parametrizzato per un singolo comune su trasparenza-valutazione-merito.it.

    Args:
        base_url: URL base del portale (es. 'https://forli.trasparenza-valutazione-merito.it')
        comune_name: Nome del comune per il campo 'comune' negli atti salvati
        provincia: Sigla provincia (es. 'FC')
        progetto: Tag progetto per il DB
    """

    def __init__(self, base_url: str, comune_name: str, provincia: str, progetto: str):
        fonte = f'albo_pretorio_{provincia.lower()}_{comune_name.lower().replace(" ", "_")}'
        super().__init__(fonte=fonte, progetto=progetto)
        self.base_url = base_url.rstrip('/')
        self.comune_name = comune_name
        self.provincia = provincia

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get_form_date(self) -> str | None:
        resp = self.get(f'{self.base_url}{_PAGE_PATH}')
        if not resp:
            return None
        m = re.search(
            rf'_{_PORTLET}_formDate[^>]*value="(\d+)"',
            resp.text
        )
        return m.group(1) if m else None

    def _post_search(self, form_date: str) -> bool:
        url = (
            f'{self.base_url}{_PAGE_PATH}'
            f'?p_p_id={_PORTLET}'
            f'&p_p_lifecycle=1&p_p_state=normal&p_p_mode=view'
            f'&p_p_col_id=column-1&p_p_col_count=1'
            f'&_{_PORTLET}_action=eseguiOrdinamentoLista'
        )
        data = {
            f'_{_PORTLET}_formDate': form_date,
            f'_{_PORTLET}_simpleSearchEnable': 'true',
            f'_{_PORTLET}_mostraSoloLista': 'true',
        }
        try:
            resp = self.session.post(url, data=data, timeout=self.timeout)
            resp.raise_for_status()
            time.sleep(2)
            return True
        except Exception as e:
            logger.warning(f'[{self.fonte}] POST search fallito: {e}')
            return False

    def _get_csv(self) -> str | None:
        url = (
            f'{self.base_url}{_PAGE_PATH}'
            f'?p_p_id={_PORTLET}'
            f'&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view'
            f'&p_p_resource_id=exportList&p_p_cacheability=cacheLevelPage'
            f'&p_p_col_id=column-1&p_p_col_count=1'
            f'&_{_PORTLET}_format=csv'
        )
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            time.sleep(2)
            return resp.content.decode('utf-8-sig', errors='replace')
        except Exception as e:
            logger.warning(f'[{self.fonte}] GET CSV fallito: {e}')
            return None

    def _parse_csv(self, raw_csv: str) -> list[dict]:
        reader = csv.DictReader(io.StringIO(raw_csv))
        atti = []
        for row in reader:
            oggetto    = row.get('Oggetto', '').strip()
            contenuto  = row.get('Contenuto', '').strip()
            proponente = row.get('Proponente descrizione', '').strip()
            data_inizio = row.get('Data inizio pubblicazione', '').strip()
            url_atto   = row.get('Url atto', '').strip()
            anno_reg   = row.get('Anno registrazione', '').strip()
            num_reg    = row.get('Numero registrazione', '').strip()

            if not oggetto:
                continue

            if url_atto:
                url = url_atto
            elif anno_reg and num_reg:
                url = (
                    f'{self.base_url}{_PAGE_PATH}'
                    f'?anno_reg={anno_reg}&num_reg={num_reg}'
                )
            else:
                continue

            testo = ' | '.join(filter(None, [oggetto, proponente, contenuto]))

            atti.append({
                'titolo':             oggetto,
                'testo':              testo,
                'url':                url,
                'comune':             self.comune_name,
                'provincia':          self.provincia,
                'data_pubblicazione': data_inizio or None,
            })
        return atti

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scrape(self) -> list[dict]:
        form_date = self._get_form_date()
        if not form_date:
            logger.warning(f'[{self.fonte}] formDate non trovato — portale non raggiungibile o struttura cambiata')
            return []

        if not self._post_search(form_date):
            return []

        raw_csv = self._get_csv()
        if not raw_csv:
            return []

        atti = self._parse_csv(raw_csv)
        logger.info(f'[{self.fonte}] {len(atti)} atti scaricati da {self.comune_name}')
        return atti
