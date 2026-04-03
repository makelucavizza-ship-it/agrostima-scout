# AgroStima Scout — CLAUDE.md

## Stato attuale

MVP esteso al bacino FC + RN + RA. Sistema in fase di validazione.
I periti del territorio si spostano fino a 1h30 — le tre province
sono il bacino naturale di riferimento, non FC da sola.

**Progetto attivo:** `agrostima-scout`
**Database:** `../../data/shared.db`
**Tag DB:** `progetto = 'agrostima'`

---

## Struttura file

```
progetti-automation-professionisti/
├── core/
│   ├── db.py
│   ├── classifier.py
│   ├── notifier.py
│   ├── config.py
│   └── crawler/base.py
└── projects/agrostima-scout/
    ├── CLAUDE.md
    ├── main.py
    ├── dashboard.html       # Frontend minimo — selezione provincia + raggio
    └── crawler/
        ├── pvp.py
        ├── asteweb.py
        ├── albo_pretorio_fc.py
        ├── albo_pretorio_rn.py   # Da implementare
        ├── albo_pretorio_ra.py   # Da implementare
        ├── agrea.py
        └── bonifica.py
```

---

## Regole di comportamento

**Prima di scrivere codice**, produci sempre questo piano e aspetta conferma:
```
TASK:
FILE COINVOLTI:
APPROCCIO: (max 5 punti)
RISCHI:
DOMANDE:
```

- Un task alla volta, completato al 100%
- Leggi sempre il file prima di modificarlo
- Se manca qualcosa in core/, costruiscilo lì — mai duplicare logica
- Risposte brevi in fase di codice: commenta solo il perché, non il cosa

---

## Fonti — stato attuale e prossimi passi

### Fonti nazionali — aprire a tutto il territorio (modifica minima)

| Fonte | Stato | Cosa fare |
|---|---|---|
| PVP Portale Vendite Pubbliche | Attivo solo FC | Rimuovere filtro provincia dalla query |
| AsteGiudiziarie.net | Attivo solo FC | Rimuovere filtro provincia dalla query |

Queste due fonti coprono già tutto il territorio nazionale.
La modifica è probabilmente un parametro nella query HTTP — verificare
il crawler esistente prima di toccare qualsiasi altra cosa.

### Fonti regionali — già coprono FC + RN + RA

| Fonte | Stato |
|---|---|
| AGREA Emilia-Romagna | Attivo, nessuna modifica necessaria |

### Fonti provinciali — da estendere

| Fonte | FC | RN | RA |
|---|---|---|---|
| Albo Pretorio comuni principali | Attivo (Forlì, Cesena) | Da implementare | Da implementare |
| Consorzio di Bonifica | Attivo (Romagna) | Rimandato | Rimandato |

**Comuni prioritari per RN:**
Rimini, Riccione, Santarcangelo di Romagna, Cattolica, Novafeltria

**Comuni prioritari per RA:**
Ravenna, Faenza, Lugo, Cervia, Bagnacavallo

### Fonti assicurative
Monitoraggio manuale per ora. Nessun portale strutturato da scrapare nella v1.
Rivalutare in v2 se Unipol Agro o Groupama pubblicano bandi in formato accessibile.

---

## Frontend minimo — dashboard.html

Un singolo file HTML standalone (nessun backend aggiuntivo, legge da shared.db).

**Funzionalità richieste:**
- Selezione provincia di origine del perito (FC / RN / RA)
- Slider o input per il raggio di spostamento accettato (km)
- Lista delle opportunità filtrate per distanza dalla provincia selezionata
- Nessun login, nessuna autenticazione nella v1

**Logica di filtro:**
Il filtro per raggio si basa sulla provincia dell'atto (`provincia` in `atti_grezzi`),
non sulle coordinate geografiche — troppo costoso da implementare ora.
Mappatura semplice: FC/RN/RA sempre incluse, province confinanti
incluse se il raggio supera una soglia ragionevole (es. >80km).

**Stack:** HTML + JS vanilla, nessun framework, nessuna dipendenza esterna.
Connessione al DB tramite endpoint FastAPI minimale se necessario,
oppure export JSON schedulato da main.py — valutare l'approccio
più semplice prima di implementare.

---

## Checklist MVP esteso

```
[x] PVP e AsteGiudiziarie attivi ogni 6h (solo FC)
[x] Albo pretorio Forlì e Cesena ogni giorno
[x] Pre-filtro regex operativo
[x] Classificazione Haiku sul 30% rimanente
[x] Classificazioni salvate in shared.db senza duplicati
[x] Alert Telegram entro 10 minuti
[x] Nessun duplicato notificato
[x] Errori su canale admin Telegram
[ ] PVP e AsteGiudiziarie aperti a tutto il nazionale
[ ] Albo pretorio comuni RN
[ ] Albo pretorio comuni RA
[ ] dashboard.html con filtro provincia + raggio
[ ] Stabilità Railway 7 giorni consecutivi
[ ] 3 periti confermano rilevanza opportunità sul bacino FC+RN+RA
```

---

## Trigger di validazione (misurati su FC + RN + RA)

| Metrica | Trigger espansione |
|---|---|
| Opportunità rilevanti/mese (bacino totale) | ≥ 15 |
| Tasso apertura alert Telegram | ≥ 60% |
| Periti paganti soddisfatti | ≥ 3 |

---

## Espansione province — dopo la validazione

| Fase | Province | Quando |
|---|---|---|
| Tier 1 | MO, RE, BO, FE | Dopo validazione bacino FC+RN+RA |
| Tier 2 | Emilia-Romagna completa | Mesi 9-18 |
| Tier 3 | MN, CR, LO (Pianura Padana) | Dopo 18 mesi — valutare ANAS/RFI nazionali |

---

## Cosa NON fare ora

- Nuove province oltre FC+RN+RA
- Consorzi di bonifica locali per RN e RA
- Autenticazione o login nel frontend
- Stripe
- Docker
- Test automatici
- n8n (v2)

---

## Costi a regime

Railway ~5€ + Haiku 1-3€ = **6-8€/mese**

---

## Import standard

```python
import sys
sys.path.append('../../')
from core.db import get_connection, salva_atto, salva_classificazione
from core.classifier import classifica_atto
from core.notifier import invia_telegram
from core.config import passa_prefiltro, categorie_probabili, KEYWORDS_PER_CATEGORIA
from core.crawler.base import BaseCrawler
```

## Formato notifica Telegram

```
🌾 NUOVA OPPORTUNITÀ — {FONTE}

📋 {TITOLO}
📍 {COMUNE} ({PROVINCIA})
🏷️ {CATEGORIA}
📅 Scadenza: {DATA o "non specificata"}
💶 Valore: {IMPORTO o "non disponibile"}

🔗 {URL}

— AgroStima Scout • {datetime}
```

Errori admin:
```
⚠️ ERRORE CRAWLER — AgroStima
Fonte: {nome}
Errore: {messaggio}
{datetime}
```
