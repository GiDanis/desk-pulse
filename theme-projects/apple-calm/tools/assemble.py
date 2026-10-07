"""Rebuild the registry/manifests and the small typed renderer entry points."""
import json
import hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
B=ROOT/'bundle'; Q=B/'qml'
PREP=ROOT/'tools/blueprint'
def put(name,text): (Q/name).write_text('pragma ComponentBehavior: Bound\n'+text.strip()+'\n')
def entry(name,base,kind,body):
 put(name,f'''import QtQuick
import SmartPC.ThemeApi 2.0
import "Format.js" as Format

{base} {{
    id: root
    required property {kind} context
    ctx: context
    {body}
}}''')
entry('HomeNow.qml','ClockPage','PageContext','')
entry('HomeClock.qml','ClockFocusPage','PageContext','')
entry('HomeDay.qml','DayPage','PageContext','')
entry('WeatherNow.qml','CurrentWeatherPage','PageContext','')
entry('WeatherForecast.qml','ForecastPage','PageContext','')
entry('AccountUsage.qml','AccountPage','PageContext','')
entry('Menu.qml','Panel','MenuContext','''title: "Menu"
    subtitle: "Scegli una funzione"
    rows: { context.dataRevision; return Format.list(context.rows).map(x => ({id:x.id,title:x.title,detail:x.detail,value:"",icon:Format.settingIcon(x.id),enabled:x.enabled,actionId:x.actionId || "menu.activate",targetId:x.targetId || x.id})) }
    rowAction: "menu.activate"''')
entry('DeviceInfo.qml','Panel','InfoContext','''title: "Informazioni dispositivo"
    tabs: context.tabs
    rows: { context.dataRevision; return Format.info(context.rows) }
    footer: context.updatedAt === null ? "Informazioni non disponibili" : "Rilevato " + Format.stamp(context.updatedAt)''')
entry('Settings.qml','Panel','SettingsContext','''title: Format.settingTitle(context.sectionId)
    subtitle: context.description
    rows: { context.dataRevision; return Format.settings(context.rows) }
    footer: [context.feedback,context.operation.message,context.draft && context.draft.editing ? "Anteprima · " + context.draft.themeId : ""].filter(Boolean).join(" · ")
    rowAction: "settings.activate"''')
entry('SportOverview.qml','Panel','PageContext','''pageMode: true
    title: context.sport ? context.sport.competitionName || "Calcio" : "Calcio"
    subtitle: context.selection.tabId || "Partite"
    source: context.sport ? context.sport.source : null
    rows: { context.dataRevision; return context.sport ? context.selection.tabId === "CLASSIFICA" ? Format.standings(context.sport.standings) : Format.matches(context.sport.matches, context.selection.tabId) : [] }
    emptyText: "Nessuna partita disponibile in questa vista"
    rowAction: "details.open"''')
entry('TeamOverview.qml','Panel','PageContext','''pageMode: true
    title: context.team ? context.team.identity.name || "La tua squadra" : "La tua squadra"
    subtitle: context.team ? context.team.recordText : "Scegli una squadra nelle impostazioni"
    source: context.team ? context.team.source : null
    rows: { context.dataRevision; return context.team ? Format.matches(context.team.fixtures) : [] }
    emptyText: "Dati della squadra non disponibili"
    rowAction: "details.open"''')
entry('RacingOverview.qml','Panel','PageContext','''pageMode: true
    title: context.racing && context.racing.kind === "motogp" ? "MotoGP" : "Formula 1"
    subtitle: context.selection.tabId || "Calendario"
    source: context.racing ? context.racing.source : null
    rows: { context.dataRevision; if (!context.racing) return []; if (context.selection.tabId === "CLASSIFICA") return Format.standings(context.racing.standings); if (context.selection.tabId === "IN CORSO") return Format.timing(context.racing.live.rows); return Format.events(Format.list(context.racing.events).filter(x => context.selection.tabId === "RISULTATI" ? x.endsAt !== null && x.endsAt < context.clock.epoch : x.endsAt === null || x.endsAt >= context.clock.epoch)) }
    emptyText: "Nessun dato disponibile in questa vista"
    rowAction: "details.open"''')
for name,title,rows in [('SportFixtures.qml','Partite','Format.matches(context.matches)'),('SportStandings.qml','Classifica','Format.standings(context.standings)')]:
 entry(name,'Panel','SportListContext',f'''title: "{title}"
    subtitle: context.selectedRoundId ? "Giornata " + context.selectedRoundId : "Calcio"
    source: context.source
    rows: {{ context.dataRevision; return {rows} }}
    rowAction: "details.open"''')
entry('TeamDetail.qml','Panel','TeamContext','''title: context.team ? context.team.identity.name || "Squadra" : "Squadra"
    tabs: context.tabs
    source: context.team ? context.team.source : null
    rows: { context.dataRevision; return Format.teamRows(context) }
    footer: context.serieAOnly ? "Calendario Serie A" : "Calendario completo"
    rowAction: "details.open"''')
entry('TeamPicker.qml','Panel','TeamPickerContext','''title: "Scegli squadra"
    subtitle: "La selezione si salva con 5"
    rows: { context.dataRevision; return Format.list(context.teams).map(x => Format.row(x.id,x.name,x.id === context.savedTeamId ? "Squadra preferita" : "", "", "football")) }
    rowAction: "details.open"''')
