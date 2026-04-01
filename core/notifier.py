import os
import requests
from datetime import datetime

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def _send(token: str, chat_id: str, text: str) -> bool:
    url = _TELEGRAM_API.format(token=token)
    try:
        r = requests.post(
            url,
            json={
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True,
            },
            timeout=15,
        )
        return r.ok
    except Exception:
        return False


def invia_telegram(testo: str, chat_id: str = None) -> bool:
    token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    target = chat_id or os.getenv('TELEGRAM_CHAT_ID_UTENTE', '')
    if not token or not target:
        return False
    return _send(token, target, testo)


def invia_errore_admin(fonte: str, errore: str, progetto: str = 'Sistema') -> bool:
    token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    admin_id = os.getenv('TELEGRAM_CHAT_ID_ADMIN', '')
    if not token or not admin_id:
        return False
    testo = (
        f"⚠️ ERRORE CRAWLER — {progetto}\n"
        f"Fonte: {fonte}\n"
        f"Errore: {errore}\n"
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    return _send(token, admin_id, testo)
