# SmartPC — Inventario statico per il consolidamento UX

**8 ottobre 2026 · Dichiarazioni dei sorgenti; nessuna verifica runtime o fisica.**

Registro completo machine-readable e hash delle sei fonti: [static-inventory.json](evidence/ux-consolidation-2026-10-08/static-inventory.json). Studio e interpretazione: [dossier UX](ux-research-consolidation-2026-10-08.md).

## Riscontri

- **56 superfici** nel contratto e **48 presentazioni esplicite** in Apple Calm 1.2.0.
- **7 superfici Rete** e `scene.main` senza presentazione esplicita: `network.detail`, `network.devices`, `network.overview`, `network.ports`, `network.router`, `network.wifi`, `scene.main`, `settings.network`.
- Queste assenze non attestano viste rotte: fallback/ereditarietà e scene hanno percorsi differenti. Verificare ciascuna superficie; progettare la copertura Rete nativa nella nuova revisione.
- **13 sezioni e 97 dichiarazioni di riga** in `settingRows.sections`: includono indice, condizionali e template. Non sono 97 preferenze indipendenti o controlli contemporaneamente visibili.
- Il contratto dichiara `settings.casa` e `settings.network`, ma il registro delle righe non contiene le due sezioni. I controlli esistenti vanno integrati nell’inventario tramite SettingsPanel/adapter prima della migrazione; non dedurre che le pagine siano prive di opzioni.
- Catalogo builtin: **22 mapping semantici**. Sorgente Apple Calm: **50 forme, 22 alias**. La quantità non dimostra copertura delle azioni; serve la matrice ID → uso → renderer.

## Superfici dichiarate

| ID | Host | Contesto | Azioni dichiarate | Presentazione esplicita Apple Calm |
| --- | --- | --- | --- | --- |
| `account.usage` | page | PageContext | 7 | Sì |
| `alerts.badge` | notification | NotificationContext | 2 | Sì |
| `alerts.banner.large` | notification | NotificationContext | 2 | Sì |
| `alerts.banner.small` | notification | NotificationContext | 2 | Sì |
| `alerts.detail` | notification | NotificationContext | 3 | Sì |
| `alerts.inbox` | notification | NotificationContext | 5 | Sì |
| `alerts.urgent` | notification | NotificationContext | 3 | Sì |
| `casa.detail` | overlay | CasaContext | 8 | Sì |
| `casa.devices` | page | CasaContext | 9 | Sì |
| `casa.overview` | page | CasaContext | 9 | Sì |
| `device.info` | overlay | InfoContext | 10 | Sì |
| `home.clock` | page | PageContext | 7 | Sì |
| `home.day` | page | PageContext | 7 | Sì |
| `home.now` | page | PageContext | 7 | Sì |
| `network.detail` | overlay | NetworkContext | 10 | Assente; verificare percorso |
| `network.devices` | page | NetworkContext | 10 | Assente; verificare percorso |
| `network.overview` | page | NetworkContext | 11 | Assente; verificare percorso |
| `overlay.commands` | overlay | CommandsContext | 6 | Sì |
| `overlay.menu` | overlay | MenuContext | 9 | Sì |
| `overlay.summary` | overlay | SummaryContext | 6 | Sì |
| `racing.calendar` | overlay | RacingContext | 12 | Sì |
| `racing.driver.detail` | overlay | DriverContext | 12 | Sì |
| `racing.event.detail` | overlay | RacingContext | 12 | Sì |
| `racing.live` | overlay | RacingContext | 12 | Sì |
| `racing.overview` | page | PageContext | 12 | Sì |
| `racing.session.detail` | overlay | RacingContext | 12 | Sì |
| `racing.standings` | overlay | RacingContext | 12 | Sì |
| `scene.main` | scene | SceneContext | 0 | Assente; verificare percorso |
| `settings.account` | overlay | SettingsContext | 10 | Sì |
| `settings.appearance` | overlay | SettingsContext | 18 | Sì |
| `settings.appearance.notifications` | overlay | SettingsContext | 18 | Sì |
| `settings.casa` | overlay | CasaContext | 12 | Sì |
| `settings.display` | overlay | SettingsContext | 10 | Sì |
| `settings.index` | overlay | SettingsContext | 9 | Sì |
| `settings.integrations` | overlay | SettingsContext | 9 | Sì |
| `settings.modules` | overlay | SettingsContext | 10 | Sì |
| `settings.network` | overlay | NetworkContext | 13 | Assente; verificare percorso |
| `settings.notifications` | overlay | SettingsContext | 9 | Sì |
| `settings.notifications.categories` | overlay | SettingsContext | 10 | Sì |
| `settings.notifications.quiet` | overlay | SettingsContext | 10 | Sì |
| `settings.racing` | overlay | SettingsContext | 10 | Sì |
| `settings.sources` | overlay | SettingsContext | 10 | Sì |
| `settings.sport` | overlay | SettingsContext | 10 | Sì |
| `shell.main` | shell | ShellContext | 6 | Sì |
| `sport.fixtures` | overlay | SportListContext | 12 | Sì |
| `sport.match.detail` | overlay | MatchContext | 12 | Sì |
| `sport.overview` | page | PageContext | 12 | Sì |
| `sport.standings` | overlay | SportListContext | 12 | Sì |
| `sport.team` | page | PageContext | 12 | Sì |
| `sport.team.detail` | overlay | TeamContext | 12 | Sì |
| `sport.team.picker` | overlay | TeamPickerContext | 12 | Sì |
| `weather.forecast` | page | PageContext | 7 | Sì |
| `weather.now` | page | PageContext | 7 | Sì |
| `network.router` | overlay | NetworkRouterContext | 12 | Assente; verificare percorso |
| `network.wifi` | overlay | NetworkWifiContext | 12 | Assente; verificare percorso |
| `network.ports` | overlay | NetworkPortsContext | 12 | Assente; verificare percorso |

