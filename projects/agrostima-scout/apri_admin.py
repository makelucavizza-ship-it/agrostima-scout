"""
Apre la dashboard admin nel browser senza avviare FastAPI.
Uso: python apri_admin.py
"""
import json
import os
import sys
import webbrowser
import tempfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DB_PATH = Path(__file__).resolve().parent.parent.parent / 'data' / 'shared.db'

import sqlite3

def leggi_dati():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    atti_rows = conn.execute("""
        SELECT
            ag.id, ag.titolo, ag.fonte, ag.comune, ag.provincia,
            ag.data_pubblicazione, ag.scaricato_il, ag.url,
            cl.categoria, cl.professionisti_interessati,
            cl.rilevante, cl.urgenza, cl.scadenza, cl.importo
        FROM atti_grezzi ag
        LEFT JOIN classificazioni cl ON cl.atto_id = ag.id
        ORDER BY ag.scaricato_il DESC
        LIMIT 500
    """).fetchall()

    atti = []
    for r in atti_rows:
        prof_raw = r['professionisti_interessati']
        try:
            professionisti = json.loads(prof_raw) if prof_raw else []
        except Exception:
            professionisti = []
        atti.append({
            'id': r['id'],
            'titolo': r['titolo'] or '',
            'fonte': r['fonte'] or '',
            'comune': r['comune'] or '',
            'provincia': r['provincia'] or '',
            'data_pubblicazione': r['data_pubblicazione'] or '',
            'scaricato_il': (r['scaricato_il'] or '')[:16],
            'url': r['url'] or '',
            'categoria': r['categoria'] or '',
            'professionisti': professionisti,
            'rilevante': bool(r['rilevante']),
            'urgenza': bool(r['urgenza']),
            'scadenza': r['scadenza'] or '',
            'importo': r['importo'] or '',
        })

    tot_atti = conn.execute('SELECT COUNT(*) FROM atti_grezzi').fetchone()[0]
    tot_cl = conn.execute('SELECT COUNT(*) FROM classificazioni').fetchone()[0]
    per_fonte = dict(conn.execute('SELECT fonte, COUNT(*) FROM atti_grezzi GROUP BY fonte').fetchall())
    prof_rows = conn.execute(
        'SELECT professionisti_interessati FROM classificazioni WHERE professionisti_interessati IS NOT NULL'
    ).fetchall()

    per_prof = defaultdict(int)
    for row in prof_rows:
        try:
            for p in json.loads(row[0]):
                per_prof[p] += 1
        except Exception:
            pass

    conn.close()

    stats = {
        'totali': {'atti': tot_atti, 'classificati': tot_cl},
        'per_fonte': per_fonte,
        'per_professionista': dict(sorted(per_prof.items(), key=lambda x: -x[1])),
    }
    return atti, stats


def genera_html(atti, stats):
    template_path = Path(__file__).parent / 'admin.html'
    html = template_path.read_text(encoding='utf-8')

    # Sostituisce la chiamata fetch con dati embedded
    dati_js = f"""
<script>
const _EMBEDDED_ATTI = {json.dumps(atti, ensure_ascii=False)};
const _EMBEDDED_STATS = {json.dumps(stats, ensure_ascii=False)};
</script>"""

    # Inietta i dati e sostituisce init()
    html = html.replace(
        'async function init() {',
        f'{dati_js}\nasync function init() {{'
    ).replace(
        """  const [atti, stats] = await Promise.all([
    fetch('/api/admin/atti').then(r => r.json()),
    fetch('/api/admin/stats').then(r => r.json()),
  ]);""",
        """  const atti = _EMBEDDED_ATTI;
  const stats = _EMBEDDED_STATS;"""
    )

    return html


def main():
    print('Lettura database...')
    atti, stats = leggi_dati()
    print(f'  {stats["totali"]["atti"]} atti, {stats["totali"]["classificati"]} classificati')

    print('Generazione HTML...')
    html = genera_html(atti, stats)

    tmp = tempfile.NamedTemporaryFile(
        mode='w', suffix='.html', delete=False,
        encoding='utf-8', prefix='agrostima_admin_'
    )
    tmp.write(html)
    tmp.close()

    print(f'Apertura browser: {tmp.name}')
    webbrowser.open(f'file:///{tmp.name}')
    print('Fatto.')


if __name__ == '__main__':
    main()
