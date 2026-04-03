import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.crawler.base import BaseCrawler
from core.crawler.albo_pretorio_liferay import AlboPretorioLiferayCrawler

import logging
logger = logging.getLogger(__name__)

# Comuni prioritari RN su trasparenza-valutazione-merito.it
# Se un comune restituisce 0 atti → WAF o subdomain errato → vedere i log
RN_COMUNI = [
    ('https://rimini.trasparenza-valutazione-merito.it',                  'Rimini',                    'RN'),
    ('https://riccione.trasparenza-valutazione-merito.it',                'Riccione',                  'RN'),
    ('https://santarcangelodiromagna.trasparenza-valutazione-merito.it',  'Santarcangelo di Romagna',  'RN'),
    ('https://cattolica.trasparenza-valutazione-merito.it',               'Cattolica',                 'RN'),
]


class AlboPretorioRnCrawler(BaseCrawler):
    """
    Albo Pretorio comuni provincia RN — aggrega risultati da ogni comune.
    Frequenza: 1x/giorno (cron ore 7:10).
    """

    def __init__(self, progetto: str):
        super().__init__(fonte='albo_pretorio_rn', progetto=progetto)

    def scrape(self) -> list[dict]:
        tutti = []
        for base_url, comune, provincia in RN_COMUNI:
            try:
                crawler = AlboPretorioLiferayCrawler(
                    base_url=base_url,
                    comune_name=comune,
                    provincia=provincia,
                    progetto=self.progetto,
                )
                atti = crawler.scrape()
                tutti.extend(atti)
            except Exception as e:
                logger.warning(f'[albo_pretorio_rn] Errore per {comune}: {e}')
        logger.info(f'[albo_pretorio_rn] Totale atti RN: {len(tutti)}')
        return tutti
