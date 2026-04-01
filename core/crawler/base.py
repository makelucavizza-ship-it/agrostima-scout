import time
import logging
from abc import ABC, abstractmethod

import requests

logger = logging.getLogger(__name__)

_DEFAULT_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/122.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'it-IT,it;q=0.9,en;q=0.8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}


class BaseCrawler(ABC):
    def __init__(self, fonte: str, progetto: str):
        self.fonte = fonte
        self.progetto = progetto
        self.timeout = 15
        self.session = requests.Session()
        self.session.headers.update(_DEFAULT_HEADERS)

    def get(self, url: str, retries: int = 3, delay: float = 2.0) -> requests.Response | None:
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                time.sleep(delay)  # Rate limiting tra richieste allo stesso dominio
                return response
            except requests.RequestException as e:
                logger.warning(f"[{self.fonte}] Tentativo {attempt + 1}/{retries} fallito: {e}")
                if attempt < retries - 1:
                    time.sleep(delay * (attempt + 1))
        logger.error(f"[{self.fonte}] Tutti i tentativi falliti per {url}")
        return None

    @abstractmethod
    def scrape(self) -> list[dict]:
        """
        Restituisce una lista di dict con le chiavi:
            titolo, testo, url, comune, provincia, data_pubblicazione
        """
        ...
