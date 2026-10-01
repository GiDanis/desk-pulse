"""One-shot Tuya Cloud discovery probe. No commands or background service."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys

from tuya_core import CloudClient, TuyaError, load_config, read_inventory, synchronize


def default_config():
    return Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'smartpc/tuya-cloud.json'


def init_config(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    template = {'endpoint': '', 'access_id': '', 'access_secret': '', 'uid': ''}
    try:
        with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as stream:
            json.dump(template, stream, indent=2); stream.write('\n')
    except FileExistsError:
        raise TuyaError('config', 'File già presente: non è stato sovrascritto.') from None
    print('Configurazione creata con permessi 600: ' + str(path))
    print('Compilare dal portale Tuya Developer; non inserire chiavi o password in chat.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=default_config())
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--init-config', action='store_true')
    modes.add_argument('--check-config', action='store_true')
    parser.add_argument('--cache', type=Path, default=Path(os.environ.get('XDG_CACHE_HOME', str(Path.home()/'.cache'))) / 'smartpc/tuya-inventory.json')
    parser.add_argument('--device-index', type=int, action='append', default=[], help='Indice 1-based dell’elenco appena acquisito, ripetibile fino a 4 volte.')
    args = parser.parse_args(argv)
    try:
        if args.init_config:
            init_config(args.config); return 0
        config = load_config(args.config)
        if args.check_config:
            print('Configurazione valida; accesso cloud non ancora verificato.'); return 0
        if len(args.device_index) > 4 or any(i < 1 for i in args.device_index):
            raise TuyaError('config', 'Scegliere al massimo quattro indici positivi.')
        client = CloudClient(config)
        snapshot, changes = synchronize(client, args.cache)
        print(f'Elenco aggiornato: {len(snapshot["devices"])} dispositivi; {client.request_count} richieste.')
        print(f'Aggiunti {len(changes["added"])} · rimossi {len(changes["removed"])} · rinominati {len(changes["renamed"])} · modelli modificati {len(changes["replaced"])}')
        for index, device in enumerate(snapshot['devices'], 1):
            availability = 'online secondo Tuya' if device['online'] is True else 'offline secondo Tuya' if device['online'] is False else 'disponibilità sconosciuta'
            print(f'{index}. {device["name"]} · {device["category"] or "tipo non indicato"} · {availability}')
        for index in dict.fromkeys(args.device_index):
            if index > len(snapshot['devices']):
                raise TuyaError('config', 'Indice fuori dall’elenco: consultare gli indici appena mostrati.')
            device = snapshot['devices'][index - 1]
            # Membership is resolved from the current complete account inventory.
            rows = client.device_data(device['id'])
            print('\n' + device['name'] + ' · ultimo stato riportato dal cloud:')
            for row in rows:
                value = 'Dato da verificare' if row['value'] is None else 'Attivo' if row['value'] is True else 'Disattivo' if row['value'] is False else str(row['value'])
                print(f'  {row["code"]}: {value} {row["unit"]}'.rstrip())
        print(f'Richieste totali: {client.request_count}. Nessun comando inviato.')
        return 0
    except TuyaError as error:
        print(str(error), file=sys.stderr)
        if error.kind != 'config':
            previous = read_inventory(args.cache, client.scope)
            if previous:
                print(f'Elenco salvato disponibile: {len(previous["devices"])} dispositivi; non certifica gli stati attuali.', file=sys.stderr)
        return 2
    except OSError:
        print('Impossibile leggere o salvare un file locale; controllare percorso e permessi.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
