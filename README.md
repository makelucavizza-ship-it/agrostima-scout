# progetti-automation-professionisti

Monorepo per tool di aggregazione automatizzata di opportunità professionali
per liberi professionisti italiani.

## Struttura

```
├── core/          Codice condiviso (DB, AI, notifiche, crawler base)
├── data/          Database SQLite condiviso (shared.db — creato al primo avvio)
└── projects/      Un progetto per categoria professionale
```

## Progetti

| Progetto | Target | Provincia | Stato |
|---|---|---|---|
| agrostima-scout | Perito agrario estimatore | FC | In sviluppo |
| geometra-scout | Geometra estimatore | TBD | Pianificato |
| revisori-enti-locali | Revisore enti locali | Nazionale | Pianificato |

## Quick start — agrostima-scout

```bash
cd projects/agrostima-scout
cp .env.example .env
# Popolare .env con le credenziali reali
pip install -r requirements.txt
python main.py
```

## Regole di sviluppo

Vedi `CLAUDE.md` nella root per tutte le regole operative.
Ogni progetto ha il proprio `CLAUDE.md` in `projects/[nome]/CLAUDE.md`.
