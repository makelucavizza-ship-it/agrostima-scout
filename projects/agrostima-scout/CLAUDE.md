# AgroStima Scout — CLAUDE.md specifico

> Questo file estende /CLAUDE.md (root del monorepo).
> Leggi PRIMA il file globale, poi questo.
> In caso di conflitto, questo file ha priorità
> solo per ciò che riguarda AgroStima Scout.

---

## Contesto del progetto

AgroStima Scout risolve un problema preciso: i periti agrari
estimatori junior in provincia di Forlì-Cesena non trovano
facilmente incarichi perché le fonti sono frammentate su decine
di portali istituzionali. I senior vengono chiamati per rete
personale. Questo tool colma il gap.

**Target:** perito agrario estimatore junior, provincia FC,
libero professionista o collaboratore di studio.

**Valore core:** alert immediato su nuove opportunità di stima
(espropri, aste agricole, bandi assicurativi, consorzi di bonifica)
prima che arrivino via passaparola.

**Categoria professionale nel DB:** `perito_agrario`

---

## Posizione nel monorepo
```
progetti-automation-professionisti/
└── projects/
    └── agrostima-scout/
        ├── CLAUDE.md          # Questo file
        ├── main.py            # Entry point e scheduling
        └── crawler/
            ├── __init__.py
            ├── pvp.py
            ├── asteweb.py
            ├── albo_pretorio_fc.py
            ├── agrea.py
            └── bonifica.py
```

**Import sempre da core/ — mai copiare logica:**
```python
import sys
sys.path.append('../../')        # Root del monorepo
from core.db import get_connection, salva_atto, salva_classificazione
from core.classifier import classifica_atto
from core.notifier import invia_telegram
from core.config import passa_prefiltro, categorie_probabili, KEYWORDS_PER_CATEGORIA
from core.crawler.base import BaseCrawler
```

**Database:** `../../data/shared.db`
Tutti gli atti salvati con `progetto = 'agrostima'`.

---

## Fonti da monitorare — provincia FC

### Priorità 1 — Implementa subito

| Fonte | URL | Frequenza | Difficoltà |
|---|---|---|---|
| PVP Portale Vendite Pubbliche | pvp.giustizia.it | ogni 6h | media |
| AsteGiudiziarie.net | astegiudiziarie.it | ogni 6h | bassa |

### Priorità 2 — Settimana 2

| Fonte | URL | Frequenza | Difficoltà |
|---|---|---|---|
| Albo Pretorio Forlì | comune.forli.fc.it | 1x/giorno | alta |
| Albo Pretorio Cesena | comune.cesena.fc.it | 1x/giorno | alta |
| AGREA Emilia-Romagna | agrea.regione.emilia-romagna.it | 1x/giorno | media |
| Consorzio Bonifica Romagna | cbromagna.it | 1x/giorno | bassa |

### Priorità 3 — Su richiesta

| Fonte | Note |
|---|---|
| Altri comuni FC | Solo se validazione positiva |
| Compagnie assicurative | Monitoraggio manuale nella v1 |
| AGEA nazionale | Aggiunge poco rispetto ad AGREA |
| ANAS / RFI nazionali | Pianificato per espansione province |

**Comuni FC per albo pretorio (ordine di priorità):**
Forlì, Cesena, Cesenatico, Savignano sul Rubicone,
Meldola, Bertinoro, Forlimpopoli, Predappio, Civitella

---

## Filtro specifico per questo progetto

In `main.py`, dopo la classificazione AI, filtra così:
```python
def e_rilevante_per_agrostima(classificazione: dict) -> bool:
    """
    Determina se un atto classificato è rilevante
    per i periti agrari estimatori.
    """
    professionisti = classificazione.get(
        'professionisti_interessati', []
    )
    return (
        'perito_agrario' in professionisti
        and classificazione.get('rilevante', False)
    )
```

---

## Scheduling specifico
```python
# In main.py — frequenze calibrate per FC
scheduler.add_job(
    crawl_pvp,
    'interval', hours=6, id='pvp'
)
scheduler.add_job(
    crawl_asteweb,
    'interval', hours=6, id='asteweb'
)
scheduler.add_job(
    crawl_albo_pretorio,
    'cron', hour=7, id='albo'
)
scheduler.add_job(
    crawl_agrea,
    'cron', hour=8, id='agrea'
)
scheduler.add_job(
    crawl_bonifica,
    'cron', hour=8, minute=30, id='bonifica'
)
scheduler.add_job(
    crawl_assicurazioni,
    'cron', day_of_week='mon', hour=9,
    id='assicurazioni'
)
```

---

