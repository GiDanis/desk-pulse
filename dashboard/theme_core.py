"""Pure theme resolver: complete snapshots, inheritance, validation and catalogs."""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re
from theme_trace_hooks import recorder_for, trace_span

ROOT=Path(__file__).parent
ID=re.compile(r'^[a-z][a-z0-9_.-]{0,63}$')
HEX=re.compile(r'^#[0-9a-fA-F]{6}$')
FIELDS={'schemaVersion','id','name','version','extends','tokens','palettes','presentations','motion','scene','iconSetId','iconApiVersion','iconOverrides','assets','requirements'}

class ThemeError(ValueError):
    def __init__(self,path,message,*,issues=None):
        self.path=path; self.message=message
        self.issues=issues or []
        super().__init__(f'{path}: {message}')

def read_json(path):
    path=Path(path)
    if path.stat().st_size>128*1024: raise ThemeError(str(path),'manifest troppo grande')
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result: raise ValueError('chiave duplicata: '+key)
            result[key]=value
        return result
    try: return json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=unique)
    except (ValueError,UnicodeError) as error: raise ThemeError(str(path),'JSON non valido') from error

def merge(left,right):
    result=deepcopy(left)
    for key,value in right.items():
        result[key]=merge(result[key],value) if isinstance(value,dict) and isinstance(result.get(key),dict) else deepcopy(value)
    return result

def contained(base,path):
    if not isinstance(path,str) or not path: raise ThemeError('path','percorso richiesto')
    base=Path(base).resolve(); result=(base/path).resolve()
    if not result.is_relative_to(base): raise ThemeError(str(path),'percorso fuori dal pacchetto')
    return result

def contrast(a,b):
    def lum(color):
        rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)]
        rgb=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in rgb]
        return sum(x*y for x,y in zip(rgb,(.2126,.7152,.0722)))
    hi,lo=sorted((lum(a),lum(b)),reverse=True)
    return (hi+.05)/(lo+.05)


def contrast_rules():
    """One product contrast contract shared by runtime and authoring diagnostics."""
    for text in ('textPrimary','textSecondary'):
        for surface in ('surface','surfaceFocused','backgroundOverlay','background','bannerSurface'):
            yield 'colors.'+text, 'colors.'+surface, 4.5, 'contrast.'+text+'.'+surface
    yield 'colors.accent', 'colors.surfaceFocused', 3, 'contrast.focus'
    for mode in ('small','large','urgent','badge','inbox','detail'):
        prefix='notifications.'+mode+'.'
        for role in ('titleColor','bodyColor','sourceColor','accent'):
            yield prefix+role, prefix+'surface', 3 if role=='accent' else 4.5, prefix+role
        if mode=='inbox':
            for role,minimum in (('focusedTitleColor',4.5),('focusedBodyColor',4.5),('focusedSourceColor',4.5),('accent',3)):
                yield prefix+role,prefix+'focusedSurface',minimum,prefix+role


def contrast_issues(tokens, trace=None):
    recorder = recorder_for(trace)
    if recorder is not None:
        with recorder.span("catalog.contrast", tokenCount=len(tokens)):
            return _contrast_issues(tokens)
    return _contrast_issues(tokens)


def _contrast_issues(tokens):
    issues=[]
    for foreground,background,minimum,path in contrast_rules():
        ratio=contrast(tokens[foreground],tokens[background])
        if ratio < minimum:
            message='contrasto inferiore a 4,5:1' if minimum==4.5 else 'indicatore insufficiente'
            if background.endswith('focusedSurface'):message='contrasto insufficiente sulla selezione'
            issues.append({'code':'contrast.minimum','path':path,'message':message,
                           'foregroundRole':foreground,'backgroundRole':background,
                           'foreground':tokens[foreground],'background':tokens[background],
                           'ratio':ratio,'minimum':minimum})
    return issues

