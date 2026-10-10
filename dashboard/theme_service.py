"""Application-owned theme state. Only discrete changes cross Python/QML."""
from copy import deepcopy
from collections import OrderedDict
import json
import os
import time
from pathlib import Path

from PySide6.QtCore import QObject, Property, QRunnable, QSettings, QStandardPaths, QThreadPool, QTimer, Signal, Slot
from PySide6.QtGui import QFontDatabase, QGuiApplication, QImageReader
from theme_core import ThemeError
from theme_runtime import make_catalog, preflight
from theme_bundle import BundleManager, atomic_json
from theme_lifecycle import LifecycleManager, BASE, selection_key
from theme_api import PublicContextFactory, _plain as plain_qml_value
from theme_trace_hooks import recorder_for, trace_span, trace_operation, trace_generation


class SaveResult(QObject):
    finished = Signal(bool, str)


class SaveJob(QRunnable):
    def __init__(self, configuration, result, *, profiles=None, trace=None, request_id=None):
        super().__init__()
        self._trace=trace; self._trace_request=request_id
        self.configuration = deepcopy(configuration)
        self.profiles=deepcopy(profiles) if profiles is not None else None
        self.result = result

    def run(self):
        recorder=recorder_for(self._trace)
        if recorder is not None:
            with recorder.scope(self._trace_request), recorder.span('save.worker'):
                self._run()
        else:
            self._run()

    def _run(self):
        settings = QSettings('SmartPC', 'Dashboard')
        values={'appearance/config':json.dumps(self.configuration,ensure_ascii=False,sort_keys=True),
                'animationsEnabled':self.configuration['motionMode']!='off',
                'nightMode':self.configuration.get('paletteMode','auto')}
        if self.profiles is not None: values['appearance/themeOverrides']=json.dumps(self.profiles,ensure_ascii=False,sort_keys=True)
        previous={key:settings.value(key) for key in values}
        settings.setAtomicSyncRequired(True)
        for key,value in values.items(): settings.setValue(key,value)
        settings.sync()
        ok = settings.status() == QSettings.Status.NoError
        if not ok:
            for key,value in previous.items():
                if value is None: settings.remove(key)
                else: settings.setValue(key,value)
            settings.sync()
        recorder=recorder_for(self._trace)
        if recorder is not None: recorder.record('save.worker.finished',ok=ok)
        self.result.finished.emit(ok, '' if ok else 'Impossibile salvare le preferenze. La bozza resta disponibile.')


class PackJob(QRunnable):
    def __init__(self, operation, store, catalog, configuration, result):
        super().__init__()
        self.operation=operation; self.store=store; self.catalog=catalog
        self.configuration=deepcopy(configuration); self.result=result

    def run(self):
        from theme_pack import import_pack, export_pack
        from datetime import datetime
        try:
            if self.operation=='import':
                inbox=self.store.parent/'theme-imports'; imported=[]
                for folder in sorted(inbox.iterdir()) if inbox.is_dir() else []:
                    if folder.name.startswith('.'): continue
                    if folder.suffix in ('.smartpc-theme','.zip') or folder.is_dir() and (folder/'bundle.json').is_file():
                        revision=BundleManager(self.store.parent,app_root=self.catalog.root).import_bundle(folder,preflight=preflight,require_preflight=True)
                        imported.append(revision['id']+' '+revision['version']); continue
                    if not folder.is_dir() or not (folder/'theme.json').is_file(): continue
                    identifier=json.loads((folder/'theme.json').read_text())['id']
                    if identifier in self.catalog.packs: continue
                    imported.append(import_pack(folder,self.store,root=self.catalog.root))
                message='Importati: '+', '.join(imported) if imported else 'Nessun nuovo pacchetto in '+str(inbox)
            else:
                stamp=datetime.now().strftime('%Y%m%d-%H%M%S-%f')
                identifier='personal.export.'+stamp.replace('-','')
                output=self.store.parent/'theme-exports'/identifier
                if self.configuration.get('bundleRevision'):
                    output=output.with_suffix('.smartpc-theme')
                    BundleManager(self.store.parent,app_root=self.catalog.root).export_bundle(self.configuration['bundleRevision'],output)
                else:
                    export_pack(self.catalog,self.configuration['themeId'],output,new_id=identifier,overrides=self.configuration['overrides'])
                message='Esportato: '+str(output)
            self.result.finished.emit(True,message)
        except (ThemeError,OSError,ValueError,KeyError) as error:
            self.result.finished.emit(False,str(error))


class FontRegistry:
    """QFontDatabase is process-wide. Deduplicate by asset digest, retire unused IDs."""
    entries = {}
    clock = 0
    idle_capacity = 4

    @classmethod
    def acquire(cls, assets, families, trace=None):
        recorder=recorder_for(trace)
        needed = set()
        result = {}
        for value in families:
            if not value.startswith('asset:'): continue
            identifier = value[6:]
            asset = next((a for a in assets if a['id'] == identifier and a['type'] == 'font'), None)
            if not asset: raise ThemeError('font.'+identifier, 'risorsa font non disponibile')
            key = asset['sha256']; needed.add(key)
            if recorder is not None: recorder.record('font.acquire',assetId=identifier,digest=key,reused=key in cls.entries)
            if key not in cls.entries:
                if recorder is not None:
                    with recorder.span('font.register',assetId=identifier,digest=key):
                        number = QFontDatabase.addApplicationFont(asset['file'])
                        names = QFontDatabase.applicationFontFamilies(number) if number >= 0 else []
                else:
                    number = QFontDatabase.addApplicationFont(asset['file'])
                    names = QFontDatabase.applicationFontFamilies(number) if number >= 0 else []
                if not names: raise ThemeError('font.'+identifier, 'font non caricabile')
                cls.entries[key] = {'id':number, 'family':names[0], 'owners':set(), 'touched':0}
            cls.clock += 1; cls.entries[key]['touched'] = cls.clock
            result[value] = cls.entries[key]['family']
        return needed, result

    @classmethod
    def update(cls, owner, needed, trace=None):
        recorder=recorder_for(trace)
        if recorder is not None: recorder.record("font.owners",needed=len(needed),registered=len(cls.entries))
        for key, entry in list(cls.entries.items()):
            if key in needed: entry['owners'].add(owner)
            else: entry['owners'].discard(owner)
        inactive=sorted((key for key,entry in cls.entries.items() if not entry['owners']), key=lambda key:cls.entries[key]['touched'])
        for key in inactive[:-cls.idle_capacity]:
            if recorder is not None: recorder.record('font.remove',digest=key)
            QFontDatabase.removeApplicationFont(cls.entries[key]['id']); del cls.entries[key]


