"""
AsteGiudiziarie.net — crawler via API interna.

Flusso scoperto analizzando il bundle Vue.js (ricerca.js):
  1. POST webapi.astegiudiziarie.it/api/search/map  → lista di {idLotto, ...}
  2. POST webapi.astegiudiziarie.it/api/search/Data → dettagli per batch di ID

Il filtro per provincia (sigla "FC") non funziona server-side;
si filtra per comune iterando sulla lista FC_COMUNI.
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

# Estratti dalla sitemap RicercheImmobiliEProvinciaEComune (30 comuni FC)
FC_COMUNI = [
    'Bagno Di Romagna', 'Bertinoro', 'Borghi',
    'Castrocaro Terme E Terra Del Sole', 'Cesena', 'Cesenatico',
    'Civitella Di Romagna', 'Dovadola', 'Forlì', 'Forlimpopoli',
    'Galeata', 'Gambettola', 'Gatteo', 'Longiano', 'Meldola',
    'Mercato Saraceno', 'Modigliana', 'Montiano',
    'Portico E San Benedetto', 'Predappio', 'Premilcuore',
    'Rocca San Casciano', 'Roncofreddo', 'San Mauro Pascoli',
    'Santa Sofia', 'Sarsina', 'Savignano Sul Rubicone',
    'Sogliano Al Rubicone', 'Tredozio', 'Verghereto',
]

_BASE_PAYLOAD = {
    'tipoRicerca': 1,
    'noGeo': False,
    'idTipologie': [],     # tutti i tipi (immobili, mobili, aziende, ...)
    'idCategorie': [],
    'storica': False,
    'vetrina': False,
    'searchOnMap': False,
    'orderBy': 6,          # più recenti prima
    'priceMax': 0.0,
}

_BATCH_SIZE = 50  # IDs per chiamata a search/Data


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
    #  Layer 1 — IDs per comune                                           #
    # ------------------------------------------------------------------ #

    def _ids_per_comune(self, comune: str) -> list[int]:
        """POST search/map → lista di idLotto per il comune dato."""
        payload = {**_BASE_PAYLOAD, 'comune': comune}
        r = self.session.post(_API_BASE + 'search/map', json=payload, timeout=self.timeout)
        r.raise_for_status()
        time.sleep(2)  # Rate limiting
        return [item['idLotto'] for item in r.json() if 'idLotto' in item]

    # ------------------------------------------------------------------ #
    #  Layer 2 — Dettagli per batch di IDs                                #
    # ------------------------------------------------------------------ #

    def _dettagli_batch(self, ids: list[int]) -> list[dict]:
        """POST search/Data con una lista di ID → lista di dettagli."""
        r = self.session.post(_API_BASE + 'search/Data', json=ids, timeout=self.timeout)
        r.raise_for_status()
        time.sleep(2)  # Rate limiting
        return r.json()

    # ------------------------------------------------------------------ #
    #  Mapping campo API → formato atto grezzo                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _map_atto(item: dict) -> dict:
        # Titolo: categoria + comune
        categoria = item.get('categoria') or item.get('tipologia') or 'Asta giudiziaria'
        comune = item.get('comune') or ''
        titolo = f"{categoria} — {comune} (FC)"

        # Testo per il prefiltro: tutto ciò che è utile
        testo_parts = [
            item.get('descrizione') or '',
            item.get('categoria') or '',
            item.get('tipologia') or '',
            item.get('tribunale') or '',
            item.get('ruolo') or '',
        ]
        testo = ' '.join(p for p in testo_parts if p)

        # URL scheda dettagliata
        slug = item.get('urlSchedaDettagliata') or ''
        url = (_SITE_ROOT + slug) if slug.startswith('/') else slug

        # Data più rilevante disponibile
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
            'provincia': item.get('provincia') or 'FC',
            'data_pubblicazione': data,
        }

    # ------------------------------------------------------------------ #
    #  Entry point                                                         #
    # ------------------------------------------------------------------ #

    def scrape(self) -> list[dict]:
        # Raccogli tutti gli ID FC (deduplicati — stesso lotto può apparire in più ricerche)
        tutti_ids: dict[int, None] = {}
        for comune in FC_COMUNI:
            try:
                ids = self._ids_per_comune(comune)
                for id_ in ids:
                    tutti_ids[id_] = None
                logger.debug(f"[asteweb] {comune}: {len(ids)} lotti")
            except Exception as exc:
                logger.warning(f"[asteweb] Errore search/map per {comune}: {exc}")

        ids_list = list(tutti_ids.keys())
        logger.info(f"[asteweb] ID unici FC: {len(ids_list)}")

        if not ids_list:
            return []

        # Recupera dettagli in batch
        atti = []
        for i in range(0, len(ids_list), _BATCH_SIZE):
            batch = ids_list[i:i + _BATCH_SIZE]
            try:
                dettagli = self._dettagli_batch(batch)
                for item in dettagli:
                    # Doppia verifica: solo FC (per sicurezza)
                    if item.get('provincia') == 'FC':
                        atto = self._map_atto(item)
                        if atto['url']:  # scarta se non ha URL
                            atti.append(atto)
            except Exception as exc:
                logger.warning(f"[asteweb] Errore search/Data batch {i}-{i+_BATCH_SIZE}: {exc}")

        logger.info(f"[asteweb] Atti FC trovati: {len(atti)}")
        return atti
