"""Application-owned theme state. Only discrete changes cross Python/QML."""
from copy import deepcopy
from collections import OrderedDict
import json
import os
from pathlib import Path

from PySide6.QtCore import QObject, Property, QRunnable, QSettings, QStandardPaths, QThreadPool, Signal, Slot
from PySide6.QtGui import QFontDatabase, QGuiApplication, QImageReader
from theme_core import ThemeCatalog, ThemeError


class SaveResult(QObject):
    finished = Signal(bool, str)


class SaveJob(QRunnable):
    def __init__(self, configuration, result):
        super().__init__()
        self.configuration = deepcopy(configuration)
        self.result = result

    def run(self):
        settings = QSettings('SmartPC', 'Dashboard')
        values={'appearance/config':json.dumps(self.configuration,ensure_ascii=False,sort_keys=True),
                'animationsEnabled':self.configuration['motionMode']!='off',
                'nightMode':self.configuration.get('paletteMode','auto')}
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
                    if not folder.is_dir() or not (folder/'theme.json').is_file(): continue
                    identifier=json.loads((folder/'theme.json').read_text())['id']
                    if identifier in self.catalog.packs: continue
                    imported.append(import_pack(folder,self.store,root=self.catalog.root))
                message='Importati: '+', '.join(imported) if imported else 'Nessun nuovo pacchetto in '+str(inbox)
            else:
                stamp=datetime.now().strftime('%Y%m%d-%H%M%S-%f')
                identifier='personal.export.'+stamp.replace('-','')
                output=self.store.parent/'theme-exports'/identifier
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
    def acquire(cls, assets, families):
        needed = set()
        result = {}
        for value in families:
            if not value.startswith('asset:'): continue
            identifier = value[6:]
            asset = next((a for a in assets if a['id'] == identifier and a['type'] == 'font'), None)
            if not asset: raise ThemeError('font.'+identifier, 'risorsa font non disponibile')
            key = asset['sha256']; needed.add(key)
            if key not in cls.entries:
                number = QFontDatabase.addApplicationFont(asset['file'])
                names = QFontDatabase.applicationFontFamilies(number) if number >= 0 else []
                if not names: raise ThemeError('font.'+identifier, 'font non caricabile')
                cls.entries[key] = {'id':number, 'family':names[0], 'owners':set(), 'touched':0}
            cls.clock += 1; cls.entries[key]['touched'] = cls.clock
            result[value] = cls.entries[key]['family']
        return needed, result

    @classmethod
    def update(cls, owner, needed):
        for key, entry in list(cls.entries.items()):
            if key in needed: entry['owners'].add(owner)
            else: entry['owners'].discard(owner)
        inactive=sorted((key for key,entry in cls.entries.items() if not entry['owners']), key=lambda key:cls.entries[key]['touched'])
        for key in inactive[:-cls.idle_capacity]:
            QFontDatabase.removeApplicationFont(cls.entries[key]['id']); del cls.entries[key]


