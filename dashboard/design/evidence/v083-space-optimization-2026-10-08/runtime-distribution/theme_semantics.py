"""Adaptive foregrounds derived from the canonical graph, never saved as overrides."""
from functools import lru_cache
from pathlib import Path
import json
from theme_core import contrast, ThemeError

@lru_cache(maxsize=8)
def graph(root):
    return json.loads((Path(root)/'theme-api/semantic-roles.json').read_text())

def token_specs(root):
    return {row['futureToken']:{'type':'color','default':row['legacy'].get('fixedColor','#6de0be')}
            for row in graph(str(root))['roles'].values()}

def resolve_semantics(tokens, explicit, root):
    document=graph(str(root)); roles=document['roles']; report=[]
    for name, role in roles.items():
        key=role['futureToken']
        usages=[u for u in document['usages'] if u['foreground']==name]
        pairs=[(tokens[u.get('backgroundFallbackFor',u['backgroundToken'])] if u.get('backgroundFallbackFor') in tokens else tokens[u['backgroundToken']],u['minimum']) for u in usages]
        original=tokens.get(key) if key in explicit else role['legacy'].get('fixedColor',tokens.get(role['legacy'].get('token',''), '#6de0be'))
        def valid(color): return all(contrast(color,bg)>=minimum for bg,minimum in pairs)
        if key in explicit:
            if not valid(original):
                raise ThemeError(key,'contrasto del ruolo semantico insufficiente',issues=[{'code':'contrast.semantic','path':key,'foreground':original,'background':bg,'minimum':minimum,'ratio':contrast(original,bg)} for bg,minimum in pairs if contrast(original,bg)<minimum])
            tokens[key]=original; continue
        color=original
        if not valid(color):
            channels=[int(color[i:i+2],16) for i in (1,3,5)]
            candidates=[]
            for target in (0,255):
                for step in range(1,256):
                    values=[round(v+(target-v)*step/255) for v in channels]
                    candidate='#'+''.join(f'{v:02x}' for v in values)
                    if valid(candidate): candidates.append((sum((a-b)**2 for a,b in zip(channels,values)),candidate)); break
            # A shared focus indicator can span both light and dark surfaces.
            if not candidates:
                for grey in range(256):
                    candidate=f'#{grey:02x}{grey:02x}{grey:02x}'
                    if valid(candidate): candidates.append((sum((a-grey)**2 for a in channels),candidate))
            if not candidates: raise ThemeError(key,'nessun foreground comune soddisfa le superfici dichiarate')
            color=min(candidates)[1]
        tokens[key]=color
        if color!=original: report.append({'role':key,'source':original,'derived':color,'policy':'legacyDerivedNotPersisted'})
    return report