## Formato notifica Telegram
```
🌾 NUOVA OPPORTUNITÀ — {FONTE}

📋 {TITOLO}
📍 {COMUNE} (FC)
🏷️ {CATEGORIA}
📅 Scadenza: {DATA o "non specificata"}
💶 Valore: {IMPORTO o "non disponibile"}

🔗 {URL}

— AgroStima Scout • {datetime}
```

Errori al canale admin:
```
⚠️ ERRORE CRAWLER — AgroStima
Fonte: {nome}
Errore: {messaggio}
{datetime}
```

---

## Variabili d'ambiente — .env
```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID_UTENTE=chat_id_del_perito
TELEGRAM_CHAT_ID_ADMIN=chat_id_admin

# Email opzionale (v2)
RESEND_API_KEY=your_resend_key
EMAIL_DESTINATARIO=perito@email.it

# Database — punta sempre al DB condiviso
DB_PATH=../../data/shared.db

# Progetto — usato come tag nel DB
PROGETTO=agrostima

# Ambiente
ENVIRONMENT=development
```

---

## Ordine di sviluppo — non deviare
```
[ ] 1.  Verifica che core/ esista e sia completo
        (db.py, classifier.py, notifier.py, config.py,
        crawler/base.py) — se manca qualcosa, costruiscilo
        in core/ prima di toccare questo progetto

[ ] 2.  Crea .env e .env.example in questa cartella

[ ] 3.  Crea main.py con import da core/ e test
        della connessione al DB condiviso

[ ] 4.  crawler/asteweb.py — fonte più semplice,
        HTML statico, eredita da BaseCrawler

[ ] 5.  Integra asteweb in main.py con scheduling,
        verifica che scriva correttamente su shared.db
        con progetto='agrostima'

[ ] 6.  Verifica che il pre-filtro regex di core/config.py
        funzioni correttamente sugli atti di agrostima

[ ] 7.  Verifica che classifier.py classifichi correttamente
        e salvi in classificazioni senza duplicati

[ ] 8.  crawler/pvp.py

[ ] 9.  Deploy Railway — verifica 48h di stabilità

[ ] 10. crawler/albo_pretorio_fc.py
        (Forlì prima, poi Cesena)

[ ] 11. crawler/agrea.py + crawler/bonifica.py

[ ] 12. Espansione province secondo piano statistico:
        RA → BO → FE (dopo validazione FC)
```

**Nota sul punto 1:** core/ è il fondamento di tutto
il monorepo. Se stai costruendo agrostima-scout per primo,
costruisci core/ come parte di questo progetto ma
strutturalo già per essere riusato dagli altri.
Non mettere logica specifica di FC dentro core/.

---

## Espansione province — trigger e priorità

Non espandere a calendario fisso. Espandi quando:

- FC produce stabilmente 15+ opportunità rilevanti/mese
- Il tasso di apertura degli alert Telegram supera il 60%
- Almeno 3 periti paganti confermano il valore del tool

**Ordine di espansione raccomandato:**

| Fase | Province | Motivazione |
|---|---|---|
| Tier 1 (mesi 6-9) | RA, BO, FE | Confinanti, stessa vocazione agricola ER |
| Tier 2 (mesi 9-18) | MO, RE, RN | Emilia-Romagna completa |
| Tier 3 (dopo 18 mesi) | MN, CR, LO | Pianura Padana, massima SAU |

Per le province Tier 3 valuta l'aggiunta delle fonti
nazionali ANAS e RFI invece di espandere comune per comune:
coprono automaticamente tutto il territorio nazionale.

---

## Definizione di MVP completato
```
[ ] PVP e AsteGiudiziarie girano ogni 6h senza crash
[ ] Albo pretorio Forlì e Cesena monitorati ogni giorno
[ ] Pre-filtro regex elimina almeno il 70% degli atti
[ ] Classificazione Haiku gira sul restante 30%
[ ] Ogni classificazione salvata nel DB condiviso,
    mai ripetuta per lo stesso atto_id
[ ] Alert Telegram entro 10 minuti dalla scoperta
[ ] Nessun duplicato notificato mai
[ ] Errori notificati su canale admin Telegram
[ ] Sistema stabile su Railway per 7 giorni consecutivi
[ ] Almeno 3 periti agrari junior confermano che
    le opportunità trovate sono reali e rilevanti
```

---

## Costi operativi stimati a regime

| Voce | Costo mensile |
|---|---|
| Railway hosting | ~5€ |
| Claude Haiku (dopo prefiltro) | 1-3€ |
| Telegram Bot API | 0€ |
| Quote DB condiviso | 0€ |
| **Totale** | **~6-8€/mese** |

Il DB condiviso non aggiunge costi rispetto
a un DB isolato: SQLite è un file locale.
Le classificazioni già esistenti vengono riusate
gratuitamente da ogni progetto futuro.
