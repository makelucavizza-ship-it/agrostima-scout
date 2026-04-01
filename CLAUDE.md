# progetti-automation-professionisti — CLAUDE.md globale

## ⚠️ LEGGI PRIMA DI TUTTO: COMPORTAMENTO OBBLIGATORIO

Queste regole si applicano a TUTTE le sessioni, su TUTTI i progetti
del monorepo. Non possono essere ignorate o aggirate.

### Regola 1 — Pianifica prima di scrivere codice

Prima di scrivere una singola riga di codice, produci sempre
questo piano e aspetta conferma esplicita:
```
TASK: [descrizione in una riga]
FILE COINVOLTI: [lista esatta — root relativa al monorepo]
APPROCCIO: [max 5 punti]
RISCHI: [cosa potrebbe andare storto]
DOMANDE: [tutti i dubbi aperti — chiedili QUI, non a metà lavoro]
```

Se hai più di un dubbio aperto, NON procedere con il codice.

### Regola 2 — Un task alla volta, completato al 100%

Non passare al task successivo finché quello corrente non è:
scritto, testabile, integrato col resto del codice esistente.

### Regola 3 — Mai riscrivere ciò che esiste

Prima di creare un file, verifica se esiste già qualcosa
di simile nel monorepo. Prima di modificare una funzione,
leggi l'implementazione attuale. Non duplicare mai logica
tra progetti — se serve in due posti, va in core/.

### Regola 4 — Chiedi, non assumere

Se un requisito è ambiguo, fai UNA domanda specifica e aspetta.
Le assunzioni sbagliate costano più token delle domande.

### Regola 5 — Risposte brevi in fase di codice

Commenta solo:
- Il perché di scelte non ovvie
- I parametri non autoesplicativi
- I TODO espliciti

Non commentare cosa fa ogni riga. Non aggiungere prose
esplicative intorno al codice se non esplicitamente richiesto.

### Regola 6 — Leggi prima di modificare

Prima di modificare qualsiasi file esistente, leggi lo stato
attuale con il tool di lettura. Non modificare alla cieca.

### Regola 7 — Indica sempre il progetto attivo

All'inizio di ogni sessione dichiara su quale progetto stai
lavorando. Leggi il CLAUDE.md globale (questo file) e poi
il CLAUDE.md specifico del progetto in
projects/[nome-progetto]/CLAUDE.md.

### Regola 8 — Riporta la percentuale di avanzamento dopo ogni task

Al termine di ogni task completato, riporta sempre:
```
AVANZAMENTO: [X]% — [cosa è completato] / [cosa manca]
```
La percentuale si calcola rispetto all'MVP del progetto attivo
(lista di checklist nel CLAUDE.md specifico del progetto).

---

## Contesto del monorepo

Questo monorepo raccoglie tool di aggregazione automatizzata
di opportunità professionali per liberi professionisti italiani.

Il problema comune a tutti i progetti: i professionisti junior
non trovano facilmente incarichi perché le fonti sono frammentate
su decine di portali istituzionali. I senior vengono contattati
per rete personale. Questi tool colmano il gap.

Ogni progetto serve una categoria professionale specifica
in una o più province italiane.

---

## Progetti attivi e pianificati

| Progetto | Cartella | Stato | Target | Province |
|---|---|---|---|---|
| AgroStima Scout | projects/agrostima-scout | In sviluppo | Perito agrario estimatore | FC |
| GeometraScout | projects/geometra-scout | Pianificato | Geometra estimatore | - |
| RevisoriScout | projects/revisori-enti-locali | Pianificato | Revisore enti locali | - |

Ogni progetto ha il proprio CLAUDE.md in
projects/[nome]/CLAUDE.md che estende questo file
senza contraddirlo. In caso di conflitto, il file
specifico ha priorità solo per il proprio progetto.

---

