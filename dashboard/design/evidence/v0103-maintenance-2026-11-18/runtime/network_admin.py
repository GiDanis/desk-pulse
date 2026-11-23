"""Local LAN preference administration. Stop the dashboard before writing aliases."""
import argparse
import json
import os
from pathlib import Path
from iliadbox import IliadboxClient, load_config
from network_core import NetworkStore, display, text


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))/'smartpc/iliadbox/app.json')
    parser.add_argument('--state-dir',type=Path,default=Path(os.environ.get('XDG_STATE_HOME',str(Path.home()/'.local/state')))/'smartpc/network')
    parser.add_argument('--identity');parser.add_argument('--alias');args=parser.parse_args()
    client=IliadboxClient(load_config(args.config));store=NetworkStore(args.state_dir,client.scope);snapshot=store.load()
    if args.alias is not None:
        if not args.identity or not any(d['id']==args.identity for d in snapshot['devices']) or len(args.alias)>80:
            parser.error('Identità nota e alias di massimo 80 caratteri richiesti.')
        prefs=snapshot['preferences'];alias=text(args.alias,80).strip()
        if alias:prefs['aliases'][args.identity]=alias
        else:prefs['aliases'].pop(args.identity,None)
        store.commit(preferences=prefs)
        print('Alias locale salvato. Riavvia la dashboard per rileggerlo.')
    else:
        print(json.dumps([{'id':d['id'],'name':d['name'],'originalName':d['originalName']} for d in display(snapshot,'stale',0)['devices']],ensure_ascii=False,indent=2))

if __name__=='__main__':main()