for name,title,id in [('RacingCalendar.qml','Calendario gare','racing.calendar'),('RacingEvent.qml','Gran premio','racing.event.detail'),('RacingSession.qml','Sessione','racing.session.detail'),('RacingStandings.qml','Classifica motorsport','racing.standings'),('RacingLive.qml','Timing','racing.live')]:
 extra='context.event ? context.event.name : "Gran premio"' if 'Event' in name else 'context.session ? context.session.name : "Sessione"' if 'Session' in name else json.dumps(title)
 entry(name,'Panel','RacingContext',f'''title: {extra}
    tabs: context.tabs
    source: context.contentId === "racing.live" && context.racing ? context.racing.live.source : context.source
    rows: {{ context.dataRevision; return Format.racingRows(context) }}
    footer: context.detailOperation.status === "pending" ? "Caricamento dettagli" : context.racing ? [context.racing.detailError,context.racing.partialError].filter(Boolean).join(" · ") : ""
    rowAction: "details.open"''')
entry('DriverDetail.qml','Panel','DriverContext','''title: context.driver ? context.driver.name || "Pilota" : "Pilota"
    tabs: context.tabs
    source: context.source
    rows: { context.dataRevision; return Format.driverRows(context) }
    footer: context.detailOperation.status === "pending" ? "Caricamento dettagli" : context.detailOperation.message''')
for name,mode in [('NoticeBadge.qml','badge'),('NoticeSmall.qml','small'),('NoticeLarge.qml','large'),('NoticeUrgent.qml','urgent'),('NoticeInbox.qml','inbox'),('NoticeDetail.qml','detail')]:
 entry(name,'Notice','NotificationContext',f'mode: "{mode}"')
registry=json.loads((PREP/'visual-registry.planned.json').read_text())
registry['presentations'][-1]['name']='Impostazioni'
(B/'visual-registry.json').write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
theme=json.loads((PREP/'theme.planned.json').read_text())
for identifier,file in [('ui','Cantarell-VF.otf'),('numbers','LiberationSans-Regular.ttf'),('display','LiberationSans-Bold.ttf')]:
 path='fonts/'+file
 theme['assets'].append({'id':identifier,'path':path,'type':'font','sha256':hashlib.sha256((B/path).read_bytes()).hexdigest()})
theme['tokens'].update({'typography.uiFamily':'asset:ui','typography.numbersFamily':'asset:numbers','typography.displayFamily':'asset:display'})
for mode in ['small','large','urgent','badge','inbox','detail']:
 theme['tokens'].update({'notifications.'+mode+'.radius':24,'notifications.'+mode+'.titleFamily':'asset:ui','notifications.'+mode+'.bodyFamily':'asset:ui','notifications.'+mode+'.sourceFamily':'asset:ui','notifications.'+mode+'.guideFamily':'asset:ui'})
 if mode in ['small','large','inbox']:
  theme['tokens'].update({'notifications.'+mode+'.width':896,'notifications.'+mode+'.insetX':32})
for event in ['banner.small.enter','banner.small.exit','banner.large.enter','banner.large.exit','alerts.badge.enter','alerts.badge.exit','alerts.inbox.enter','alerts.inbox.exit','alerts.detail.enter','alerts.detail.exit']:
 theme['motion'][event]={'recipe':'builtin.fade','durationMs':120,'distancePx':0,'easing':'outCubic'}
theme['tokens'].update({'notifications.small.showIcon':True,'notifications.large.showIcon':True,'notifications.urgent.showIcon':True})
theme['tokens'].update({'notifications.small.height' :124,'notifications.small.insetY':88,'notifications.large.height':360,'notifications.large.insetY':80,'notifications.inbox.height':560,'notifications.inbox.insetY':80,'notifications.detail.width':896,'notifications.detail.height':576,'notifications.detail.insetX':32,'notifications.detail.insetY':64,'notifications.badge.width':180,'notifications.badge.height':44,'notifications.badge.insetX':604,'notifications.badge.insetY':10})
for event in ['focus.change','tab.change','data.update','layout.swap']:
 theme['motion'][event]={'recipe':'builtin.cut','durationMs':0,'distancePx':0,'easing':'outCubic'}
(B/'theme.json').write_text(json.dumps(theme,ensure_ascii=False,indent=2)+'\n')
manifest=json.loads((PREP/'bundle.planned.json').read_text())
# Remove only untouched starter files which are absent from the final registry.
for name in ['Home.qml','Small.qml','Large.qml','Motion.qml','Icon.qml','Scene.qml']:
 (Q/name).unlink(missing_ok=True)
manifest['resources']=[]
for file in sorted(B.rglob('*')):
 if not file.is_file() or file.name in ['bundle.json','theme.json','visual-registry.json','integrity.json']:continue
 rel=file.relative_to(B).as_posix(); kind={'.qml':'qml','.js':'js','.png':'image','.json':'data','.otf':'font','.ttf':'font'}.get(file.suffix,'license')
 manifest['resources'].append({'id':'res.'+rel.replace('/','.').replace('-','_').lower(), 'path':rel,'type':kind})
(B/'bundle.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