## Struttura del monorepo
```
progetti-automation-professionisti/
│
├── CLAUDE.md                        # Questo file — globale
├── README.md
│
├── core/                            # Codice condiviso tra tutti i progetti
│   ├── db.py                        # Schema DB + funzioni CRUD
│   ├── classifier.py                # Classificazione AI Layer 3
│   ├── notifier.py                  # Notifiche Telegram base
│   ├── config.py                    # Config globale + keywords
│   └── crawler/
│       └── base.py                  # Classe base con retry e logging
│
├── data/
│   └── shared.db                    # Database SQLite UNICO per tutto il monorepo
│
└── projects/
    ├── agrostima-scout/
    │   ├── CLAUDE.md                # Istruzioni specifiche
    │   ├── main.py
    │   └── crawler/
    │       ├── pvp.py
    │       ├── asteweb.py
    │       └── albo_pretorio_fc.py
    ├── geometra-scout/
    │   └── CLAUDE.md
    └── revisori-enti-locali/
        └── CLAUDE.md
```

**Regola struttura:** se una funzione serve a più di un progetto,
va in core/. Se serve solo a un progetto, sta dentro
projects/[nome]/. Non derogare mai a questa regola.

---

## Architettura a tre layer — condivisa da tutti i progetti
```
LAYER 1 — RACCOLTA GREZZA (ogni crawler, ogni progetto)
Scarica tutto dalle fonti target. Zero filtri. Zero AI.
Salva testo grezzo in atti_grezzi nel DB condiviso.
Costo: zero.

LAYER 2 — PRE-FILTRO REGEX (core/config.py)
Regex su parole chiave elimina il 70-80% degli atti.
Solo gli atti rilevanti entrano nella coda classificazione.
Costo: zero.

LAYER 3 — CLASSIFICAZIONE AI (core/classifier.py)
Claude Haiku classifica gli atti filtrati.
Risultato salvato in classificazioni nel DB condiviso.
Mai classificare lo stesso atto due volte.
Il risultato viene riusato da tutti i progetti futuri.
Costo: ~0.001€ per atto, una sola volta nella vita dell'atto.
```

---

## Database condiviso — schema completo

Percorso fisico: `data/shared.db`
Tutti i progetti importano `core/db.py` e puntano
a questo file. Un solo database per tutto il monorepo.
```sql
-- Layer 1: atti grezzi scaricati dai crawler
CREATE TABLE IF NOT EXISTS atti_grezzi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fonte TEXT NOT NULL,
    progetto TEXT NOT NULL,        -- 'agrostima', 'geometra', ecc.
    comune TEXT,
    provincia TEXT,
    titolo TEXT,
    testo TEXT,
    url TEXT UNIQUE,               -- UNIQUE: previene duplicati
    data_pubblicazione TEXT,
    scaricato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Layer 3: classificazioni AI — generate una volta, riusate sempre
CREATE TABLE IF NOT EXISTS classificazioni (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    atto_id INTEGER REFERENCES atti_grezzi(id),
    categoria TEXT,
    professionisti_interessati TEXT, -- JSON array
    urgenza INTEGER DEFAULT 0,
    scadenza TEXT,
    importo TEXT,
    parole_chiave TEXT,              -- JSON array
    rilevante INTEGER DEFAULT 1,
    classificato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modello_usato TEXT DEFAULT 'claude-haiku'
);

-- Log esecuzioni crawler
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

-- Notifiche inviate — evita duplicati
CREATE TABLE IF NOT EXISTS notifiche_inviate (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    atto_id INTEGER REFERENCES atti_grezzi(id),
    progetto TEXT NOT NULL,
    canale TEXT NOT NULL,          -- 'telegram', 'email'
    inviata_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indici
CREATE INDEX IF NOT EXISTS idx_atti_url
    ON atti_grezzi(url);
CREATE INDEX IF NOT EXISTS idx_atti_progetto
    ON atti_grezzi(progetto);
CREATE INDEX IF NOT EXISTS idx_classificazioni_atto
    ON classificazioni(atto_id);
CREATE INDEX IF NOT EXISTS idx_classificazioni_professionisti
    ON classificazioni(professionisti_interessati);
```

---

