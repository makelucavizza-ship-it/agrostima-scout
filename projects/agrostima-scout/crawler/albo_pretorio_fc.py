import csv
import io
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.crawler.base import BaseCrawler

import logging
logger = logging.getLogger(__name__)

_BASE_FORLI = 'https://forli.trasparenza-valutazione-merito.it'
_PAGE_PATH  = '/web/trasparenza/albo-pretorio'
_PORTLET    = 'jcitygovalbopubblicazioni_WAR_jcitygovalbiportlet'


class AlboPretorioFcCrawler(BaseCrawler):
    """
    Albo Pretorio Forlì — Liferay jcitygovalbopubblicazioni portlet.
    Workflow: GET page → estrai formDate → POST search → GET CSV.
    Frequenza: 1x/giorno (cron ore 7).
    """

    def __init__(self, progetto: str):
        super().__init__(fonte='albo_pretorio_fc', progetto=progetto)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get_form_date(self) -> str | None:
        """GET homepage, estrae il valore del campo hidden formDate."""
        resp = self.get(f'{_BASE_FORLI}{_PAGE_PATH}')
        if not resp:
            return None
        m = re.search(
            rf'_{_PORTLET}_formDate[^>]*value="(\d+)"',
            resp.text
        )
        return m.group(1) if m else None

    def _post_search(self, form_date: str) -> bool:
        """
        POST eseguiOrdinamentoLista — stabilisce la sessione con lista completa.
        Usa la stessa requests.Session del BaseCrawler per mantenere i cookie.
        """
        url = (
            f'{_BASE_FORLI}{_PAGE_PATH}'
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
        """GET exportList CSV — richiede sessione attiva da _post_search."""
        url = (
            f'{_BASE_FORLI}{_PAGE_PATH}'
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
            # Risposta è CSV con BOM utf-8-sig
            return resp.content.decode('utf-8-sig', errors='replace')
        except Exception as e:
            logger.warning(f'[{self.fonte}] GET CSV fallito: {e}')
            return None

    @staticmethod
    def _parse_csv(raw_csv: str) -> list[dict]:
        """Converte il CSV grezzo in lista di dict normalizzati."""
        reader = csv.DictReader(io.StringIO(raw_csv))
        atti = []
        for row in reader:
            oggetto    = row.get('Oggetto', '').strip()
            contenuto  = row.get('Contenuto', '').strip()
            proponente = row.get('Proponente descrizione', '').strip()
            data_inizio = row.get('Data inizio pubblicazione', '').strip()
            url_atto   = row.get('Url atto', '').strip()

            # Campi per costruire URL univoco quando il link diretto manca
            anno_reg = row.get('Anno registrazione', '').strip()
            num_reg  = row.get('Numero registrazione', '').strip()

            if not oggetto:
                continue

            if url_atto:
                url = url_atto
            elif anno_reg and num_reg:
                # URL sintetico univoco — non navigabile ma stabile nel DB
                url = (
                    f'{_BASE_FORLI}{_PAGE_PATH}'
                    f'?anno_reg={anno_reg}&num_reg={num_reg}'
                )
            else:
                continue  # Senza ID univoco non possiamo evitare duplicati

            testo = ' | '.join(filter(None, [oggetto, proponente, contenuto]))

            atti.append({
                'titolo':             oggetto,
                'testo':              testo,
                'url':                url,
                'comune':             'Forlì',
                'provincia':          'FC',
                'data_pubblicazione': data_inizio or None,
            })
        return atti

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scrape(self) -> list[dict]:
        form_date = self._get_form_date()
        if not form_date:
            logger.error(f'[{self.fonte}] formDate non trovato')
            return []

        if not self._post_search(form_date):
            return []

        raw_csv = self._get_csv()
        if not raw_csv:
            return []

        atti = self._parse_csv(raw_csv)
        logger.info(f'[{self.fonte}] {len(atti)} atti scaricati da Forlì')
        return atti
