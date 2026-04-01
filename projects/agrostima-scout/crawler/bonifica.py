import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.crawler.base import BaseCrawler

import logging
logger = logging.getLogger(__name__)


class BonificaCrawler(BaseCrawler):
    """
    Consorzio di Bonifica della Romagna (bonificaromagna.it).
    Il sito non espone un feed strutturato di gare/appalti:
    la pagina /gare-e-appalti è un articolo statico senza lista paginata.
    TODO: Monitorare se il sito aggiunge un'area gare strutturata,
          oppure valutare il portale Amministrazione Trasparente su
          gazzettaamministrativa.it come fonte alternativa.
    """

    BASE_URL = 'https://www.bonificaromagna.it'

    def __init__(self, progetto: str):
        super().__init__(fonte='bonifica', progetto=progetto)

    def scrape(self) -> list[dict]:
        logger.info(
            f'[{self.fonte}] Fonte non ancora strutturata — '
            'nessun feed gare disponibile su bonificaromagna.it'
        )
        return []