## Pre-filtro regex — core/config.py
```python
# Dizionario completo delle keyword per categoria professionale.
# Ogni progetto usa il sottoinsieme rilevante per il proprio target.
# Aggiungere nuove categorie qui — mai nei file dei singoli progetti.

KEYWORDS_PER_CATEGORIA = {
    "perito_agrario": [
        "esproprio", "espropriazione", "indennità provvisoria",
        "occupazione d'urgenza", "stima", "terreno agricolo",
        "fondo rustico", "perito", "perizia", "valutazione fondiaria",
        "decreto di esproprio", "cessione volontaria", "valore agricolo",
        "coltura", "seminativo", "vigneto", "oliveto"
    ],
    "geometra": [
        "incarico professionale", "progettazione", "collaudo",
        "direzione lavori", "variante urbanistica", "piano regolatore",
        "certificato agibilità", "frazionamento", "accatastamento",
        "conformità edilizia", "sanatoria", "condono"
    ],
    "ingegnere": [
        "progetto strutturale", "relazione tecnica", "verifica sismica",
        "collaudo statico", "certificazione energetica", "impianto",
        "perizia tecnica", "consulenza tecnica"
    ],
    "avvocato": [
        "contenzioso", "patrocinio", "difensore", "consulenza legale",
        "rappresentanza legale", "ricorso", "opposizione",
        "incarico legale", "assistenza legale"
    ],
    "commercialista": [
        "revisione contabile", "collegio sindacale", "revisore",
        "bilancio", "certificazione fiscale", "consulenza fiscale"
    ],
    "revisore_enti_locali": [
        "revisore dei conti", "organo di revisione", "collegio dei revisori",
        "nomina revisore", "revisione contabile ente locale",
        "comune", "provincia", "città metropolitana"
    ],
    "geologo": [
        "relazione geologica", "indagine geotecnica", "sondaggio",
        "rischio idrogeologico", "studio geologico", "bonifica"
    ],
    "generico_alto_valore": [
        "affidamento diretto", "manifestazione di interesse",
        "selezione", "bando", "avviso pubblico", "gara",
        "incarico", "consulenza", "nomina", "conferimento"
    ]
}

# Lista piatta per pre-filtro rapido
TUTTE_LE_KEYWORDS = [
    kw for lista in KEYWORDS_PER_CATEGORIA.values()
    for kw in lista
]

def passa_prefiltro(testo: str) -> bool:
    """
    Controllo O(n) prima di qualsiasi chiamata AI.
    Restituisce True se l'atto merita classificazione.
    """
    testo_lower = testo.lower()
    return any(kw in testo_lower for kw in TUTTE_LE_KEYWORDS)

def categorie_probabili(testo: str) -> list[str]:
    """
    Identifica le categorie professionali probabilmente interessate.
    Usato per arricchire il prompt di classificazione AI.
    """
    testo_lower = testo.lower()
    return [
        categoria
        for categoria, keywords in KEYWORDS_PER_CATEGORIA.items()
        if any(kw in testo_lower for kw in keywords)
    ]
```

---

## Classificazione AI — core/classifier.py
```python
def classifica_atto(testo: str, categorie_hint: list[str]) -> dict:
    """
    Classifica un atto con Claude Haiku.
    Chiamare SOLO dopo passa_prefiltro() == True.
    Il risultato va salvato immediatamente nel DB.
    Non chiamare mai due volte per lo stesso atto_id.
    """
    testo_troncato = testo[:1500]  # Risparmio token — sufficiente per classificare

    prompt = f"""Classifica questo atto pubblico italiano.
Rispondi SOLO con JSON valido, nessun testo aggiuntivo.

Categorie probabili già identificate: {categorie_hint}

Atto:
{testo_troncato}

JSON richiesto:
{{
  "categoria": "esproprio|bando|determina|delibera|asta|autorizzazione|ordinanza|altro",
  "professionisti_interessati": ["perito_agrario","geometra","ingegnere","avvocato","commercialista","revisore_enti_locali","geologo","altro"],
  "urgenza": true|false,
  "scadenza": "YYYY-MM-DD o null",
  "importo": "numero o null",
  "parole_chiave": ["max","5","parole"],
  "rilevante": true|false
}}"""

    response = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",  # Mai Sonnet o Opus per classificazione
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )

    try:
        return json.loads(response.content[0].text)
    except json.JSONDecodeError:
        return {
            "categoria": "altro",
            "professionisti_interessati": [],
            "urgenza": False,
            "scadenza": None,
            "importo": None,
            "parole_chiave": [],
            "rilevante": False
        }
```

---

