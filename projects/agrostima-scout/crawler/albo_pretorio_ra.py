import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.crawler.base import BaseCrawler
from core.crawler.albo_pretorio_liferay import AlboPretorioLiferayCrawler

import logging
logger = logging.getLogger(__name__)

# Comuni prioritari RA su trasparenza-valutazione-merito.it
# Ravenna esclusa: usa trasparenzaealbo.comune.ra.it (JS-rendered) → rimandato v2
RA_COMUNI = [
    ('https://faenza.trasparenza-valutazione-merito.it',      'Faenza',       'RA'),
    ('https://lugo.trasparenza-valutazione-merito.it',        'Lugo',         'RA'),
    ('https://cervia.trasparenza-valutazione-merito.it',      'Cervia',       'RA'),
    ('https://bagnacavallo.trasparenza-valutazione-merito.it', 'Bagnacavallo', 'RA'),
]


class AlboPretorioRaCrawler(BaseCrawler):
    """
    Albo Pretorio comuni provincia RA — aggrega risultati da ogni comune.
    Frequenza: 1x/giorno (cron ore 7:20).
    """

    def __init__(self, progetto: str):
        super().__init__(fonte='albo_pretorio_ra', progetto=progetto)

    def scrape(self) -> list[dict]:
        tutti = []
        for base_url, comune, provincia in RA_COMUNI:
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
                logger.warning(f'[albo_pretorio_ra] Errore per {comune}: {e}')
        logger.info(f'[albo_pretorio_ra] Totale atti RA: {len(tutti)}')
        return tutti