class ThemeService(QObject):
    changed = Signal()
    editorChanged = Signal()
    saveFinished = Signal(bool)
    candidateChanged = Signal()

    def __init__(self, parent=None, *, store=None, root=None):
        super().__init__(parent)
        location = store or os.environ.get('SMARTPC_THEME_STORE') or str(Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))/'themes')
        self.store = Path(location)
        self.catalog = ThemeCatalog(self.store, **({'root':root} if root else {}))
        settings = QSettings('SmartPC', 'Dashboard')
        legacy = str(settings.value('animationsEnabled','true')).lower() not in ('false','0')
        legacy_palette = settings.value('nightMode','auto')
        if legacy_palette not in ('auto','day','night'): legacy_palette = 'auto'
        self._image_sizes = {}; self._resolved_cache = OrderedDict(); self._operation_pending = False
        self._committed = {'schemaVersion':1, 'themeId':'base', 'overrides':{}, 'motionMode':'normal' if legacy else 'off', 'paletteMode':legacy_palette}
        self._variant = 'day'; self._revision = 0; self._snapshot = {}; self._draft = None
        self._error = ''; self._status = 'ready'; self._pending = None
        self._candidate = None; self._candidate_config = None; self._draft_valid = True; self._generation = 0; self._active_content = ''; self._staged_fonts = set()
        self._font_owner = id(self)
        self._save_result = SaveResult(self)
        self._save_result.finished.connect(self._saved)
        self._pack_result = SaveResult(self)
        self._pack_result.finished.connect(self._pack_finished)
        saved = settings.value('appearance/config')
        if saved:
            try:
                config = json.loads(saved)
                if not isinstance(config,dict): raise ThemeError('configuration','oggetto richiesto')
                config.setdefault('paletteMode',settings.value('nightMode','auto'))
                self._validate_config(config)
                self._committed = config
            except (ValueError, TypeError, ThemeError) as error:
                self._error = 'Preferenze recuperate con Base: '+str(error); self._status = 'recovery'
        try:
            self._publish(self._committed)
        except (ThemeError,ValueError,OSError) as error:
            self._error = 'Risorse recuperate con Base: '+str(error); self._status = 'recovery'
            self._committed = {'schemaVersion':1,'themeId':'base','overrides':{},'motionMode':'normal','paletteMode':'auto'}
            self._publish(self._committed)
        self.destroyed.connect(lambda: FontRegistry.update(self._font_owner, set()))

    def _data(self, configuration, variant):
        key=(json.dumps(configuration,sort_keys=True,separators=(',',':')),variant)
        cached=self._resolved_cache.get(key)
        if cached is not None:
            result,stamps=cached
            try:
                unchanged=all((Path(path).stat().st_size,Path(path).stat().st_mtime_ns)==stamp for path,stamp in stamps.items())
            except OSError: unchanged=False
            if unchanged:
                self._resolved_cache.move_to_end(key)
                return deepcopy(result)
            self._resolved_cache.pop(key,None)
        result=self.catalog.resolve(configuration['themeId'],configuration['overrides'],variant,configuration['motionMode'])
        stamps={a['file']:(Path(a['file']).stat().st_size,Path(a['file']).stat().st_mtime_ns) for a in result['assets']}
        self._resolved_cache[key]=(deepcopy(result),stamps)
        while len(self._resolved_cache)>32:self._resolved_cache.popitem(last=False)
        return result

    def _validate_config(self, configuration):
        if not isinstance(configuration,dict) or type(configuration.get('schemaVersion')) is not int or configuration.get('schemaVersion') != 1 or set(configuration)-{'schemaVersion','themeId','overrides','motionMode','paletteMode'}:
            raise ThemeError('configuration','formato non supportato')
        if not all(key in configuration for key in ('themeId','overrides','motionMode')): raise ThemeError('configuration','campi obbligatori mancanti')
        if configuration.get('paletteMode','auto') not in ('auto','day','night'): raise ThemeError('paletteMode','modalità non valida')
        if not isinstance(configuration.get('overrides'),dict): raise ThemeError('overrides','oggetto richiesto')
        for variant in ('day','night'):
            self._data(configuration,variant)

    def _resolve(self, configuration):
        result = self._data(configuration,self._variant)
        image_bytes = 0
        for asset in result['assets']:
            if asset['type'] != 'image': continue
            size = self._image_sizes.get(asset['sha256'])
            if size is None:
                reader = QImageReader(asset['file'])
                dimensions = reader.size()
                if not reader.canRead() or not dimensions.isValid(): raise ThemeError(asset['id'],'immagine non decodificabile')
                size = dimensions.width()*dimensions.height()*4
                self._image_sizes[asset['sha256']] = size
            image_bytes += size
        if image_bytes > 24*1024*1024: raise ThemeError('assets.images','budget texture per tema superato')
        families = [result['tokens'][key] for key in ('typography.uiFamily','typography.numbersFamily','typography.displayFamily')]
        families += [v['family'] for v in result['icons'].values() if isinstance(v,dict) and v.get('backend')=='glyph']
        needed, replacements = FontRegistry.acquire(result['assets'],families)
        for key in ('typography.uiFamily','typography.numbersFamily','typography.displayFamily'):
            value = result['tokens'][key]
            if not value:
                result['tokens'][key] = QGuiApplication.font().family()
            else:
                if value not in replacements and value not in QFontDatabase.families(): raise ThemeError(key,'famiglia font non disponibile')
                result['tokens'][key] = replacements.get(value,value)
        for icon in result['icons'].values():
            if isinstance(icon,dict) and icon.get('backend')=='glyph':
                if icon['family'] not in replacements and icon['family'] not in QFontDatabase.families(): raise ThemeError('icon.family','famiglia font non disponibile')
                icon['family'] = replacements.get(icon['family'],icon['family'])
                font = __import__('PySide6.QtGui',fromlist=['QRawFont','QFont'])
                raw = font.QRawFont.fromFont(font.QFont(icon['family']))
                if not raw.supportsCharacter(ord(icon['glyph'])): raise ThemeError('icon.glyph','glifo mancante nel font')
        return result, needed

    def _publish(self, configuration, prepared=None):
        result, needed = prepared if prepared is not None else self._resolve(configuration)
        self._revision += 1
        result['revision'] = self._revision
        result['paletteMode'] = configuration.get('paletteMode','auto')
        self._visible = deepcopy(configuration)
        self._snapshot = result
        self._active_fonts = needed; self._staged_fonts = set()
        FontRegistry.update(self._font_owner, needed)
        self.changed.emit()

    @Property('QVariantMap',notify=candidateChanged)
    def candidateAppearance(self): return deepcopy(self._candidate or {})

    @Slot(str)
    def setActiveContent(self, content):
        self._active_content = content
        if self._candidate is not None:
            candidate = deepcopy(self._candidate_config)
            self._clear_candidate()
            self._change(candidate)

    def _clear_candidate(self, retain_fonts=None):
        self._candidate = None; self._candidate_config = None; self._generation += 1; self._staged_fonts = set()
        FontRegistry.update(self._font_owner,self._active_fonts | (retain_fonts or set()))
        self.candidateChanged.emit()

    @Slot(int,bool,str)
    def acceptCandidate(self, generation, ok, message):
        if self._candidate is None or generation != self._candidate['generation']: return
        candidate = self._candidate_config
        prepared = (deepcopy(self._candidate),set(self._staged_fonts))
        self._candidate = None; self._candidate_config = None
        self._draft_valid = ok
        if ok:
            self._publish(candidate,prepared)
            self._error = ''
        else:
            self._error = message or 'Presentazione non caricabile; aspetto precedente conservato'
        self.candidateChanged.emit(); self.editorChanged.emit()

    @Slot(str,str,result=bool)
    def recoverVisual(self, content, message):
        base = self.catalog.resolve('base')
        if self._snapshot['presentations'].get(content) == base['presentations'].get(content): return False
        self._clear_candidate()
        self._committed = {'schemaVersion':1,'themeId':'base','overrides':{},'motionMode':'off','paletteMode':self._visible.get('paletteMode','auto')}
        self._draft = None; self._publish(self._committed)
        self._status = 'recovery'; self._error = message
        self.editorChanged.emit(); return True

    @Property('QVariantMap',notify=changed)
    def resolvedAppearance(self): return deepcopy(self._snapshot)
    @Property(int,notify=changed)
    def revision(self): return self._revision
    @Property(str,notify=changed)
    def activeThemeId(self): return self._snapshot['themeId']
    @Property(str,notify=editorChanged)
    def status(self): return self._status
    @Property(str,notify=editorChanged)
    def lastError(self): return self._error
    @Property(bool,notify=editorChanged)
    def readyToApply(self): return self._draft is not None and self._candidate is None and self._pending is None and not self._operation_pending and self._draft_valid
    @Property(bool,notify=editorChanged)
    def editing(self): return self._draft is not None
    @Property('QVariantMap',notify=editorChanged)
    def draft(self): return deepcopy(self._draft or self._committed)
    @Property('QVariantList',notify=editorChanged)
    def themes(self): return [{'id':p['id'],'name':p['name'],'version':p['version']} for p in self.catalog.packs.values()]
    @Property('QStringList',notify=editorChanged)
    def fontFamilies(self): return ['']+QFontDatabase.families()
    @Property('QStringList',notify=editorChanged)
    def catalogErrors(self): return self.catalog.errors

    @Slot(str)
    def setVariant(self, variant):
        if variant == self._variant or variant not in ('day','night'): return
        self._variant = variant
        self._publish(self._visible)

    @Slot()
    def beginEdit(self):
        if self._pending is not None or self._operation_pending: return
        self._draft = deepcopy(self._committed); self._draft_valid = True; self._status = 'ready'; self._error = ''; self.editorChanged.emit()

    @Slot(str,result=bool)
    def selectDraft(self, identifier):
        if self._draft is None or self._pending is not None or self._operation_pending: return False
        candidate = deepcopy(self._draft); candidate['themeId'] = identifier
        return self._change(candidate)

    @Slot(str,'QVariant',result=bool)
    def setToken(self, path, value):
        if self._draft is None or self._pending is not None or self._operation_pending: return False
        candidate = deepcopy(self._draft); candidate['overrides'].setdefault('tokens',{})[path] = value
        return self._change(candidate)

    @Slot('QVariantMap',result=bool)
    def setTokens(self, values):
        if self._draft is None or self._pending is not None or self._operation_pending: return False
        candidate = deepcopy(self._draft)
        candidate['overrides'].setdefault('tokens',{}).update(values)
        return self._change(candidate)

    @Slot(str,result=bool)
    def transferPack(self, operation):
        if operation not in ('import','export') or self._operation_pending or self._pending is not None or self._candidate is not None: return False
        configuration = deepcopy(self._draft if self._draft is not None else self._committed)
        catalog = ThemeCatalog(self.store,root=self.catalog.root)
        self._operation_pending = True; self._status = 'working'; self._error = ''; self.editorChanged.emit()
        QThreadPool.globalInstance().start(PackJob(operation,self.store,catalog,configuration,self._pack_result))
        return True

    @Slot(bool,str)
    def _pack_finished(self, ok, message):
        self._operation_pending = False; self._status = 'ready' if ok else 'error'
        if ok: self.reloadCatalog()
        self._error = message; self.editorChanged.emit()

    @Slot(result=bool)
    def reloadCatalog(self):
        try:
            candidate = ThemeCatalog(self.store,root=self.catalog.root)
            current = self._draft if self._draft is not None else self._committed
            candidate.resolve(current['themeId'],current['overrides'],self._variant,current['motionMode'])
            self.catalog = candidate; self._resolved_cache.clear(); self._error = '; '.join(candidate.errors)
            self.editorChanged.emit(); return True
        except (ThemeError,OSError) as error:
            self._error = str(error); self.editorChanged.emit(); return False

    @Slot(str,'QVariant',result=bool)
    def setSection(self, section, value):
        if self._draft is None or self._pending is not None or self._operation_pending: return False
        candidate = deepcopy(self._draft)
        if section in ('motionMode','paletteMode'): candidate[section] = value
        elif section in ('presentations','motion','scene','iconOverrides','iconSetId'): candidate['overrides'][section] = value
        else: return False
        return self._change(candidate)

    def _change(self, candidate):
        try:
            self._validate_config(candidate)
            resolved, needed = self._resolve(candidate)
            content = self._active_content
            self._draft = candidate
            if content and resolved['presentations'].get(content) != self._snapshot['presentations'].get(content):
                self._draft_valid = False
                self._generation += 1
                resolved.update(revision=self._revision+1, generation=self._generation, paletteMode=candidate.get('paletteMode','auto'))
                self._candidate = resolved; self._candidate_config = deepcopy(candidate)
                # Fonts needed by both current and staged visuals remain registered until commit/cancel.
                self._staged_fonts = needed
                FontRegistry.update(self._font_owner,needed | self._active_fonts)
                self._error = ''; self.candidateChanged.emit(); self.editorChanged.emit()
            else:
                self._draft_valid = True
                self._clear_candidate(needed); self._publish(candidate,(resolved,needed))
                self._error = ''; self.editorChanged.emit()
            return True
        except (ThemeError,OSError,ValueError,TypeError) as error:
            FontRegistry.update(self._font_owner,self._active_fonts | self._staged_fonts)
            self._error = str(error); self.editorChanged.emit(); return False

    @Slot(result=bool)
    def preview(self):
        if self._draft is None: return False
        return self._change(deepcopy(self._draft))

    @Slot()
    def cancel(self):
        if self._pending is not None: return
        self._clear_candidate()
        self._draft = None; self._publish(self._committed); self._error = ''; self.editorChanged.emit()

    @Slot(result=bool)
    def resetDraft(self):
        if self._draft is None: self.beginEdit()
        return self._change({'schemaVersion':1,'themeId':'base','overrides':{},'motionMode':'normal','paletteMode':'auto'})

    @Slot(result=bool)
    def apply(self):
        if self._draft is None or self._pending is not None or self._candidate is not None or not self._draft_valid or self._operation_pending: return False
        try:
            self._validate_config(self._draft)
        except (ThemeError,OSError,ValueError,TypeError) as error:
            self._error = str(error); self.editorChanged.emit(); return False
        if self._visible != self._draft:
            if not self._change(deepcopy(self._draft)) or self._candidate is not None: return False
        self._pending = deepcopy(self._draft); self._status = 'saving'; self._error = ''; self.editorChanged.emit()
        QThreadPool.globalInstance().start(SaveJob(self._pending,self._save_result))
        return True

    @Slot(bool,str)
    def _saved(self, ok, message):
        if ok:
            self._committed = self._pending; self._draft = None
        else:
            self._publish(self._committed)
        self._pending = None; self._status = 'ready' if ok else 'error'; self._error = message
        self.editorChanged.emit(); self.saveFinished.emit(ok)
