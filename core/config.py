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