class ThemeService(QObject):
    changed = Signal()
    editorChanged = Signal()
    saveFinished = Signal(bool)
    candidateChanged = Signal()
    frameStateChanged = Signal()
    transferFinished = Signal(bool,str)
    themeOperationChanged = Signal()
    themeActivationFinished = Signal(bool)

    def __init__(self, parent=None, *, store=None, root=None, trace=None):
        super().__init__(parent)
        self._trace=trace; self._save_trace_request=None; self._save_frame_deadline=None
        self._latest_verified_ticks=0; self._latest_health_key=""; self._latest_compacted_key=""; self._latest_cleanup_scheduled=False
        location = store or os.environ.get('SMARTPC_THEME_STORE') or str(Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))/'themes')
        self.store = Path(location)
        self._root = Path(root) if root else Path(__file__).parent
        self.bundles = BundleManager(self.store.parent,app_root=self._root)
        self.lifecycle = LifecycleManager(self.store.parent,app_root=self._root)
        self._activation = None; self._activation_frame = False; self._gui_ready = False
        self._auto_apply = False; self._auto_saved = False; self._theme_timed_out = False
        self._theme_operation = {'busy':False,'phase':'idle','message':''}
        self._theme_deadline = QTimer(self)
        self._theme_deadline.setSingleShot(True)
        self._theme_deadline.setInterval(18000)
        self._theme_deadline.timeout.connect(self._theme_operation_timeout)
        self._leases = {}; self._api_factory = PublicContextFactory(self)
        self._lease_fonts = {}
        self._lease_font_catalog = None
        self._bundle_metadata_cache = OrderedDict()
        self.catalog = make_catalog(self.store,self._root,trace=trace)
        settings = QSettings('SmartPC', 'Dashboard')
        legacy = str(settings.value('animationsEnabled','true')).lower() not in ('false','0')
        legacy_palette = settings.value('nightMode','auto')
        if legacy_palette not in ('auto','day','night'): legacy_palette = 'auto'
        self._image_sizes = {}; self._resolved_cache = OrderedDict(); self._operation_pending = False
        self._committed = {'schemaVersion':1, 'themeId':'base', 'overrides':{}, 'motionMode':'normal' if legacy else 'off', 'paletteMode':legacy_palette}
        self._variant = 'day'; self._revision = 0; self._snapshot = {}; self._draft = None
        self._error = ''; self._status = 'ready'; self._pending = None
        try: self._profiles=json.loads(settings.value('appearance/themeOverrides','{}'))
        except (TypeError,ValueError): self._profiles={}
        if not isinstance(self._profiles,dict): self._profiles={}
        self._profiles={key:value for key,value in self._profiles.items()
                        if isinstance(key,str) and isinstance(value,dict)
                        and all(isinstance(value.get(section,{}),dict) for section in ('tokens','presentations','motion','scene','iconOverrides'))}
        self._draft_profiles=None; self._pending_profiles=None
        self._candidate = None; self._candidate_config = None; self._draft_valid = True; self._generation = 0; self._active_content = ''; self._staged_fonts = set()
        self._prepared_contents = set(); self._awaiting_contents = set()
        self._font_owner = id(self)
        self._save_result = SaveResult(self)
        self._save_result.finished.connect(self._saved)
        self._pack_result = SaveResult(self)
        self._pack_result.finished.connect(self._pack_finished)
        if recorder_for(self._trace) is not None:
            self._trace.bind_service(self)
        # Recovery is required even before the first appearance preference has
        # been saved (for example, a crash during the first bundle preview).
        recovery=self.lifecycle.recover()
        journal=self.lifecycle.read()
        saved = settings.value('appearance/config')
        if saved:
            try:
                config = json.loads(saved)
                if not isinstance(config,dict): raise ThemeError('configuration','oggetto richiesto')
                config.setdefault('paletteMode',settings.value('nightMode','auto'))
                if recovery['recovered'] or journal.get('lastRecovery') or config.get('bundleRevision',BASE) != journal['active']:
                    chosen=journal['active']
                    if chosen == BASE:
                        previous=self._previous_configuration()
                        config=previous if previous and 'bundleRevision' not in previous else {**config,'themeId':'base','overrides':{}}
                        config.pop('bundleRevision',None)
                    else:
                        config.update(themeId=chosen['id'],bundleRevision=chosen,overrides=journal['adaptations']['perRevision'].get(selection_key(chosen),{}))
                    self._status='recovery'; self._error='Tema recuperato dopo attivazione interrotta'
                self._validate_config(config)
                self._committed = config
            except (ValueError, TypeError, ThemeError) as error:
                self._error = 'Preferenze recuperate con Base: '+str(error); self._status = 'recovery'
        elif journal['active'] != BASE:
            self._committed.update(themeId=journal['active']['id'],bundleRevision=journal['active'],
                                   overrides=journal['adaptations']['perRevision'].get(selection_key(journal['active']),{}))
        try:
            self._committed=self._normalize_adjustments(self._committed)
            self._publish(self._committed)
        except (ThemeError,ValueError,OSError) as error:
            self._error = 'Risorse recuperate con Base: '+str(error); self._status = 'recovery'
            self._committed = {'schemaVersion':1,'themeId':'base','overrides':{},'motionMode':'normal','paletteMode':'auto'}
            self._publish(self._committed)
        self.destroyed.connect(lambda: FontRegistry.update(self._font_owner, set(),trace=self._trace))

    @Property(QObject,constant=True)
    def apiFactory(self): return self._api_factory

    @Slot(str)
    def recoverScene(self, message):
        self._recover_base(message)

    @Property(bool,notify=frameStateChanged)
    def needsFrameAcknowledgement(self): return not self._gui_ready or bool(self._activation and not self._activation_frame)

    @Slot(int,bool)
    def acknowledgeThemeFrame(self, revision, coherent):
        if revision != self._revision or not coherent: return
        self._gui_ready=True
        if self._activation:
            self._activation_frame=True
        self.frameStateChanged.emit()
        self.editorChanged.emit()
        if self._auto_apply:
            if self._auto_saved:
                self._finish_theme_operation(True)
            else:
                QTimer.singleShot(0, self._apply_selected_theme)

    @Slot()
    @Slot(bool)
    def heartbeat(self, coherent=True):
        # A responsive GUI can still lose a committed renderer's readiness.
        # Only a real coherent submitted frame can make it ready again.
        if not coherent and self._gui_ready:
            self._gui_ready=False
            self._activation_frame=False
            self.frameStateChanged.emit()
            self.editorChanged.emit()
        transitioning = bool(self._candidate or self._auto_apply or self._activation and not self._activation_frame)
        self.lifecycle.heartbeat(ready=self._gui_ready and not self._theme_timed_out, transition=transitioning)
        health_key=selection_key(self._committed.get('bundleRevision',BASE))
        if health_key != self._latest_health_key:
            self._latest_health_key=health_key; self._latest_verified_ticks=0
        if coherent and self._gui_ready and not self.editing and self._status == 'ready':
            self._latest_verified_ticks += 1
            if self._latest_verified_ticks >= 3: self._schedule_latest_cleanup()
        else:
            self._latest_verified_ticks = 0

    def _schedule_latest_cleanup(self):
        pin=self._committed.get('bundleRevision')
        if not pin or self._latest_cleanup_scheduled or self._latest_verified_ticks < 3:
            return
        if selection_key(pin) == self._latest_compacted_key or self._bundle_metadata(self._committed).get('retention') != 'latest':
            return
        self._latest_cleanup_scheduled=True
        QTimer.singleShot(0,self._compact_latest)

    def _compact_latest(self):
        self._latest_cleanup_scheduled=False
        pin=self._committed.get('bundleRevision')
        if not pin or self.editing or not self._gui_ready or self._status != 'ready': return
        try:
            report=self.lifecycle.finalize_latest(pin)
            # Recovery settings must not point to a payload which was removed.
            base={**deepcopy(self._committed),'themeId':'base','overrides':{}}
            base.pop('bundleRevision',None)
            atomic_json(self.store.parent/'theme-previous-configuration.json',base)
            self.catalog=make_catalog(self.store,self._root,selected=pin,trace=self._trace)
            prefix=pin['id']+'@'
            active_key=selection_key(pin)
            self._profiles={key:value for key,value in self._profiles.items() if not key.startswith(prefix) or key == active_key}
            settings=QSettings('SmartPC','Dashboard')
            settings.setValue('appearance/themeOverrides',json.dumps(self._profiles,ensure_ascii=False,sort_keys=True))
            settings.sync()
            if not report['retained']: self._latest_compacted_key=selection_key(pin)
            self.editorChanged.emit()
        except (ThemeError,OSError,ValueError):
            # Cleanup never withdraws a valid active renderer; retry on a later
            # heartbeat/lease release, under the lifecycle manager lock.
            return


    def _cancel_activation(self):
        if self._activation:
            self.lifecycle.cancel(self._activation['ticket'])
            self._activation=None; self._activation_frame=False
            self.frameStateChanged.emit()

    def _begin_activation(self, configuration):
        self._cancel_activation()
        atomic_json(self.store.parent/'theme-previous-configuration.json',self._committed)
        identity=configuration.get('bundleRevision',BASE)
        self._activation=self.lifecycle.begin(identity,configuration['overrides'])
        self._activation_frame=False
        self.frameStateChanged.emit()

    def _previous_configuration(self):
        """A backup is advisory; damage must never abort canonical recovery."""
        path=self.store.parent/'theme-previous-configuration.json'
        try:
            previous=json.loads(path.read_text()) if path.is_file() else {}
            if previous:
                self._validate_config(previous)
            return previous
        except (OSError,ThemeError,ValueError,TypeError):
            return {}

    @Slot(int,result=bool)
    def stepRevision(self, direction):
        if self._draft is None or self._pending is not None or self._operation_pending: return False
        versions=[r for r in getattr(self.catalog,'installed_bundle_revisions',[]) if r['id']==self._draft['themeId']]
        if not versions: self._error='Il tema distribuito non ha revisioni importate'; self.editorChanged.emit(); return False
        pin=self._draft.get('bundleRevision',{})
        index=next((i for i,r in enumerate(versions) if r['digest']==pin.get('digest')),-1)
        chosen=versions[(index+(1 if direction>=0 else -1))%len(versions)]
        self._remember_draft()
        candidate=deepcopy(self._draft)
        candidate['bundleRevision']={k:chosen[k] for k in ('id','version','digest')}
        # A revision has its own visual overrides; do not carry renderer IDs across versions.
        candidate['overrides']=deepcopy((self._draft_profiles or {}).get(self._profile_key(candidate),self.lifecycle.read()['adaptations']['perRevision'].get(selection_key(candidate['bundleRevision']),{})))
        scale=self._draft.get('overrides',{}).get('tokens',{}).get('typography.textScale')
        if scale is not None: candidate['overrides'].setdefault('tokens',{})['typography.textScale']=scale
        return self._change(candidate)

    @Slot('QVariantMap',result=str)
    def acquireRevision(self, identity):
        if not identity or identity.get('origin')!='bundle': return ''
        pin={'id':identity['revision'].split('@')[0],'version':identity['revision'].split('@')[1].split('#')[0],'digest':identity['digest']}
        token=self.lifecycle.acquire(pin,'renderer')
        try:
            if self._lease_font_catalog is not self.catalog:
                self._lease_fonts.clear()
                self._lease_font_catalog = self.catalog
            key = selection_key(pin)
            entry = self._lease_fonts.get(key)
            # Catalog assets are immutable between reloads. Check file identity
            # before reusing font digests; changed files take the full resolver.
            if entry is None or entry[1] != self._font_file_stamp(entry[2]):
                assets = self.catalog.resolve(pin['id'])['assets'] if getattr(self.catalog,'bundle_revisions',{}).get(pin['id'])==pin else []
                fonts = [asset for asset in assets if asset['type']=='font']
                files = tuple(Path(asset['file']) for asset in fonts)
                entry = ({asset.get('sha256') for asset in fonts}, self._font_file_stamp(files), files)
                if len(self._lease_fonts) >= 8:
                    self._lease_fonts.pop(next(iter(self._lease_fonts)))
                self._lease_fonts[key] = entry
            digests=entry[0]
            FontRegistry.update('host:'+token,digests,trace=self._trace)
            self._leases[token]=True
        except Exception:
            FontRegistry.update('host:'+token,set(),trace=self._trace)
            self.lifecycle.release(token)
            raise
        return token

    @staticmethod
    def _font_file_stamp(files):
        return tuple((str(path), info.st_dev, info.st_ino, info.st_size,
                      info.st_mtime_ns, info.st_ctime_ns)
                     for path in files for info in [path.stat()])

    @Slot(str)
    def releaseRevision(self, token):
        if token in self._leases:
            FontRegistry.update('host:'+token,set(),trace=self._trace)
            self.lifecycle.release(token); self._leases.pop(token,None)
            self._schedule_latest_cleanup()

    @trace_span("service.data")
    def _data(self, configuration, variant):
        pin=configuration.get('bundleRevision')
        if pin:
            self.lifecycle._available(pin)
            self.bundles.verify_revision(pin)
        key=(json.dumps(configuration,sort_keys=True,separators=(',',':')),variant)
        cached=self._resolved_cache.get(key)
        recorder=recorder_for(self._trace)
        if recorder is not None: recorder.record('service.cache.lookup',hit=cached is not None,variant=variant,entries=len(self._resolved_cache))
        if cached is not None:
            result,stamps=cached
            try:
                unchanged=all((Path(path).stat().st_size,Path(path).stat().st_mtime_ns)==stamp for path,stamp in stamps.items())
            except OSError: unchanged=False
            if unchanged:
                self._resolved_cache.move_to_end(key)
                if recorder is not None:
                    with recorder.span('service.cache.copy',variant=variant): return deepcopy(result)
                return deepcopy(result)
            if recorder is not None: recorder.record('service.cache.invalidate',variant=variant)
            self._resolved_cache.pop(key,None)
        pin=configuration.get('bundleRevision')
        if pin and getattr(self.catalog,'bundle_revisions',{}).get(configuration['themeId']) != pin:
            self.catalog=make_catalog(self.store,self._root,selected=pin,trace=self._trace)
        result=self.catalog.resolve(configuration['themeId'],configuration['overrides'],variant,configuration['motionMode'])
        stamps={a['file']:(Path(a['file']).stat().st_size,Path(a['file']).stat().st_mtime_ns) for a in result['assets']}
        if recorder is not None:
            with recorder.span('service.cache.store',variant=variant):
                self._resolved_cache[key]=(deepcopy(result),stamps)
        else:
            self._resolved_cache[key]=(deepcopy(result),stamps)
        while len(self._resolved_cache)>32:self._resolved_cache.popitem(last=False)
        return result

    def _bundle_metadata(self, configuration, *, load=False):
        """Exact immutable revision metadata; QML getters never read the store."""
        pin=configuration.get('bundleRevision')
        if not pin: return {}
        key=selection_key(pin)
        metadata=getattr(self.catalog,'bundle_revision_metadata',{}).get(key) or self._bundle_metadata_cache.get(key)
        if metadata is None and load:
            metadata=deepcopy(self.bundles.verify_revision(pin)['manifest'])
            self._bundle_metadata_cache[key]=metadata
            while len(self._bundle_metadata_cache)>32: self._bundle_metadata_cache.popitem(last=False)
        return metadata or {}

    def _adjustments(self, configuration, *, load=False):
        metadata=self._bundle_metadata(configuration,load=load)
        if not configuration.get('bundleRevision'): return ['paletteMode','textScale','motionMode']
        # Reduced/Off remain system policy even when an author declares no controls.
        return sorted(set(metadata.get('adjustments',[])) | {'motionMode'})

    def _normalize_adjustments(self, configuration):
        allowed=self._adjustments(configuration,load=True)
        if 'paletteMode' not in allowed: configuration['paletteMode']='auto'
        if 'textScale' not in allowed:
            configuration.get('overrides',{}).get('tokens',{}).pop('typography.textScale',None)
        return configuration

    def _guard_adjustment(self, name):
        if name in self._adjustments(self._draft,load=True): return True
        self._error='Adattamento non supportato dal tema: '+name
        self.editorChanged.emit()
        return False

    def _theme_metadata(self, identifier, configuration=None):
        pack=self.catalog.packs[identifier]
        configuration=configuration or {'themeId':identifier,'bundleRevision':getattr(self.catalog,'bundle_revisions',{}).get(identifier)}
        metadata=self._bundle_metadata(configuration)
        coverage=metadata.get('coverage',{})
        own=len(coverage.get('surfaces',[])); fallback=len(coverage.get('fallbacks',[]))
        mode=coverage.get('mode','builtin')
        summary=('Completo · '+str(own)+' visuali propri') if mode=='complete' else ('Parziale · '+str(own)+' propri · '+str(fallback)+' Base') if mode=='partial' else 'Visuali distribuiti con la dashboard'
        return {'id':identifier,'name':pack['name'],'version':(configuration.get('bundleRevision') or {}).get('version',pack['version']),
                'coverageMode':mode,'ownCount':own,'fallbackCount':fallback,'coverageSummary':summary,
                'adjustments':self._adjustments(configuration),'retention':metadata.get('retention','all')}

    @trace_span("service.validateConfig")
    def _validate_config(self, configuration):
        if not isinstance(configuration,dict) or type(configuration.get('schemaVersion')) is not int or configuration.get('schemaVersion') != 1 or set(configuration)-{'schemaVersion','themeId','overrides','motionMode','paletteMode','bundleRevision'}:
            raise ThemeError('configuration','formato non supportato')
        if not all(key in configuration for key in ('themeId','overrides','motionMode')): raise ThemeError('configuration','campi obbligatori mancanti')
        if 'bundleRevision' in configuration:
            if not isinstance(configuration['bundleRevision'],dict) or configuration['bundleRevision'].get('id') != configuration['themeId']:
                raise ThemeError('bundleRevision','identità diversa dal tema selezionato')
            # An empty/partial identity is not an implicit legacy selection.
            selection_key(configuration['bundleRevision'])
        if configuration.get('paletteMode','auto') not in ('auto','day','night'): raise ThemeError('paletteMode','modalità non valida')
        if not isinstance(configuration.get('overrides'),dict): raise ThemeError('overrides','oggetto richiesto')
        for variant in ('day','night'):
            self._data(configuration,variant)

    @trace_span("service.resolve")
    def _resolve(self, configuration):
        result = self._data(configuration,self._variant)
        image_bytes = 0
        recorder=recorder_for(self._trace)
        for asset in result['assets']:
            if asset['type'] != 'image': continue
            size = self._image_sizes.get(asset['sha256'])
            if recorder is not None: recorder.record('image.headerCache',assetId=asset['id'],hit=size is not None)
            if size is None:
                if recorder is not None:
                    with recorder.span('image.header',assetId=asset['id']):
                        reader = QImageReader(asset['file']); dimensions = reader.size()
                        if not reader.canRead() or not dimensions.isValid(): raise ThemeError(asset['id'],'immagine non decodificabile')
                        size = dimensions.width()*dimensions.height()*4
                else:
                    reader = QImageReader(asset['file']); dimensions = reader.size()
                    if not reader.canRead() or not dimensions.isValid(): raise ThemeError(asset['id'],'immagine non decodificabile')
                    size = dimensions.width()*dimensions.height()*4
                self._image_sizes[asset['sha256']] = size
            image_bytes += size
        if image_bytes > 24*1024*1024: raise ThemeError('assets.images','budget texture per tema superato')
        font_keys = [key for key in result['tokens'] if key.endswith('Family') and self.catalog.contract[key]['type'] == 'string']
        families = [result['tokens'][key] for key in font_keys]
        families += [v['family'] for v in result['icons'].values() if isinstance(v,dict) and v.get('backend')=='glyph']
        needed, replacements = FontRegistry.acquire(result['assets'],families,trace=self._trace)
        available_families=set(QFontDatabase.families())
        default_family=QGuiApplication.font().family()
        for key in font_keys:
            value = result['tokens'][key]
            if not value:
                result['tokens'][key] = default_family
            else:
                if value not in replacements and value not in available_families: raise ThemeError(key,'famiglia font non disponibile')
                result['tokens'][key] = replacements.get(value,value)
        for icon in result['icons'].values():
            if isinstance(icon,dict) and icon.get('backend')=='glyph':
                if icon['family'] not in replacements and icon['family'] not in available_families: raise ThemeError('icon.family','famiglia font non disponibile')
                icon['family'] = replacements.get(icon['family'],icon['family'])
                font = __import__('PySide6.QtGui',fromlist=['QRawFont','QFont'])
                raw = font.QRawFont.fromFont(font.QFont(icon['family']))
                if not raw.supportsCharacter(ord(icon['glyph'])): raise ThemeError('icon.glyph','glifo mancante nel font')
        return result, needed

    @trace_span("service.publish")
    def _publish(self, configuration, prepared=None):
        configuration=self._normalize_adjustments(deepcopy(configuration))
        result, needed = prepared if prepared is not None else self._resolve(configuration)
        result.pop('generation', None); result.pop('requiredContents', None)
        self._revision += 1
        result['revision'] = self._revision
        self._gui_ready=False
        self.frameStateChanged.emit()
        result['paletteMode'] = configuration.get('paletteMode','auto')
        result['bundleRevision']=deepcopy(configuration.get('bundleRevision',{}))
        result['adjustments']=self._adjustments(configuration)
        result['coverage']=deepcopy(self._bundle_metadata(configuration).get('coverage',{}))
        if self._activation: self.lifecycle.mark_ready(self._activation['ticket'])
        self._visible = deepcopy(configuration)
        self._snapshot = result
        self._active_fonts = needed; self._staged_fonts = set()
        FontRegistry.update(self._font_owner, needed,trace=self._trace)
        if recorder_for(self._trace) is not None: self._trace.published(self._revision)
        self.changed.emit()
        if self._auto_apply and self._pending is None:
            self._update_theme_operation(phase='presenting',message='Verifica della nuova schermata…')

    @Property('QVariantMap',notify=candidateChanged)
    def candidateAppearance(self): return deepcopy(self._candidate or {})

    @Slot(str)
    def setActiveContent(self, content):
        if content == self._active_content: return
        self._active_content = content
        if self._candidate is not None:
            candidate = deepcopy(self._candidate_config)
            self._restart_candidate(candidate)

    @Slot('QStringList')
    def setPreparedContents(self, contents):
        """Selected notification renderers participate even while hidden/prewarmed."""
        prepared = set(contents)
        if prepared == self._prepared_contents:
            return
        self._prepared_contents = prepared
        if self._candidate is not None:
            candidate = deepcopy(self._candidate_config)
            self._restart_candidate(candidate)

    def _restart_candidate(self, candidate):
        if recorder_for(self._trace) is not None:
            with self._trace.correlate_generation(self._candidate['generation']):
                self._clear_candidate()
                self._change(candidate)
        else:
            self._clear_candidate()
            self._change(candidate)

    def _clear_candidate(self, retain_fonts=None, *, trace_outcome='superseded'):
        if self._candidate is not None and recorder_for(self._trace) is not None:
            self._trace.cleared(self._candidate['generation'],outcome=trace_outcome)
        self._candidate = None; self._candidate_config = None; self._generation += 1; self._staged_fonts = set()
        self._awaiting_contents = set()
        FontRegistry.update(self._font_owner,self._active_fonts | (retain_fonts or set()),trace=self._trace)
        self.candidateChanged.emit()

    @Slot(int,bool,str)
    def acceptCandidate(self, generation, ok, message):
        self.reportCandidate(generation, self._active_content, ok, message)

    @Slot(int,str,bool,str)
    @trace_generation
    def reportCandidate(self, generation, content, ok, message):
        recorder=recorder_for(self._trace)
        reason=('noCandidate' if self._candidate is None else 'staleGeneration' if generation != self._candidate['generation'] else 'unexpectedContent' if content not in self._awaiting_contents else 'accepted')
        if recorder is not None: recorder.record('candidate.ack',generation=generation,contentId=content,ok=ok,reason=reason)
        if reason != 'accepted': return
        self._awaiting_contents.remove(content)
        if self._auto_apply:
            self._update_theme_operation(completed=self._theme_operation.get('total',0)-len(self._awaiting_contents))
        if ok and self._awaiting_contents: return
        candidate = self._candidate_config
        prepared = (deepcopy(self._candidate),set(self._staged_fonts))
        self._candidate = None; self._candidate_config = None
        self._awaiting_contents = set()
        self._draft_valid = ok
        if ok:
            self._publish(candidate,prepared)
            self._error = ''
        else:
            if recorder is not None:
                self._trace.finished(recorder.current_request,'failed',reason='candidateRejected')
                self._trace.cleared(generation,outcome='failed')
            self._cancel_activation()
            self._error = message or 'Presentazione non caricabile; aspetto precedente conservato'
        self.candidateChanged.emit()
        if not ok:
            self._staged_fonts = set()
            FontRegistry.update(self._font_owner,self._active_fonts,trace=self._trace)
        self.editorChanged.emit()
        if not ok and self._auto_apply:
            self._fail_theme_operation(message or 'La nuova schermata non è disponibile')

    @Property('QVariantMap', notify=themeOperationChanged)
    def themeOperation(self): return deepcopy(self._theme_operation)

    @Property(bool, notify=editorChanged)
    def dirty(self): return self._draft is not None and self._draft != self._committed

    def _update_theme_operation(self, **values):
        self._theme_operation.update(values)
        self.themeOperationChanged.emit()

    @Slot(str, result=bool)
    def activateTheme(self, identifier):
        if self._auto_apply or self._candidate is not None or self._pending is not None or self._operation_pending:
            return False
        if identifier not in self.catalog.packs:
            self._error='Tema non disponibile'; self.editorChanged.emit(); return False
        if not self.editing: self.beginEdit()
        self._auto_apply=True; self._auto_saved=False; self._theme_timed_out=False
        self._theme_operation={'busy':True,'phase':'preparing','targetId':identifier,
            'targetName':self._theme_metadata(identifier).get('name',identifier),
            'message':'Preparazione delle schermate…','completed':0,'total':0,
            'palette':deepcopy(self._snapshot.get('tokens',{})),
            'motionMode':self._visible.get('motionMode','off')}
        self.themeOperationChanged.emit()
        self._theme_deadline.start()
        if (identifier == self._committed['themeId'] and not self.dirty
                and not self.lifecycle.read().get('lastRecovery')):
            self._finish_theme_operation(True)
            return True
        if not self.selectDraft(identifier):
            self._fail_theme_operation(self._error)
            return False
        if self._candidate:
            self._update_theme_operation(total=len(self._awaiting_contents),completed=0)
        else:
            self._update_theme_operation(phase='presenting',message='Verifica della nuova schermata…')
        QTimer.singleShot(0,self._apply_selected_theme)
        return True

    def _apply_selected_theme(self):
        if not self._auto_apply or self._auto_saved or self._pending is not None:
            return
        if self._candidate is not None or not self._gui_ready or not self.readyToApply:
            return
        self._update_theme_operation(phase='saving',message='Salvataggio delle preferenze…')
        if not self.apply(): self._fail_theme_operation(self._error)

    def _finish_theme_operation(self, ok, message=''):
        self._auto_apply=False; self._auto_saved=False; self._theme_timed_out=False; self._theme_deadline.stop()
        name=self._theme_operation.get('targetName','Tema')
        self._update_theme_operation(busy=False,phase='completed' if ok else 'failed',
            message=name+' attivo' if ok else message)
        self.themeActivationFinished.emit(ok)

    def _fail_theme_operation(self, message):
        self._auto_apply=False; self._auto_saved=False
        if self._pending is None: self.cancel()
        self._status='error'; self._error=message
        self._finish_theme_operation(False,message+' · Tema precedente ripristinato')
        self.editorChanged.emit()

    def _theme_operation_timeout(self):
        if not self._auto_apply: return
        if self._pending is None and not self._auto_saved:
            self._fail_theme_operation('Tempo massimo di attivazione superato')
        else:
            # Never race an in-flight durable write with a second writer. Fresh
            # pulses now withdraw readiness so the external watchdog bounds a
            # hung worker/final frame; a late valid save can still finish safely.
            self._theme_timed_out=True
            self._update_theme_operation(message='Attivazione lenta · verifica di sicurezza in corso…')

    @Slot(str,str,result=bool)
    @trace_operation("recoverVisual")
    def recoverVisual(self, content, message):
        base = self.catalog.resolve('base')
        if self._snapshot['presentations'].get(content) == base['presentations'].get(content): return False
        self._recover_base(message)
        return True

    def _recover_base(self, message):
        if recorder_for(self._trace) is not None: self._trace.recovery()
        self._clear_candidate()
        result=self.lifecycle.recover(message,failed_active=self._activation is None and bool(self._visible.get('bundleRevision')))
        if self._activation or self._visible.get('bundleRevision') or result['recovered']:
            self._activation=None; self._activation_frame=False
            selected=result['selection']
            previous=self._previous_configuration()
            if selected != BASE:
                configuration={**self._committed,'themeId':selected['id'],'bundleRevision':selected,
                    'overrides':self.lifecycle.read()['adaptations']['perRevision'].get(selection_key(selected),{})}
            elif previous and 'bundleRevision' not in previous:
                configuration=previous
            else:
                configuration={'schemaVersion':1,'themeId':'base','overrides':{},'motionMode':'off','paletteMode':self._visible.get('paletteMode','auto')}
        else:
            configuration={'schemaVersion':1,'themeId':'base','overrides':{},'motionMode':'off','paletteMode':self._visible.get('paletteMode','auto')}
        self._committed=configuration; self._draft=None
        self._publish(configuration)
        settings=QSettings('SmartPC','Dashboard')
        settings.setValue('appearance/config',json.dumps(configuration))
        settings.setValue('animationsEnabled',configuration['motionMode']!='off')
        settings.setValue('nightMode',configuration.get('paletteMode','auto')); settings.sync()
        self._status='recovery'; self._error=message
        self.frameStateChanged.emit(); self.editorChanged.emit()

    @Property('QVariantMap',notify=changed)
    def resolvedAppearance(self): return deepcopy(self._snapshot)
    @Property(int,notify=changed)
    def revision(self): return self._revision
    @Property(str,notify=changed)
    def activeThemeId(self): return self._snapshot['themeId']
    @Property(str,notify=editorChanged)
    def savedThemeId(self): return self._committed['themeId']
    @Property(str,notify=editorChanged)
    def status(self): return self._status
    @Property(str,notify=editorChanged)
    def lastError(self): return self._error
    @Property(bool,notify=editorChanged)
    def readyToApply(self): return self._draft is not None and self._candidate is None and self._pending is None and not self._operation_pending and self._draft_valid and (not self._activation or self._activation_frame)
    @Property(bool,notify=editorChanged)
    def editing(self): return self._draft is not None
    @Property('QVariantMap',notify=editorChanged)
    def draft(self): return deepcopy(self._draft or self._committed)
    @Property('QVariantList',notify=editorChanged)
    def themes(self):
        selected=self._draft or self._committed
        return [self._theme_metadata(identifier,selected if identifier==selected['themeId'] else None) for identifier in self.catalog.packs]
    @Property('QVariantMap',notify=editorChanged)
    def selectedTheme(self):
        configuration=self._draft or self._committed
        return self._theme_metadata(configuration['themeId'],configuration)
    @Property('QVariantList',notify=editorChanged)
    def revisions(self):
        identifier=(self._draft or self._committed)['themeId']
        return deepcopy([row for row in getattr(self.catalog,'installed_bundle_revisions',[]) if row['id']==identifier])
    @Property('QStringList',notify=editorChanged)
    def fontFamilies(self): return ['']+QFontDatabase.families()
    @Property('QStringList',notify=editorChanged)
    def catalogErrors(self): return self.catalog.errors

    @Slot(str)
    @trace_operation("setVariant")
    def setVariant(self, variant):
        if variant == self._variant or variant not in ('day','night'): return
        self._variant = variant
        if self._candidate is not None:
            candidate = deepcopy(self._candidate_config)
            self._clear_candidate()
            self._change(candidate)
        else:
            try: self._publish(self._visible)
            except (ThemeError, OSError, ValueError) as error:
                self._recover_base(str(error))

    @Slot()
    @trace_span("service.beginEdit")
    def beginEdit(self):
        if self._pending is not None or self._operation_pending: return
        self._draft = deepcopy(self._committed); self._draft_profiles=deepcopy(self._profiles); self._draft_valid = True; self._status = 'ready'; self._error = ''; self.editorChanged.emit()

    @staticmethod
    def _profile_key(configuration):
        return selection_key(configuration['bundleRevision']) if configuration.get('bundleRevision') else 'schema1:'+configuration['themeId']

    def _remember_draft(self):
        if self._draft is not None and self._draft_profiles is not None:
            self._draft_profiles[self._profile_key(self._draft)]=deepcopy(self._draft['overrides'])

    @Slot(str,result=bool)
    @trace_operation("selectDraft")
    def selectDraft(self, identifier):
        if self._draft is None or self._pending is not None or self._operation_pending: return False
        candidate = deepcopy(self._draft); candidate['themeId'] = identifier
        pin=getattr(self.catalog,'bundle_revisions',{}).get(identifier)
        if pin: candidate['bundleRevision']=deepcopy(pin)
        else: candidate.pop('bundleRevision',None)
        if identifier != self._draft['themeId']:
            self._remember_draft()
            candidate['overrides']=deepcopy((self._draft_profiles or {}).get(self._profile_key(candidate),{}))
            scale=self._draft.get('overrides',{}).get('tokens',{}).get('typography.textScale')
            if scale is not None: candidate['overrides'].setdefault('tokens',{})['typography.textScale']=scale
        return self._change(candidate)

    @Slot(str,'QVariant',result=bool)
    @trace_operation("setToken")
    def setToken(self, path, value):
        if self._draft is None or self._pending is not None or self._operation_pending: return False
        if path=='typography.textScale' and not self._guard_adjustment('textScale'): return False
        value=plain_qml_value(value)
        candidate = deepcopy(self._draft); candidate['overrides'].setdefault('tokens',{})[path] = value
        return self._change(candidate)

    @Slot('QVariantMap',result=bool)
    @trace_operation("setTokens")
    def setTokens(self, values):
        if self._draft is None or self._pending is not None or self._operation_pending: return False
        if 'typography.textScale' in values and not self._guard_adjustment('textScale'): return False
        values=plain_qml_value(values)
        candidate = deepcopy(self._draft)
        candidate['overrides'].setdefault('tokens',{}).update(values)
        return self._change(candidate)

    @Slot(str,result=bool)
    @trace_span("service.transferPack")
    def transferPack(self, operation):
        if operation not in ('import','export') or self._operation_pending or self._pending is not None or self._candidate is not None: return False
        configuration = deepcopy(self._draft if self._draft is not None else self._committed)
        catalog = make_catalog(self.store,self._root,selected=configuration.get('bundleRevision'),trace=self._trace)
        self._operation_pending = True; self._status = 'working'; self._error = ''; self.editorChanged.emit()
        QThreadPool.globalInstance().start(PackJob(operation,self.store,catalog,configuration,self._pack_result))
        return True

    @Slot(bool,str)
    def _pack_finished(self, ok, message):
        self._operation_pending = False; self._status = 'ready' if ok else 'error'
        if ok: self.reloadCatalog()
        self._error = message; self.editorChanged.emit(); self.transferFinished.emit(ok,message)

    @Slot(result=bool)
    @trace_span("service.reloadCatalog")
    def reloadCatalog(self):
        try:
            candidate = make_catalog(self.store,self._root,selected=(self._draft or self._committed).get('bundleRevision'),trace=self._trace)
            current = self._draft if self._draft is not None else self._committed
            candidate.resolve(current['themeId'],current['overrides'],self._variant,current['motionMode'])
            self.catalog = candidate; self._resolved_cache.clear(); self._error = '; '.join(candidate.errors)
            self.editorChanged.emit(); return True
        except (ThemeError,OSError) as error:
            self._error = str(error); self.editorChanged.emit(); return False

    @Slot(str,'QVariant',result=bool)
    @trace_operation("setSection")
    def setSection(self, section, value):
        if self._draft is None or self._pending is not None or self._operation_pending: return False
        if section=='paletteMode' and not self._guard_adjustment('paletteMode'): return False
        value=plain_qml_value(value)
        candidate = deepcopy(self._draft)
        if section in ('motionMode','paletteMode'): candidate[section] = value
        elif section in ('presentations','motion','scene','iconOverrides','iconSetId'): candidate['overrides'][section] = value
        else: return False
        return self._change(candidate)

    @Slot(result=bool)
    @trace_operation("resetNotifications")
    def resetNotifications(self):
        if self._draft is None or self._pending is not None or self._operation_pending: return False
        candidate = deepcopy(self._draft)
        for section, prefix in (('tokens','notifications.'), ('presentations','alerts.'), ('motion','banner.small.'), ('motion','banner.large.'), ('motion','alerts.')):
            values = candidate['overrides'].get(section, {})
            candidate['overrides'][section] = {key:value for key,value in values.items() if not key.startswith(prefix)}
        return self._change(candidate)

    @trace_span("service.change")
    def _change(self, candidate):
        try:
            candidate=self._normalize_adjustments(deepcopy(candidate))
            self._validate_config(candidate)
            resolved, needed = self._resolve(candidate)
            contents = self._prepared_contents | ({self._active_content} if self._active_content else set())
            def identity(snapshot,content):
                identifier=snapshot['presentations'].get(content)
                return snapshot['presentationRegistry'].get(identifier,{}).get('rendererKey',identifier)
            contents |= {content for content in ('shell.main', 'scene.main') if content in resolved['presentations'] and (content != 'scene.main' or resolved['scene']['enabled'])}
            # An optional shell/scene can disappear when returning to Base. It
            # must be retired after publish, not loaded as an undefined renderer.
            changed = {content for content in contents if content in resolved['presentations']
                       and identity(resolved,content) != identity(self._snapshot,content)}
            if candidate.get('bundleRevision') or self._visible.get('bundleRevision'):
                self._begin_activation(candidate)
            self._draft = candidate
            if changed:
                self._draft_valid = False
                self._generation += 1
                resolved.update(revision=self._revision+1, generation=self._generation, requiredContents=sorted(changed), paletteMode=candidate.get('paletteMode','auto'))
                if self._candidate is not None and recorder_for(self._trace) is not None:
                    self._trace.cleared(self._candidate['generation'],outcome='superseded')
                self._candidate = resolved; self._candidate_config = deepcopy(candidate)
                self._awaiting_contents = set(changed)
                if self._auto_apply: self._update_theme_operation(total=len(changed),completed=0)
                # Fonts needed by both current and staged visuals remain registered until commit/cancel.
                self._staged_fonts = needed
                FontRegistry.update(self._font_owner,needed | self._active_fonts,trace=self._trace)
                if recorder_for(self._trace) is not None: self._trace.candidate(self._generation)
                self._error = ''; self.candidateChanged.emit(); self.editorChanged.emit()
            else:
                self._draft_valid = True
                self._clear_candidate(needed); self._publish(candidate,(resolved,needed))
                self._error = ''; self.editorChanged.emit()
            return True
        except (ThemeError,OSError,ValueError,TypeError) as error:
            FontRegistry.update(self._font_owner,self._active_fonts | self._staged_fonts,trace=self._trace)
            self._error = str(error); self.editorChanged.emit(); return False

    @Slot(result=bool)
    @trace_operation("preview")
    def preview(self):
        if self._draft is None or self._pending is not None or self._operation_pending: return False
        return self._change(deepcopy(self._draft))

    @Slot(result=bool)
    @trace_operation("cancel")
    def cancel(self):
        if self._pending is not None: return False
        if self._auto_apply:
            self._finish_theme_operation(False,'Cambio annullato · Tema precedente conservato')
        # Shutdown also calls cancel. With no preview there is nothing to
        # republish: creating loaders while the Qt event loop exits is unsafe.
        if self._draft is None and self._candidate is None and self._activation is None:
            return True
        self._clear_candidate(trace_outcome='cancelled')
        self._cancel_activation()
        self._draft = None; self._draft_profiles=None
        try: self._publish(self._committed)
        except (ThemeError, OSError, ValueError) as error:
            self._recover_base(str(error)); return True
        self._error = ''; self.editorChanged.emit(); return True

    @Slot(result=bool)
    @trace_operation("resetDraft")
    def resetDraft(self):
        if self._pending is not None or self._operation_pending: return False
        if self._draft is None: self.beginEdit()
        return self._change({'schemaVersion':1,'themeId':'base','overrides':{},'motionMode':'normal','paletteMode':'auto'})

    @Slot(result=bool)
    @trace_operation("apply")
    def apply(self):
        if self._draft is None or self._pending is not None or self._candidate is not None or not self._draft_valid or self._operation_pending: return False
        if self._activation and not self._activation_frame:
            self._error='Attendere il primo frame coerente del tema'; self.editorChanged.emit(); return False
        try:
            self._validate_config(self._draft)
        except (ThemeError,OSError,ValueError,TypeError) as error:
            self._error = str(error); self.editorChanged.emit(); return False
        if self._visible != self._draft:
            if not self._change(deepcopy(self._draft)) or self._candidate is not None: return False
        # Reconstructing a preview after a save failure starts a new activation.
        # Its frame acknowledgment cannot be inherited from the old preview.
        if self._activation and not self._activation_frame:
            self._error='Attendere il primo frame coerente del tema'; self.editorChanged.emit(); return False
        self._remember_draft()
        self._pending_profiles=deepcopy(self._draft_profiles)
        self._save_frame_deadline=None
        self._pending = deepcopy(self._draft); self._status = 'saving'; self._error = ''; self.editorChanged.emit()
        recorder=recorder_for(self._trace)
        self._save_trace_request=recorder.current_request if recorder is not None else None
        if recorder is not None: recorder.record('save.queued')
        QThreadPool.globalInstance().start(SaveJob(self._pending,self._save_result,profiles=self._pending_profiles,trace=recorder,request_id=self._save_trace_request))
        return True

    @Slot(bool,str)
    def _saved(self, ok, message):
        if self._pending is None: return
        # A provider refresh can briefly withdraw coherence while the settings
        # worker is finishing. Wait for a fresh real frame rather than fail a
        # valid apply depending on the heartbeat/callback ordering. The bounded
        # deadline retains the existing journal rollback on lost readiness.
        if ok and self._activation and not self._activation_frame:
            if self._save_frame_deadline is None: self._save_frame_deadline=time.monotonic()+3
            if time.monotonic()<self._save_frame_deadline:
                QTimer.singleShot(25,lambda:self._saved(ok,message))
                return
        self._save_frame_deadline=None
        recorder=recorder_for(self._trace)
        request=self._save_trace_request
        if recorder is not None:
            with recorder.scope(request), recorder.span('save.callback'):
                ok=self._saved_state(ok,message)
                self._trace.finished(request,'noVisualChange' if ok else 'failed',persisted=ok)
        else:
            self._saved_state(ok,message)
        self._save_trace_request=None

    def _saved_state(self, ok, message):
        if ok:
            try:
                if not self._activation and self.lifecycle.read().get('lastRecovery'):
                    self._activation=self.lifecycle.begin(BASE,self._pending['overrides'])
                    self.lifecycle.mark_ready(self._activation['ticket'])
                    self._activation_frame=self._gui_ready
                if self._activation:
                    self.lifecycle.commit(self._activation['ticket'],{'coherent':self._activation_frame,'presented':self._activation_frame,'key':selection_key(self._pending.get('bundleRevision',BASE))})
                    self._activation=None; self._activation_frame=False
            except (ThemeError,OSError) as error:
                ok=False; message=str(error)
                # Qt settings succeeded but journal failed: restore appearance preference only.
                settings=QSettings('SmartPC','Dashboard'); settings.setValue('appearance/config',json.dumps(self._committed)); settings.setValue('animationsEnabled',self._committed['motionMode']!='off'); settings.setValue('nightMode',self._committed.get('paletteMode','auto')); settings.setValue('appearance/themeOverrides',json.dumps(self._profiles)); settings.sync()
        if ok:
            self._committed = self._pending; self._draft = None
            if self._pending_profiles is not None: self._profiles=self._pending_profiles
            self._draft_profiles=None
        else:
            try:
                self._cancel_activation()
            except (ThemeError,OSError) as error:
                # A failed durable cancellation remains in the journal for boot
                # recovery. Finish the asynchronous action and restore the GUI
                # instead of leaving the editor permanently in "saving".
                self._activation=None; self._activation_frame=False
                message += '; '+str(error)
            self._publish(self._committed)
        self._pending = None; self._pending_profiles=None; self._status = 'ready' if ok else 'error'; self._error = message
        self.editorChanged.emit(); self.saveFinished.emit(ok)
        if self._auto_apply:
            if ok:
                self._auto_saved=True; self._gui_ready=False
                self._update_theme_operation(phase='finishing',message='Verifica finale della schermata…')
                self.frameStateChanged.emit()
            else:
                self._finish_theme_operation(False,message+' · Tema precedente ripristinato')
        return ok
