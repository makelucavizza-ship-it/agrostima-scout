import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.crawler.base import BaseCrawler


class PvpCrawler(BaseCrawler):
    """
    PVP — Portale Vendite Pubbliche (pvp.giustizia.it)
    Priorità 1 — frequenza 6h
    TODO: implementare scrape() — filtro provincia FC, categoria beni agricoli
    """

    BASE_URL = 'https://pvp.giustizia.it/pvp/it/risultati_ricerca.page'

    def __init__(self, progetto: str):
        super().__init__(fonte='pvp', progetto=progetto)

    def scrape(self) -> list[dict]:
        # TODO: implementare
        # - Ricerca per provincia FC
        # - Filtrare per categorie rilevanti (terreni agricoli, fondi rustici)
        # - Restituire lista di dict con: titolo, testo, url, comune, provincia, data_pubblicazione
        return []
