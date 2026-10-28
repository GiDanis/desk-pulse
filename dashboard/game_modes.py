"""Stable session contracts. Legacy modes remain readable, never certify laps."""
MAX_RACE_DRIVERS = 5

MODES = {
    'impara': ('Impara', 'Un pilota · un giro per tentativo · base pronta e affinamento della guida.'),
    'qualifica': ('Qualifica', 'Una vettura · lancio e tre giri cronometrati · pesi congelati.'),
    'gara': ('Gara', '2–5 versioni qualificate · griglia dal miglior giro.'),
    'impara_infinito': ('Impara giro infinito', 'Giri continui fino a incidente, stallo o Pausa.'),
    'impara_sorpasso': ('Impara sorpasso', 'Sorpassi e difesa con bot congelati · un solo pilota apprende.'),
}
LEARNING = frozenset(('impara', 'impara_infinito', 'impara_sorpasso'))
CONTINUOUS = LEARNING - {'impara'}
LEGACY = frozenset(('prova', 'campione'))
GRID = {'fastest_first': 'Più veloce davanti', 'slowest_first': 'Più lento davanti'}
QUALIFICATION_PROTOCOL = 'flying-lap-1'

def learning(mode): return mode in LEARNING

def label(mode): return MODES.get(mode, (mode, ''))[0]

def lap_time(value):
    if value is None: return '—'
    ms = round(float(value)*1000)
    minutes, rest = divmod(ms, 60000)
    seconds, milliseconds = divmod(rest, 1000)
    return f'{minutes}:{seconds:02},{milliseconds:03}'

def qualified_snapshot(driver, track):
    from game_catalog import scope_hash
    for cert in driver.get('timedQualifications', []) if driver else []:
        if (cert.get('protocol') == QUALIFICATION_PROTOCOL and cert.get('track') == track
            and not cert.get('releaseArchived')
            and cert.get('profile',{}).get('learningBackend')==driver['profile'].get('learningBackend')
            and cert.get('scope') == scope_hash(track, cert['profile']['observation'])
            and cert.get('bestLap', 0) > 0 and cert.get('policy')):
            return cert
    return None

def grid_order(drivers, track, order):
    if order not in GRID: raise ValueError('Ordine griglia non valido')
    entries=[]
    for driver in drivers:
        cert=qualified_snapshot(driver, track)
        if not cert: raise ValueError('Serve almeno un giro valido di Qualifica su questo circuito')
        entries.append((driver, cert))
    return sorted(entries, key=lambda x: ((1 if order == 'fastest_first' else -1)*x[1]['bestLap'], tuple((1 if order == 'fastest_first' else -1)*v for v in sorted(l['time'] for l in x[1]['laps'])), x[0]['number'], x[0]['id']))
