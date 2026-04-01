import sqlite3
import json
import os
from pathlib import Path

DB_PATH = os.getenv(
    'DB_PATH',
    str(Path(__file__).resolve().parent.parent / 'data' / 'shared.db')
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS atti_grezzi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fonte TEXT NOT NULL,
    progetto TEXT NOT NULL,
    comune TEXT,
    provincia TEXT,
    titolo TEXT,
    testo TEXT,
    url TEXT UNIQUE,
    data_pubblicazione TEXT,
    scaricato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS classificazioni (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    atto_id INTEGER REFERENCES atti_grezzi(id),
    categoria TEXT,
    professionisti_interessati TEXT,
    urgenza INTEGER DEFAULT 0,
    scadenza TEXT,
    importo TEXT,
    parole_chiave TEXT,
    rilevante INTEGER DEFAULT 1,
    classificato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modello_usato TEXT DEFAULT 'claude-haiku'
);

CREATE TABLE IF NOT EXISTS log_crawler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fonte TEXT NOT NULL,
    progetto TEXT NOT NULL,
    eseguito_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atti_scaricati INTEGER DEFAULT 0,
    nuovi_inseriti INTEGER DEFAULT 0,
    filtrati_regex INTEGER DEFAULT 0,
    classificati_ai INTEGER DEFAULT 0,
    errori TEXT,
    durata_secondi REAL
);

CREATE TABLE IF NOT EXISTS notifiche_inviate (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    atto_id INTEGER REFERENCES atti_grezzi(id),
    progetto TEXT NOT NULL,
    canale TEXT NOT NULL,
    inviata_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_atti_url ON atti_grezzi(url);
CREATE INDEX IF NOT EXISTS idx_atti_progetto ON atti_grezzi(progetto);
CREATE INDEX IF NOT EXISTS idx_classificazioni_atto ON classificazioni(atto_id);
CREATE INDEX IF NOT EXISTS idx_classificazioni_professionisti
    ON classificazioni(professionisti_interessati);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Crea le tabelle se non esistono. Idempotente."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    with conn:
        conn.executescript(_SCHEMA)
    conn.close()


def salva_atto(
    fonte: str,
    progetto: str,
    titolo: str,
    testo: str,
    url: str,
    comune: str = None,
    provincia: str = None,
    data_pubblicazione: str = None,
) -> int | None:
    """
    Inserisce un atto grezzo.
    Restituisce l'id del record inserito, o None se l'URL era già presente.
    """
    conn = get_connection()
    try:
        with conn:
            cursor = conn.execute(
                """INSERT INTO atti_grezzi
                   (fonte, progetto, comune, provincia, titolo, testo, url, data_pubblicazione)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (fonte, progetto, comune, provincia, titolo, testo, url, data_pubblicazione),
            )
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def salva_classificazione(
    atto_id: int, classificazione: dict, modello: str = 'claude-haiku'
) -> int:
    conn = get_connection()
    try:
        with conn:
            cursor = conn.execute(
                """INSERT INTO classificazioni
                   (atto_id, categoria, professionisti_interessati, urgenza,
                    scadenza, importo, parole_chiave, rilevante, modello_usato)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    atto_id,
                    classificazione.get('categoria'),
                    json.dumps(classificazione.get('professionisti_interessati', []), ensure_ascii=False),
                    1 if classificazione.get('urgenza') else 0,
                    classificazione.get('scadenza'),
                    classificazione.get('importo'),
                    json.dumps(classificazione.get('parole_chiave', []), ensure_ascii=False),
                    1 if classificazione.get('rilevante') else 0,
                    modello,
                ),
            )
            return cursor.lastrowid
    finally:
        conn.close()


def atto_gia_classificato(atto_id: int) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM classificazioni WHERE atto_id = ?", (atto_id,)
    ).fetchone()
    conn.close()
    return row is not None


def notifica_gia_inviata(atto_id: int, progetto: str, canale: str) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM notifiche_inviate WHERE atto_id = ? AND progetto = ? AND canale = ?",
        (atto_id, progetto, canale),
    ).fetchone()
    conn.close()
    return row is not None


def salva_notifica(atto_id: int, progetto: str, canale: str):
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT INTO notifiche_inviate (atto_id, progetto, canale) VALUES (?, ?, ?)",
            (atto_id, progetto, canale),
        )
    conn.close()


def log_run(
    fonte: str,
    progetto: str,
    atti_scaricati: int = 0,
    nuovi_inseriti: int = 0,
    filtrati_regex: int = 0,
    classificati_ai: int = 0,
    errori: str = None,
    durata_secondi: float = None,
):
    conn = get_connection()
    with conn:
        conn.execute(
            """INSERT INTO log_crawler
               (fonte, progetto, atti_scaricati, nuovi_inseriti,
                filtrati_regex, classificati_ai, errori, durata_secondi)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (fonte, progetto, atti_scaricati, nuovi_inseriti,
             filtrati_regex, classificati_ai, errori, durata_secondi),
        )
    conn.close()
