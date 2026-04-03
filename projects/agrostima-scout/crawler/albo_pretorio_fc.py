import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.crawler.base import BaseCrawler
from core.crawler.albo_pretorio_liferay import AlboPretorioLiferayCrawler

import logging
logger = logging.getLogger(__name__)

_BASE_URL  = 'https://forli.trasparenza-valutazione-merito.it'
_COMUNE    = 'Forlì'
_PROVINCIA = 'FC'


class AlboPretorioFcCrawler(BaseCrawler):
    """
    Albo Pretorio Forlì — thin wrapper su AlboPretorioLiferayCrawler.
    Frequenza: 1x/giorno (cron ore 7).
    """

    def __init__(self, progetto: str):
        super().__init__(fonte='albo_pretorio_fc', progetto=progetto)

    def scrape(self) -> list[dict]:
        crawler = AlboPretorioLiferayCrawler(
            base_url=_BASE_URL,
            comune_name=_COMUNE,
            provincia=_PROVINCIA,
            progetto=self.progetto,
        )
        atti = crawler.scrape()
        logger.info(f'[albo_pretorio_fc] {len(atti)} atti da Forlì')
        return atti