## Righe impostazioni dichiarate

| Sezione | Numero dichiarazioni | ID |
| --- | --- | --- |
| `settings.index` | 9 | `appearance`, `display`, `modules`, `notifications`, `account`, `integrations` (condizionale), `sources`, `casa`, `network` |
| `settings.display` | 6 | `display.mode`, `display.manualBrightness`, `display.dayBrightness`, `display.nightBrightness`, `display.dayStart`, `display.nightStart` |
| `settings.appearance` | 20 | `appearance.palette`, `appearance.motion`, `appearance.theme`, `appearance.homeComposition`, `appearance.textScale`, `appearance.density`, `appearance.cardRadius`, `appearance.accent`, `appearance.uiFont`, `appearance.numbersFont`, `appearance.transitions`, `appearance.scene`, `appearance.apply`, `appearance.cancel`, `appearance.reset`, `appearance.reload`, `appearance.clockFont`, `appearance.import`, `appearance.export`, `appearance.notifications` |
| `settings.appearance.notifications` | 25 | `notifications.visual.mode`, `notifications.visual.composition.small`, `notifications.visual.composition.large`, `notifications.visual.composition.urgent`, `notifications.visual.composition.badge`, `notifications.visual.composition.inbox`, `notifications.visual.composition.detail`, `notifications.visual.preview`, `notifications.visual.padding`, `notifications.visual.titleSize`, `notifications.visual.bodySize`, `notifications.visual.sourceSize`, `notifications.visual.radius`, `notifications.visual.anchor`, `notifications.visual.inboxRows`, `notifications.visual.titleFont`, `notifications.visual.bodyFont`, `notifications.visual.sourceFont`, `notifications.visual.icon`, `notifications.visual.source`, `notifications.visual.enter`, `notifications.visual.exit`, `appearance.apply`, `notifications.visual.reset`, `appearance.back` |
| `settings.modules` | 8 | `module.oggi`, `module.meteo`, `module.account`, `module.sport` (condizionale), `module.f1` (condizionale), `module.motogp` (condizionale), `module.casa` (condizionale), `module.network` (condizionale) |
| `settings.notifications` | 2 | `notifications.quiet`, `notifications.categories` |
| `settings.notifications.quiet` | 3 | `notifications.quiet.enabled`, `notifications.quiet.start`, `notifications.quiet.end` |
| `settings.notifications.categories` | 3 | `notifications.weatherInterruptions`, `notifications.accountInterruptions`, `notifications.sportGoals` (condizionale) |
| `settings.account` | 2 | `account.warningThreshold`, `account.criticalThreshold` |
| `settings.integrations` | 3 | `integration.sport` (condizionale), `integration.f1` (condizionale), `integration.motogp` (condizionale) |
| `settings.sources` | 8 | `source.weather`, `source.alerts`, `source.account`, `source.sport` (condizionale), `source.f1` (condizionale), `source.motogp` (condizionale), `source.casa` (condizionale), `source.network` (condizionale) |
| `settings.sport` | 5 | `sport.favouriteTeam`, `sport.showOnHome`, `sport.notifications`, `sport.season`, `sport.source` |
| `settings.racing` | 3 | `racing.season`, `racing.showOnHome`, `racing.source` |

## Completamento necessario

Durante U0 aggiungere etichetta effettiva, controlli generati dinamicamente, disponibilità, valore, persistenza, sede proposta e feedback. Affiancare catture/routing di tutti i temi e matrice semantica delle icone. Ricontrollare gli hash se cambiano i sorgenti; questa è la fotografia documentale della data indicata.