class ThemeCatalog:
    def __init__(self,user_directory=None,root=ROOT,*,trace=None):
        self._trace=trace
        self.root=Path(root); self.user_directory=Path(user_directory) if user_directory else None
        self.contract=read_json(self.root/'themes/token-contract.json')['tokens']
        from theme_semantics import token_specs
        self.contract.update(token_specs(self.root))
        self.presentations={}; self.recipes={}; self.icon_sets={}; self.packs={}; self.directories={}; self.errors=[]
        self.reload()

    @trace_span("catalog.reload")
    def reload(self):
        self.errors=[]; self.packs={}; self.directories={}; self.asset_cache={}
        self.contract=read_json(self.root/'themes/token-contract.json')['tokens']
        from theme_semantics import token_specs
        self.contract.update(token_specs(self.root))
        self.icon_renderers=read_json(self.root/'icons/renderers.json')['renderers']
        self.scene_renderers=read_json(self.root/'scenes/registry.json')['renderers']
        self.presentations={row['id']:row for row in read_json(self.root/'presentations/registry.json')['presentations']}
        self.recipes=read_json(self.root/'motion/registry.json')['recipes']
        self.icon_sets=read_json(self.root/'icons/catalog.json')['sets']
        # Extensions are distributed application code, not imported theme data.
        for file in sorted((self.root/'extensions').glob('*/manifest.json')):
            ext=read_json(file)
            if ext.get('apiVersion')!=1: raise ThemeError(str(file),'API estensione non supportata')
            for row in ext.get('presentations',[]):
                self._register(self.presentations,row['id'],row,file)
            for identifier,row in ext.get('recipes',{}).items(): self._register(self.recipes,identifier,row,file)
            for identifier,row in ext.get('iconRenderers',{}).items(): self._register(self.icon_renderers,identifier,row,file)
            for identifier,row in ext.get('sceneRenderers',{}).items(): self._register(self.scene_renderers,identifier,row,file)
            for identifier,row in ext.get('iconSets',{}).items(): self._register(self.icon_sets,identifier,row,file)
            for path,descriptor in ext.get('tokens',{}).items():
                if not path.startswith('ext.') or path in self.contract: raise ThemeError(path,'namespace duplicato/non valido')
                self.contract[path]=descriptor
        folders=[self.root/'themes/packs']+([self.user_directory] if self.user_directory else [])
        for folder in folders:
            for file in sorted(folder.glob('*/theme.json')):
                try:
                    pack=read_json(file); self.validate_pack(pack)
                    if pack['id'] in self.packs: raise ThemeError(pack['id'],'ID duplicato')
                    self.packs[pack['id']]=pack; self.directories[pack['id']]=file.parent
                except (OSError,ThemeError) as error: self.errors.append(str(error))
        for identifier in list(self.packs):
            try:
                for variant in ('day','night'): self.resolve(identifier,variant=variant,check_assets=False)
            except (OSError,ThemeError) as error:
                self.errors.append(str(error)); self.packs.pop(identifier,None)
        if 'base' not in self.packs: raise ThemeError('base','fallback distribuito mancante/non valido')

    def _register(self,registry,identifier,row,file):
        if not ID.fullmatch(identifier) or identifier in registry: raise ThemeError(str(file),'ID estensione duplicato/non valido')
        if isinstance(row,dict) and 'file' in row:
            contained(self.root,row['file'])
        registry[identifier]=deepcopy(row)

    @trace_span("catalog.validatePack")
    def validate_pack(self,pack):
        if not isinstance(pack,dict) or type(pack.get('schemaVersion')) is not int or pack.get('schemaVersion')!=1: raise ThemeError('schemaVersion','formato non supportato')
        unknown=set(pack)-FIELDS
        if unknown: raise ThemeError(sorted(unknown)[0],'campo sconosciuto')
        if not isinstance(pack.get('id'),str) or not ID.fullmatch(pack['id']): raise ThemeError('id','ID non valido')
        if not isinstance(pack.get('name'),str) or not 1<=len(pack['name'])<=80: raise ThemeError('name','nome non valido')
        if not isinstance(pack.get('version'),str) or not re.fullmatch(r'\d+\.\d+\.\d+',pack['version']): raise ThemeError('version','versione semantica richiesta')
        for field in ('tokens','palettes','presentations','motion','scene','iconOverrides'):
            if not isinstance(pack.get(field,{}),dict): raise ThemeError(field,'oggetto richiesto')
        if set(pack.get('palettes',{}))-{'day','night'}: raise ThemeError('palettes','variante sconosciuta')
        self.validate_tokens(pack.get('tokens',{}))
        for variant,values in pack.get('palettes',{}).items(): self.validate_tokens(values)
        if pack.get('extends') is not None and (not isinstance(pack['extends'],str) or not ID.fullmatch(pack['extends'])): raise ThemeError('extends','ID genitore non valido')
        if not isinstance(pack.get('iconSetId','builtin.plain'),str): raise ThemeError('iconSetId','ID richiesto')
        if not isinstance(pack.get('requirements',[]),list) or not all(isinstance(x,str) for x in pack.get('requirements',[])): raise ThemeError('requirements','lista di capacità richiesta')
        if pack.get('iconApiVersion',1)!=1: raise ThemeError('iconApiVersion','API non supportata')
        if not isinstance(pack.get('assets',[]),list): raise ThemeError('assets','lista richiesta')
        if len(pack.get('assets',[]))>64: raise ThemeError('assets','troppe risorse')
        if set(pack.get('requirements',[]))-{'presentation1','motion1','icons1','scene1'}: raise ThemeError('requirements','capacità non supportata')

    @trace_span("catalog.validateTokens")
    def validate_tokens(self,values):
        if not isinstance(values,dict): raise ThemeError('tokens','oggetto richiesto')
        for path,value in values.items():
            spec=self.contract.get(path)
            if not spec: raise ThemeError(path,'token sconosciuto')
            kind=spec['type']
            valid=HEX.fullmatch(value) if kind=='color' and isinstance(value,str) else isinstance(value,str) and len(value)<=120 if kind=='string' else type(value) is bool if kind=='bool' else type(value) is int if kind=='int' else type(value) in (int,float) and math.isfinite(value) if kind=='real' else False
            if not valid: raise ThemeError(path,'tipo/valore non valido')
            if 'minimum' in spec and not spec['minimum']<=value<=spec['maximum']: raise ThemeError(path,'fuori intervallo')
            if 'enum' in spec and value not in spec['enum']: raise ThemeError(path,'scelta non valida')

    def chain(self,identifier,seen=()):
        if not isinstance(identifier,str): raise ThemeError('id','ID richiesto')
        if identifier in seen: raise ThemeError('extends','ciclo di eredità')
        if len(seen)>8: raise ThemeError('extends','eredità troppo profonda')
        pack=self.packs.get(identifier)
        if not pack: raise ThemeError('id','tema o genitore non disponibile: '+identifier)
        return (self.chain(pack['extends'],seen+(identifier,)) if pack.get('extends') else [])+[pack]

    @trace_span("catalog.resolve")
    def resolve(self,identifier,overrides=None,variant='day',motion_mode='normal',check_assets=True):
        if variant not in ('day','night') or motion_mode not in ('normal','reduced','off'): raise ThemeError('environment','policy non valida')
        resolved={'tokens':{path:deepcopy(spec['default']) for path,spec in self.contract.items()},'palettes':{'day':{},'night':{}},'presentations':{},'motion':{},'scene':{'enabled':False,'renderer':'builtin.actor','skin':'plain'},'iconSetId':'builtin.plain','iconOverrides':{},'assets':[]}
        chain=self.chain(identifier); assets={}
        for pack in chain:
            resolved=merge(resolved,{key:pack[key] for key in ('tokens','palettes','presentations','motion','scene','iconSetId','iconOverrides') if key in pack})
            for asset in pack.get('assets',[]):
                if not isinstance(asset,dict) or not isinstance(asset.get('id'),str) or not ID.fullmatch(asset['id']): raise ThemeError('assets.id','ID non valido')
                path=contained(self.directories[pack['id']],asset.get('path',''))
                if not path.is_file() or path.stat().st_size>8*1024*1024: raise ThemeError(asset['id'],'risorsa mancante/troppo grande')
                if asset.get('type') not in ('font','image','data'): raise ThemeError(asset['id'],'tipo risorsa non supportato')
                digest=asset.get('sha256','')
                if check_assets:
                    stamp=(str(path),path.stat().st_size,path.stat().st_mtime_ns)
                    digest=self.asset_cache.get(stamp)
                    recorder=recorder_for(self._trace)
                    if recorder is not None:
                        recorder.record('catalog.assetHashCache', hit=digest is not None, assetId=asset['id'])
                    if digest is None:
                        if recorder is not None:
                            with recorder.span('catalog.assetHash',assetId=asset['id'],fileBytes=stamp[1]):
                                with path.open('rb') as stream: digest=hashlib.file_digest(stream,'sha256').hexdigest()
                        else:
                            with path.open('rb') as stream: digest=hashlib.file_digest(stream,'sha256').hexdigest()
                        self.asset_cache[stamp]=digest
                    if asset.get('sha256') and digest!=asset['sha256']: raise ThemeError(asset['id'],'hash non corrispondente')
                assets[asset['id']]={**asset,'file':str(path),'sha256':digest}
        resolved['assets']=list(assets.values())
        resolved['tokens']=merge(resolved['tokens'],resolved['palettes'][variant])
        overrides={} if overrides is None else overrides
        if not isinstance(overrides,dict): raise ThemeError('overrides','oggetto richiesto')
        if set(overrides)-{'tokens','presentations','motion','scene','iconOverrides','iconSetId'}: raise ThemeError('overrides','campo sconosciuto')
        resolved=merge(resolved,overrides)
        for section in ('tokens','presentations','motion','scene','iconOverrides'):
            if not isinstance(resolved.get(section),dict): raise ThemeError(section,'oggetto richiesto')
        explicit = set(overrides.get('tokens', {}))
        for pack in chain:
            explicit.update(pack.get('tokens', {}))
            explicit.update(pack.get('palettes', {}).get(variant, {}))
        for path, spec in self.contract.items():
            if spec.get('inherit') and path not in explicit:
                resolved['tokens'][path] = deepcopy(resolved['tokens'][spec['inherit']])
        self.validate_tokens(resolved['tokens'])
        for path,spec in self.contract.items():
            if 'effectiveMaximum' in spec and resolved['tokens'][path]*resolved['tokens']['typography.textScale']>spec['effectiveMaximum']: raise ThemeError(path,'dimensione effettiva incompatibile con il layout standard')
        from theme_semantics import resolve_semantics
        resolved['semanticDerivations']=resolve_semantics(resolved['tokens'],explicit,self.root)
        failures=contrast_issues(resolved['tokens'],trace=self._trace)
        if identifier in getattr(self,'bundle_revisions',{}):
            failures=[issue for issue in failures if issue['path']!='contrast.focus']
        if failures:
            first=failures[0]
            raise ThemeError(first['path'],first['message'],issues=failures)
        for mode in ('small','large','urgent','badge','inbox','detail'):
            prefix = 'notifications.' + mode + '.'
            width, height = resolved['tokens'][prefix+'width'], resolved['tokens'][prefix+'height']
            x, offset = resolved['tokens'][prefix+'insetX'], resolved['tokens'][prefix+'insetY']
            anchor = resolved['tokens'][prefix+'anchor']
            y = offset if anchor == 'top' else 640-height-offset if anchor == 'bottom' else (640-height)/2+offset
            if x+width > 960 or y < 0 or y+height > 640:
                raise ThemeError(prefix+'geometry', 'superficie fuori dal viewport 960×640')
            if min(width,height) <= 2*resolved['tokens'][prefix+'padding']:
                raise ThemeError(prefix+'padding', 'nessuna area disponibile per il contenuto')
        for prefix in ('banner.small','banner.large','alerts.badge','alerts.inbox','alerts.detail'):
            for suffix in ('enter','exit'):
                event = prefix+'.'+suffix
                if event not in resolved['motion']:
                    fallback = ('banner.' if prefix.startswith('banner.') else 'panel.')+suffix
                    resolved['motion'][event] = deepcopy(resolved['motion'].get(fallback,self.packs['base']['motion'][fallback]))
        required={content for row in self.presentations.values() if row.get('fallback') for content in row['contentIds']}
        # Existing standalone schema-1 packs acquire new notification fallbacks.
        for row in self.presentations.values():
            if row.get('fallback'):
                for content in row['contentIds']:
                    if content.startswith('alerts.') or content in ('casa.inventory', 'network.inventory', 'overlay.summary'): resolved['presentations'].setdefault(content,row['id'])
        if required-set(resolved['presentations']): raise ThemeError('presentations','contenuti obbligatori mancanti')
        for content,identifier_p in resolved['presentations'].items():
            if not isinstance(identifier_p,str): raise ThemeError('presentations.'+content,'ID richiesto')
            row=self.presentations.get(identifier_p)
            if not row or content not in row['contentIds']: raise ThemeError('presentations.'+content,'presentazione incompatibile')
            if content.startswith('alerts.') and row.get('contextApi') not in ('notification1','NotificationContext'): raise ThemeError('presentations.'+content,'NotificationContext API 1 richiesto')
            if not contained(row.get('sourceRoot',self.root),row['file']).is_file(): raise ThemeError('presentations.'+content,'componente mancante')
            layout = row.get('layoutContract')
            if content.startswith('alerts.') and layout:
                mode = content.rsplit('.',1)[-1]
                prefix = 'notifications.'+mode+'.'
                values = {key[len(prefix):]:value for key,value in resolved['tokens'].items() if key.startswith(prefix)}
                scale = resolved['tokens']['typography.textScale']
                # Conservative line envelope for the shipped templates. Alternate
                # renderers own their layout contract; engine geometry stays open.
                line = lambda size: math.ceil(size*scale*1.5)
                pad,gap=values['padding'],values['gap']
                title,body,guide,source=(line(values[key+'Size']) for key in ('title','body','guide','source'))
                minimum = 0
                if layout == 'large-stack': minimum = 2*pad+2*guide+title+body+(source if values['showSource'] else 0)+gap*(4 if values['showSource'] else 3)
                elif layout == 'poster': minimum = 2*pad+48+guide+title+body+(source if values['showSource'] else 0)+gap*(3 if values['showSource'] else 2)
                elif layout == 'large-split': minimum = 2*pad+max(42+title+guide+3*gap,body+guide+(2*source if values['showSource'] else 0)+2*gap)
                elif layout == 'urgent-stack': minimum = 2*pad+8+2*guide+title+body+(2*source if values['showSource'] else 0)+5*gap
                elif layout == 'inbox': minimum = pad+92+guide+(source if values['showSource'] else 0)+2*gap+16+title+body+min(10,gap)
                elif layout == 'detail': minimum = 2*pad+3*gap+line(resolved['tokens']['typography.size37'])+guide+body
                elif layout not in ('small-line','badge'): raise ThemeError('layoutContract','contratto template sconosciuto')
                if values['height'] < minimum:
                    raise ThemeError(prefix+'height','spazio insufficiente per testo e comandi del template; aumentare altezza o ridurre misure/spaziature')
                if values['width'] < 2*pad+2*max(values['titleSize'],values['guideSize'])*scale:
                    raise ThemeError(prefix+'width','spazio insufficiente per il template selezionato')
        for event,recipe in resolved['motion'].items():
            if not isinstance(recipe,dict) or not isinstance(recipe.get('recipe'),str) or recipe.get('recipe') not in self.recipes: raise ThemeError('motion.'+event,'ricetta non disponibile')
            allowed=self.recipes[recipe['recipe']].get('events')
            legacy_event = ('banner.'+event.rsplit('.',1)[-1] if event.startswith(('banner.small.','banner.large.')) else
                            'panel.'+event.rsplit('.',1)[-1] if event.startswith(('alerts.badge.','alerts.inbox.','alerts.detail.')) else event)
            if allowed is not None and event not in allowed and legacy_event not in allowed: raise ThemeError('motion.'+event,'ricetta incompatibile con questo evento')
            if event=='urgent.present' and (recipe['recipe']!='builtin.cut' or recipe.get('durationMs')!=0): raise ThemeError('motion.urgent.present','gli avvisi urgenti richiedono presentazione immediata')
            if type(recipe.get('durationMs')) not in (int,float) or not 0<=recipe['durationMs']<=600: raise ThemeError('motion.'+event,'durata non valida')
            if type(recipe.get('distancePx')) not in (int,float) or not 0<=recipe['distancePx']<=80: raise ThemeError('motion.'+event,'ampiezza non valida')
            for parameter,spec in self.recipes[recipe['recipe']].get('parameters',{}).items():
                if parameter in recipe and (type(recipe[parameter]) not in (int,float) or not math.isfinite(recipe[parameter]) or not spec['minimum']<=recipe[parameter]<=spec['maximum']): raise ThemeError('motion.'+event+'.'+parameter,'parametro non valido')
            if recipe.get('easing') not in ('linear','outCubic','outQuad','inOutQuad'): raise ThemeError('motion.'+event,'curva non supportata')
        if not isinstance(resolved['iconSetId'],str) or resolved['iconSetId'] not in self.icon_sets: raise ThemeError('iconSetId','set non disponibile')
        if sum(Path(a['file']).stat().st_size for a in resolved['assets'])>24*1024*1024: raise ThemeError('assets','budget file per tema superato')
        scene=resolved['scene']
        if type(scene.get('enabled')) is not bool or not isinstance(scene.get('renderer'),str) or scene.get('renderer') not in self.scene_renderers: raise ThemeError('scene','renderer non disponibile')
        bundle = getattr(self, 'bundle_metadata', {}).get(identifier)
        if bundle:
            selected = self.scene_renderers[scene['renderer']]
            identity = selected.get('rendererIdentity', {})
            pin = self.bundle_revisions[identifier]
            own_revision = pin['id'] + '@' + pin['version'] + '#' + pin['digest']
            selected_owned = (selected.get('apiVersion') == 2
                and identity.get('origin') == 'bundle' and identity.get('revision') == own_revision)
            claims_owned = 'scene.main' in bundle['coverage']['surfaces']
            if claims_owned != selected_owned or not claims_owned and selected.get('apiVersion') == 2:
                raise ThemeError('coverage.scene.main', 'renderer scena incompatibile con la copertura della revisione selezionata')
        resolved.pop('palettes')
        resolved.update(themeId=identifier,themeVersion=chain[-1]['version'],variant=variant,motionMode=motion_mode)
        resolved['presentationRegistry']=deepcopy(self.presentations); resolved['motionRegistry']=deepcopy(self.recipes)
        resolved['iconRegistry']=deepcopy(self.icon_renderers)
        resolved['sceneRegistry']=deepcopy(self.scene_renderers)
        if self.scene_renderers[scene['renderer']].get('apiVersion') == 2:
            resolved['presentations']['scene.main']=scene['renderer']
            resolved['presentationRegistry'][scene['renderer']]={**deepcopy(self.scene_renderers[scene['renderer']]),'contentIds':['scene.main']}
        resolved['icons']=merge(self.icon_sets[resolved['iconSetId']],resolved['iconOverrides'])
        for key,icon in resolved['icons'].items():
            if not ID.fullmatch(key) or not isinstance(icon,(str,dict)): raise ThemeError('icons.'+key,'descrittore non valido')
            if isinstance(icon,dict):
                if icon.get('backend') not in ('geometry','glyph','image','component'): raise ThemeError('icons.'+key,'backend sconosciuto')
                if icon.get('backend')=='geometry' and not isinstance(icon.get('symbol'),str): raise ThemeError('icons.'+key,'simbolo richiesto')
                if icon.get('backend')=='component' and (not isinstance(icon.get('renderer'),str) or icon.get('renderer') not in self.icon_renderers): raise ThemeError('icons.'+key,'renderer sconosciuto')
                if icon.get('backend')=='glyph' and (not isinstance(icon.get('glyph'),str) or len(icon['glyph'])!=1 or not isinstance(icon.get('family'),str)): raise ThemeError('icons.'+key,'glifo/famiglia non valido')
                if icon.get('backend')=='image' and (not isinstance(icon.get('asset'),str) or icon.get('asset') not in assets or assets[icon['asset']]['type']!='image'): raise ThemeError('icons.'+key,'asset sconosciuto')
        for registry in ('presentationRegistry','motionRegistry','iconRegistry','sceneRegistry'):
            for descriptor in resolved[registry].values():
                if isinstance(descriptor,dict) and 'file' in descriptor:
                    path=contained(descriptor.get('sourceRoot',self.root),descriptor['file'])
                    if not path.is_file(): raise ThemeError(registry,'componente mancante: '+str(path))
                    descriptor['sourceUrl']=path.as_uri()
                    descriptor.setdefault('rendererKey','app:'+descriptor['file'])
        resolved['parents']=[{'id':p['id'],'version':p['version']} for p in chain]
        if identifier in getattr(self, 'bundle_layouts', {}):
            resolved['layout'] = deepcopy(self.bundle_layouts[identifier])
        return resolved
