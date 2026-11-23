"""Calendar rules, independent of Qt, rendering and wall-clock scheduling."""
import random

DAY = 86400


def deadline(started, days):
    if type(days) is not int or not 0 <= days <= 3650:
        raise ValueError('Permanenza non valida: da 0 a 3650 giorni')
    return started + days * DAY if days else None


def choose_species(species, pool, counts, recent, seed, *, previous='', next_species=''):
    """Explicit successor overrides cooldown; auto favours diversity without loops."""
    eligible=[s for s in species if s in pool and counts.get(s,0)<2]
    if next_species:
        return next_species if next_species in species and counts.get(next_species,0)<2 else None
    eligible=[s for s in eligible if s!=previous and s not in recent]
    if not eligible:return None
    minimum=min(counts.get(s,0) for s in eligible)
    options=sorted(s for s in eligible if counts.get(s,0)==minimum)
    return random.Random(seed).choice(options)
