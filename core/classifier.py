import json
import os
import anthropic

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    return _client


def classifica_atto(testo: str, categorie_hint: list[str]) -> dict:
    """
    Classifica un atto con Claude Haiku.
    Chiamare SOLO dopo passa_prefiltro() == True.
    Il risultato va salvato immediatamente nel DB.
    Non chiamare mai due volte per lo stesso atto_id.
    """
    testo_troncato = testo[:1500]

    prompt = f"""Classifica questo atto pubblico italiano.
Rispondi SOLO con JSON valido, nessun testo aggiuntivo.

Categorie probabili già identificate: {categorie_hint}

Atto:
{testo_troncato}

JSON richiesto:
{{
  "categoria": "esproprio|bando|determina|delibera|asta|autorizzazione|ordinanza|altro",
  "professionisti_interessati": ["perito_agrario","geometra","ingegnere","avvocato","commercialista","revisore_enti_locali","geologo","altro"],
  "urgenza": true,
  "scadenza": "YYYY-MM-DD o null",
  "importo": "numero o null",
  "parole_chiave": ["max","5","parole"],
  "rilevante": true
}}"""

    try:
        response = _get_client().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(response.content[0].text)
    except (json.JSONDecodeError, Exception):
        return {
            "categoria": "altro",
            "professionisti_interessati": [],
            "urgenza": False,
            "scadenza": None,
            "importo": None,
            "parole_chiave": [],
            "rilevante": False,
        }
