import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.crawler.base import BaseCrawler

import logging
logger = logging.getLogger(__name__)

_API_BASE  = 'https://agrea.regione.emilia-romagna.it/++api++'
_SEARCH    = f'{_API_BASE}/@search'
_PAGE_SIZE = 50


class AgreaCrawler(BaseCrawler):
    """
    AGREA — Agenzia Regionale per le Erogazioni in Agricoltura (Emilia-Romagna).
    Usa la REST API Plone 6 pubblica (Accept: application/json).
    Endpoint: ++api++/@search?portal_type=Bando
    Frequenza: 1x/giorno (cron ore 8).
    """

    def __init__(self, progetto: str):
        super().__init__(fonte='agrea', progetto=progetto)
        # Plone REST API richiede Accept: application/json
        self.session.headers.update({'Accept': 'application/json'})

    def _fetch_page(self, start: int) -> dict | None:
        """GET una pagina di risultati dall'API di ricerca Plone."""
        url = (
            f'{_SEARCH}'
            f'?portal_type=Bando'
            f'&sort_on=effective&sort_order=descending'
            f'&b_size={_PAGE_SIZE}&b_start={start}'
        )
        resp = self.get(url)
        if not resp:
            return None
        try:
            return resp.json()
        except Exception as e:
            logger.warning(f'[{self.fonte}] JSON parse error pagina {start}: {e}')
            return None

    def _fetch_detail(self, item_url: str) -> str:
        """
        GET dettaglio singolo bando via API Plone.
        Restituisce il testo (description + text) troncato a 500 chars.
        """
        resp = self.get(item_url)
        if not resp:
            return ''
        try:
            data = resp.json()
            parts = [
                data.get('description', ''),
                data.get('title', ''),
            ]
            # Plone può avere text.data (HTML) o text (stringa)
            text_field = data.get('text', '')
            if isinstance(text_field, dict):
                text_field = text_field.get('data', '')
            if text_field:
                # Rimuovi tag HTML base
                import re
                text_field = re.sub(r'<[^>]+>', ' ', text_field)
                parts.append(text_field)
            return ' '.join(filter(None, parts))[:500]
        except Exception:
            return ''

    def scrape(self) -> list[dict]:
        atti = []
        start = 0

        while True:
            page = self._fetch_page(start)
            if not page:
                break

            items = page.get('items', [])
            if not items:
                break

            for item in items:
                item_url = item.get('@id', '')
                if not item_url:
                    continue

                titolo = item.get('title', '').strip()
                # Fetch testo completo solo se il titolo supera il prefiltro grezzo
                testo_breve = f"{titolo} {item.get('description', '')}"
                testo_dettaglio = self._fetch_detail(item_url)
                testo = testo_dettaglio if testo_dettaglio else testo_breve

                data_raw = item.get('Date', '') or item.get('effective', '')
                data_pub = data_raw[:10] if data_raw else None  # YYYY-MM-DD

                atti.append({
                    'titolo':             titolo,
                    'testo':              testo,
                    'url':                item_url,
                    'comune':             None,   # Fonte regionale, non FC-specifica
                    'provincia':          None,
                    'data_pubblicazione': data_pub,
                })

            # Paginazione Plone: controlla se ci sono altre pagine
            total = page.get('items_total', len(atti))
            start += _PAGE_SIZE
            if start >= total:
                break

        logger.info(f'[{self.fonte}] {len(atti)} bandi scaricati da AGREA')
        return atti
