"""
AsteGiudiziarie.net — crawler via API interna.

Flusso scoperto analizzando il bundle Vue.js (ricerca.js):
  1. POST webapi.astegiudiziarie.it/api/search/map  → lista di {idLotto, ...}
  2. POST webapi.astegiudiziarie.it/api/search/Data → dettagli per batch di ID

Ricerca senza filtro comune → risultati nazionali.
Se il POST senza comune restituisce 0 lotti, verificare i log
e provare ad aggiungere 'comune': '' al payload.
"""

import sys
import logging
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.crawler.base import BaseCrawler

logger = logging.getLogger(__name__)

_API_BASE = 'https://webapi.astegiudiziarie.it/api/'
_SITE_ROOT = 'https://www.astegiudiziarie.it'

_BASE_PAYLOAD = {
    'tipoRicerca': 1,
    'noGeo': False,
    'idTipologie': [],
    'idCategorie': [],
    'storica': False,
    'vetrina': False,
    'searchOnMap': False,
    'orderBy': 6,          # più recenti prima
    'priceMax': 0.0,
}

_BATCH_SIZE = 50


class AstewebCrawler(BaseCrawler):

    def __init__(self, progetto: str):
        super().__init__(fonte='asteweb', progetto=progetto)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Referer': _SITE_ROOT + '/',
            'X-Referer': _SITE_ROOT + '/',
        })

    # ------------------------------------------------------------------ #
    #  Layer 1 — IDs nazionali                                            #
    # ------------------------------------------------------------------ #

    def _ids_nazionali(self) -> list[int]:
        """POST search/map senza filtro comune → lista di idLotto nazionali."""
        r = self.session.post(_API_BASE + 'search/map', json=_BASE_PAYLOAD, timeout=self.timeout)
        r.raise_for_status()
        time.sleep(2)
        ids = [item['idLotto'] for item in r.json() if 'idLotto' in item]
        logger.info(f'[asteweb] Lotti nazionali ricevuti: {len(ids)} — limitati a 500 più recenti')
        return ids[:500]

    # ------------------------------------------------------------------ #
    #  Layer 2 — Dettagli per batch di IDs                                #
    # ------------------------------------------------------------------ #

    def _dettagli_batch(self, ids: list[int]) -> list[dict]:
        """POST search/Data con una lista di ID → lista di dettagli."""
        r = self.session.post(_API_BASE + 'search/Data', json=ids, timeout=self.timeout)
        r.raise_for_status()
        time.sleep(2)
        return r.json()

    # ------------------------------------------------------------------ #
    #  Mapping campo API → formato atto grezzo                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _map_atto(item: dict) -> dict:
        categoria = item.get('categoria') or item.get('tipologia') or 'Asta giudiziaria'
        comune    = item.get('comune') or ''
        provincia = item.get('provincia') or ''
        titolo    = f"{categoria} — {comune} ({provincia})" if provincia else f"{categoria} — {comune}"

        testo_parts = [
            item.get('descrizione') or '',
            item.get('categoria') or '',
            item.get('tipologia') or '',
            item.get('tribunale') or '',
            item.get('ruolo') or '',
        ]
        testo = ' '.join(p for p in testo_parts if p)

        slug = item.get('urlSchedaDettagliata') or ''
        url = (_SITE_ROOT + slug) if slug.startswith('/') else slug

        data = (
            item.get('dataUdienza')
            or item.get('dataFineGara')
            or item.get('dataFinePubblicazione')
        )
        if data:
            data = data[:10]  # YYYY-MM-DD

        return {
            'titolo': titolo,
            'testo': testo,
            'url': url,
            'comune': comune,
            'provincia': provincia,
            'data_pubblicazione': data,
        }

    # ------------------------------------------------------------------ #
    #  Entry point                                                         #
    # ------------------------------------------------------------------ #

    def scrape(self) -> list[dict]:
        try:
            ids_list = self._ids_nazionali()
        except Exception as exc:
            logger.warning(f'[asteweb] Errore search/map nazionale: {exc}')
            return []

        if not ids_list:
            logger.warning('[asteweb] Nessun lotto ricevuto — API potrebbe richiedere filtro comune')
            return []

        atti = []
        for i in range(0, len(ids_list), _BATCH_SIZE):
            batch = ids_list[i:i + _BATCH_SIZE]
            try:
                dettagli = self._dettagli_batch(batch)
                for item in dettagli:
                    atto = self._map_atto(item)
                    if atto['url']:
                        atti.append(atto)
            except Exception as exc:
                logger.warning(f'[asteweb] Errore search/Data batch {i}-{i + _BATCH_SIZE}: {exc}')

        logger.info(f'[asteweb] Atti nazionali trovati: {len(atti)}')
        return atti