## Stack tecnico — valido per tutti i progetti

| Componente | Scelta | Vincolo |
|---|---|---|
| Linguaggio | Python 3.11+ | |
| Scraping statico | requests + BeautifulSoup4 | Prima scelta sempre |
| Scraping JS | Playwright | Solo se strettamente necessario |
| Database | SQLite in data/shared.db | Non duplicare mai il DB |
| Scheduling | APScheduler | Dentro main.py di ogni progetto |
| AI classificazione | Claude Haiku (claude-haiku-4-5-20251001) | Mai Sonnet o Opus |
| Notifiche | Telegram Bot API | Gratis, immediato |
| Email | Resend | Solo su richiesta esplicita |
| Hosting | Railway starter | Un deploy per progetto |
| Pagamenti | Stripe | Solo dalla v2 in poi |
| Frontend | Nessuno nella v1 | |
| Orchestrazione | n8n | Pianificato per v2 |

---

## Regole obbligatorie per tutti i crawler

1. Timeout su ogni richiesta HTTP: `timeout=15` sempre
2. User-Agent realistico: definito in `core/crawler/base.py`
3. Rate limiting: `time.sleep(2)` tra richieste allo stesso dominio
4. Try/except in ogni crawler: cattura tutto, logga su DB, notifica admin
5. Fallimento isolato: se un crawler crasha, gli altri continuano
6. URL UNIQUE: i duplicati vengono ignorati automaticamente dal DB

---

## Ottimizzazione token — regole di sistema

**Durante le sessioni di sviluppo:**
- Il CLAUDE.md globale + quello specifico del progetto
  sostituiscono qualsiasi rispiegazione a inizio sessione
- La pianificazione obbligatoria (Regola 1) riduce
  le iterazioni su codice scritto per requisiti ambigui
- Le risposte brevi in fase di codice (Regola 5)
  eliminano l'overhead verboso

**A runtime:**
- Pre-filtro regex elimina il 70-80% degli atti
  prima di chiamare qualsiasi AI
- Haiku invece di Sonnet: stessa qualità per classificazione,
  costo ~5x inferiore
- Testo troncato a 1.500 caratteri: sufficiente per classificare
- Classificazione lazy: ogni atto classificato una sola volta,
  mai riprocessato anche se usato da più progetti
- Risparmio complessivo stimato: 85-90% rispetto
  a un approccio non ottimizzato

**n8n (v2):** scheduling, routing notifiche e monitoring
settimanale migreranno su n8n per eliminare
completamente il loro overhead dalle sessioni di lavoro.

---

## Cosa NON fare — mai, in nessun progetto

- Non duplicare logica tra projects/ — va in core/
- Non creare un secondo file SQLite — tutto in data/shared.db
- Non classificare lo stesso atto_id due volte
- Non chiamare Claude senza aver passato passa_prefiltro()
- Non usare Sonnet o Opus per la classificazione
- Non passare testo completo ad Haiku — tronca a 1.500 caratteri
- Non aggiungere frontend nella v1 di nessun progetto
- Non implementare Stripe prima della v2
- Non usare Docker nella v1
- Non scrivere test automatici nella v1
- Non passare al task successivo con un bug aperto nel precedente
- No n8n nella v1 — pianificato per v2

---

## Costi operativi stimati a regime (per progetto)

| Voce | Costo mensile |
|---|---|
| Railway hosting | ~5€ |
| Claude Haiku classificazione | 1-3€ |
| Telegram Bot API | 0€ |
| Resend email (opzionale) | 0€ |
| **Totale per progetto** | **~6-8€/mese** |

Il database condiviso non aggiunge costi: SQLite è un file locale,
le classificazioni già esistenti vengono riusate gratuitamente
da ogni nuovo progetto senza rielaborazione.

---

## Come iniziare una sessione di lavoro

1. Apri la cartella root `progetti-automation-professionisti/`
   in Claude Code — mai la sottocartella del singolo progetto
2. Dichiara il progetto attivo:
   *"Stiamo lavorando su agrostima-scout"*
3. Claude legge questo file + il CLAUDE.md specifico del progetto
4. Prima di qualsiasi task, produci il piano (Regola 1)
   e aspetta conferma
