# SmartPC Theme API 2 — contract reference

**Contract only: QML runtime module, broker and adapters are not implemented.**

Generated from the four canonical JSON documents. Do not edit generated files.

API fingerprint: `30013160355ad8ccb3f7c3e39569061e6f4cd9aa64893ea2444fa8a48901cec0`

This fingerprint is independent from the schema-1 registry fingerprint.

## Surfaces

| Content ID | Context/version | Host | Legacy route | Actions |
| --- | --- | --- | --- | --- |
| account.usage | PageContext 2 | page | — | navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step, selection.move |
| alerts.badge | NotificationContext 1 | notification | — | home, openInbox |
| alerts.banner.large | NotificationContext 1 | notification | — | home, openInbox |
| alerts.banner.small | NotificationContext 1 | notification | — | home, openInbox |
| alerts.detail | NotificationContext 1 | notification | alertDetail | back, home, scrollDetails |
| alerts.inbox | NotificationContext 1 | notification | alerts | back, home, moveSelection, openDetails, selectEvent |
| alerts.urgent | NotificationContext 1 | notification | — | dismiss, home, openDetails |
| device.info | InfoContext 1 | overlay | info | navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step, selection.move, selection.select, sources.refresh, tabs.select |
| home.day | PageContext 2 | page | — | details.open, navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step |
| home.now | PageContext 2 | page | — | details.open, navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step |
| overlay.commands | CommandsContext 1 | overlay | commands | navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step |
| overlay.menu | MenuContext 1 | overlay | menu | menu.activate, navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step, selection.move, selection.select |
| overlay.summary | SummaryContext 1 | overlay | detail | navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step |
| racing.calendar | RacingContext 1 | overlay | racingList | details.open, details.refresh, details.scroll, navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step, selection.move, selection.select, tabs.select |
| racing.driver.detail | DriverContext 1 | overlay | racingDriver | details.open, details.refresh, details.scroll, navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step, selection.move, selection.select, tabs.select |
| racing.event.detail | RacingContext 1 | overlay | racingEvent | details.open, details.refresh, details.scroll, navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step, selection.move, selection.select, tabs.select |
| racing.live | RacingContext 1 | overlay | racingTiming | details.open, details.refresh, details.scroll, navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step, selection.move, selection.select, tabs.select |
| racing.overview | PageContext 2 | page | — | details.open, details.refresh, details.scroll, navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step, selection.move, selection.select, tabs.select |
| racing.session.detail | RacingContext 1 | overlay | racingSession | details.open, details.refresh, details.scroll, navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step, selection.move, selection.select, tabs.select |
| racing.standings | RacingContext 1 | overlay | racingTable | details.open, details.refresh, details.scroll, navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step, selection.move, selection.select, tabs.select |
| scene.main | SceneContext 1 | scene | — | — |
| settings.account | SettingsContext 1 | overlay | accountSettings | navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step, selection.move, selection.select, settings.activate, settings.adjust |
| settings.appearance | SettingsContext 1 | overlay | appearance | appearance.apply, appearance.cancel, appearance.export, appearance.import, appearance.notificationPreview, appearance.preview, appearance.reload, appearance.reset, navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step, selection.move, selection.select, settings.activate, settings.adjust |
| settings.appearance.notifications | SettingsContext 1 | overlay | appearanceNotifications | appearance.apply, appearance.cancel, appearance.export, appearance.import, appearance.notificationPreview, appearance.preview, appearance.reload, appearance.reset, navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step, selection.move, selection.select, settings.activate, settings.adjust |
| settings.display | SettingsContext 1 | overlay | system | navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step, selection.move, selection.select, settings.activate, settings.adjust |
| settings.index | SettingsContext 1 | overlay | settings | navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step, selection.move, selection.select, settings.activate |
| settings.integrations | SettingsContext 1 | overlay | integrations | navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step, selection.move, selection.select, settings.activate |
| settings.modules | SettingsContext 1 | overlay | modules | navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step, selection.move, selection.select, settings.activate, settings.adjust |
| settings.notifications | SettingsContext 1 | overlay | notifications | navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step, selection.move, selection.select, settings.activate |
| settings.notifications.categories | SettingsContext 1 | overlay | notificationCategories | navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step, selection.move, selection.select, settings.activate, settings.adjust |
| settings.notifications.quiet | SettingsContext 1 | overlay | notificationQuiet | navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step, selection.move, selection.select, settings.activate, settings.adjust |
| settings.racing | SettingsContext 1 | overlay | racingSettings | navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step, selection.move, selection.select, settings.activate, settings.adjust |
| settings.sources | SettingsContext 1 | overlay | sources | navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step, selection.move, selection.select, settings.activate, sources.refresh |
| settings.sport | SettingsContext 1 | overlay | sportSettings | navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step, selection.move, selection.select, settings.activate, settings.adjust |
| shell.main | ShellContext 1 | shell | — | navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step |
| sport.fixtures | SportListContext 1 | overlay | sportList | details.open, details.refresh, details.scroll, navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step, selection.move, selection.select, tabs.select |
| sport.match.detail | MatchContext 1 | overlay | sportDetail | details.open, details.refresh, details.scroll, navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step, selection.move, selection.select, tabs.select |
| sport.overview | PageContext 2 | page | — | details.open, details.refresh, details.scroll, navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step, selection.move, selection.select, tabs.select |
| sport.standings | SportListContext 1 | overlay | sportTable | details.open, details.refresh, details.scroll, navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step, selection.move, selection.select, tabs.select |
| sport.team | PageContext 2 | page | — | details.open, details.refresh, details.scroll, navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step, selection.move, selection.select, tabs.select |
| sport.team.detail | TeamContext 1 | overlay | sportTeam | details.open, details.refresh, details.scroll, navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step, selection.move, selection.select, tabs.select |
| sport.team.picker | TeamPickerContext 1 | overlay | sportTeamPicker | details.open, details.refresh, details.scroll, navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step, selection.move, selection.select, tabs.select |
| weather.forecast | PageContext 2 | page | — | details.open, navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step |
| weather.now | PageContext 2 | page | — | details.open, navigation.back, navigation.family.step, navigation.home, navigation.inbox, navigation.menu, navigation.view.step |

## Contexts

### SurfaceContext

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| contentId | string | required / non-null | {} |
| contextVersion | int | required / non-null | {"const": 1} |
| surfaceInstanceId | string | required / non-null | {} |
| appearanceRevision | int | required / non-null | {"minimum": 0} |
| dataRevision | int | required / non-null | {"minimum": 0} |
| style | ThemeStyle | required / non-null | {} |
| lifecycle | SurfaceLifecycle | required / non-null | {} |
| viewport | Rect | required / non-null | {} |
| safeArea | Rect | required / non-null | {} |
| commands | CommandModel | required / non-null | {} |
| actions | ActionModel | required / non-null | {} |

Method `requestAction(string, string, legacyMap) → ActionResult`.

### PageContext

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| contentId | string | required / non-null | {} |
| contextVersion | int | required / non-null | {"const": 2} |
| surfaceInstanceId | string | required / non-null | {} |
| appearanceRevision | int | required / non-null | {"minimum": 0} |
| dataRevision | int | required / non-null | {"minimum": 0} |
| style | ThemeStyle | required / non-null | {} |
| lifecycle | SurfaceLifecycle | required / non-null | {} |
| viewport | Rect | required / non-null | {} |
| safeArea | Rect | required / non-null | {} |
| commands | CommandModel | required / non-null | {} |
| actions | ActionModel | required / non-null | {} |
| clock | ClockState | required / non-null | {} |
| selection | SelectionState | required / non-null | {} |
| weather | WeatherData | required / nullable | {} |
| account | AccountData | required / nullable | {} |
| nextEvent | NextEventData | required / nullable | {} |
| sport | SportData | required / nullable | {} |
| team | TeamData | required / nullable | {} |
| fantasy | FantasyData | required / nullable | {} |
| racing | RacingData | required / nullable | {} |

Method `requestAction(string, string, legacyMap) → ActionResult`.

### ShellContext

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| contentId | string | required / non-null | {} |
| contextVersion | int | required / non-null | {"const": 1} |
| surfaceInstanceId | string | required / non-null | {} |
| appearanceRevision | int | required / non-null | {"minimum": 0} |
| dataRevision | int | required / non-null | {"minimum": 0} |
| style | ThemeStyle | required / non-null | {} |
| lifecycle | SurfaceLifecycle | required / non-null | {} |
| viewport | Rect | required / non-null | {} |
| safeArea | Rect | required / non-null | {} |
| commands | CommandModel | required / non-null | {} |
| actions | ActionModel | required / non-null | {} |
| families | FamilyModel | required / non-null | {} |
| currentFamilyId | string | required / non-null | {} |
| currentViewId | string | required / non-null | {} |
| navigation | NavigationSnapshot | required / non-null | {} |
| layout | ShellLayout | required / non-null | {} |
| uiStatus | UiStatus | required / non-null | {} |

Method `requestAction(string, string, legacyMap) → ActionResult`.

### MenuContext

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| contentId | string | required / non-null | {} |
| contextVersion | int | required / non-null | {"const": 1} |
| surfaceInstanceId | string | required / non-null | {} |
| appearanceRevision | int | required / non-null | {"minimum": 0} |
| dataRevision | int | required / non-null | {"minimum": 0} |
| style | ThemeStyle | required / non-null | {} |
| lifecycle | SurfaceLifecycle | required / non-null | {} |
| viewport | Rect | required / non-null | {} |
| safeArea | Rect | required / non-null | {} |
| commands | CommandModel | required / non-null | {} |
| actions | ActionModel | required / non-null | {} |
| rows | MenuRowModel | required / non-null | {} |
| selection | SelectionState | required / non-null | {} |

Method `requestAction(string, string, legacyMap) → ActionResult`.

### CommandsContext

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| contentId | string | required / non-null | {} |
| contextVersion | int | required / non-null | {"const": 1} |
| surfaceInstanceId | string | required / non-null | {} |
| appearanceRevision | int | required / non-null | {"minimum": 0} |
| dataRevision | int | required / non-null | {"minimum": 0} |
| style | ThemeStyle | required / non-null | {} |
| lifecycle | SurfaceLifecycle | required / non-null | {} |
| viewport | Rect | required / non-null | {} |
| safeArea | Rect | required / non-null | {} |
| commands | CommandModel | required / non-null | {} |
| actions | ActionModel | required / non-null | {} |
| keyMap | CommandModel | required / non-null | {} |
| firstRun | bool | required / non-null | {} |

Method `requestAction(string, string, legacyMap) → ActionResult`.

### SummaryContext

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| contentId | string | required / non-null | {} |
| contextVersion | int | required / non-null | {"const": 1} |
| surfaceInstanceId | string | required / non-null | {} |
| appearanceRevision | int | required / non-null | {"minimum": 0} |
| dataRevision | int | required / non-null | {"minimum": 0} |
| style | ThemeStyle | required / non-null | {} |
| lifecycle | SurfaceLifecycle | required / non-null | {} |
| viewport | Rect | required / non-null | {} |
| safeArea | Rect | required / non-null | {} |
| commands | CommandModel | required / non-null | {} |
| actions | ActionModel | required / non-null | {} |
| familyId | string | required / non-null | {} |
| clock | ClockState | required / non-null | {} |
| weather | WeatherData | required / nullable | {} |
| nextEvent | NextEventData | required / nullable | {} |

Method `requestAction(string, string, legacyMap) → ActionResult`.

### SettingsContext

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| contentId | string | required / non-null | {} |
| contextVersion | int | required / non-null | {"const": 1} |
| surfaceInstanceId | string | required / non-null | {} |
| appearanceRevision | int | required / non-null | {"minimum": 0} |
| dataRevision | int | required / non-null | {"minimum": 0} |
| style | ThemeStyle | required / non-null | {} |
| lifecycle | SurfaceLifecycle | required / non-null | {} |
| viewport | Rect | required / non-null | {} |
| safeArea | Rect | required / non-null | {} |
| commands | CommandModel | required / non-null | {} |
| actions | ActionModel | required / non-null | {} |
| sectionId | string | required / non-null | {} |
| rows | SettingRowModel | required / non-null | {} |
| selection | SelectionState | required / non-null | {} |
| draft | AppearanceDraftSummary | required / nullable | {} |
| operation | OperationState | required / non-null | {} |
| description | string | required / non-null | {} |
| feedback | string | required / non-null | {} |

Method `requestAction(string, string, legacyMap) → ActionResult`.

### InfoContext

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| contentId | string | required / non-null | {} |
| contextVersion | int | required / non-null | {"const": 1} |
| surfaceInstanceId | string | required / non-null | {} |
| appearanceRevision | int | required / non-null | {"minimum": 0} |
| dataRevision | int | required / non-null | {"minimum": 0} |
| style | ThemeStyle | required / non-null | {} |
| lifecycle | SurfaceLifecycle | required / non-null | {} |
| viewport | Rect | required / non-null | {} |
| safeArea | Rect | required / non-null | {} |
| commands | CommandModel | required / non-null | {} |
| actions | ActionModel | required / non-null | {} |
| tabs | TabModel | required / non-null | {} |
| rows | InfoRowModel | required / non-null | {} |
| selection | SelectionState | required / non-null | {} |
| sources | SourceModel | required / non-null | {} |
| updatedAt | real | required / nullable | {"unit": "epochSeconds"} |

Method `requestAction(string, string, legacyMap) → ActionResult`.

### SportListContext

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| contentId | string | required / non-null | {} |
| contextVersion | int | required / non-null | {"const": 1} |
| surfaceInstanceId | string | required / non-null | {} |
| appearanceRevision | int | required / non-null | {"minimum": 0} |
| dataRevision | int | required / non-null | {"minimum": 0} |
| style | ThemeStyle | required / non-null | {} |
| lifecycle | SurfaceLifecycle | required / non-null | {} |
| viewport | Rect | required / non-null | {} |
| safeArea | Rect | required / non-null | {} |
| commands | CommandModel | required / non-null | {} |
| actions | ActionModel | required / non-null | {} |
| source | SourceState | required / non-null | {} |
| matches | MatchModel | required / non-null | {} |
| standings | StandingModel | required / non-null | {} |
| rounds | RoundModel | required / non-null | {} |
| selection | SelectionState | required / non-null | {} |
| selectedRoundId | string | required / non-null | {} |
| favouriteTeamId | string | required / non-null | {} |

Method `requestAction(string, string, legacyMap) → ActionResult`.

### MatchContext

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| contentId | string | required / non-null | {} |
| contextVersion | int | required / non-null | {"const": 1} |
| surfaceInstanceId | string | required / non-null | {} |
| appearanceRevision | int | required / non-null | {"minimum": 0} |
| dataRevision | int | required / non-null | {"minimum": 0} |
| style | ThemeStyle | required / non-null | {} |
| lifecycle | SurfaceLifecycle | required / non-null | {} |
| viewport | Rect | required / non-null | {} |
| safeArea | Rect | required / non-null | {} |
| commands | CommandModel | required / non-null | {} |
| actions | ActionModel | required / non-null | {} |
| match | MatchData | required / non-null | {} |
| source | SourceState | required / non-null | {} |
| tabs | TabModel | required / non-null | {} |
| selection | SelectionState | required / non-null | {} |
| fantasy | FantasyData | required / nullable | {} |
| detailOperation | OperationState | required / non-null | {} |
| origin | string | required / non-null | {} |

Method `requestAction(string, string, legacyMap) → ActionResult`.

### TeamContext

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| contentId | string | required / non-null | {} |
| contextVersion | int | required / non-null | {"const": 1} |
| surfaceInstanceId | string | required / non-null | {} |
| appearanceRevision | int | required / non-null | {"minimum": 0} |
| dataRevision | int | required / non-null | {"minimum": 0} |
| style | ThemeStyle | required / non-null | {} |
| lifecycle | SurfaceLifecycle | required / non-null | {} |
| viewport | Rect | required / non-null | {} |
| safeArea | Rect | required / non-null | {} |
| commands | CommandModel | required / non-null | {} |
| actions | ActionModel | required / non-null | {} |
| team | TeamData | required / non-null | {} |
| tabs | TabModel | required / non-null | {} |
| selection | SelectionState | required / non-null | {} |
| calendarScope | string | required / non-null | {} |
| serieAOnly | bool | required / non-null | {} |

Method `requestAction(string, string, legacyMap) → ActionResult`.

### TeamPickerContext

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| contentId | string | required / non-null | {} |
| contextVersion | int | required / non-null | {"const": 1} |
| surfaceInstanceId | string | required / non-null | {} |
| appearanceRevision | int | required / non-null | {"minimum": 0} |
| dataRevision | int | required / non-null | {"minimum": 0} |
| style | ThemeStyle | required / non-null | {} |
| lifecycle | SurfaceLifecycle | required / non-null | {} |
| viewport | Rect | required / non-null | {} |
| safeArea | Rect | required / non-null | {} |
| commands | CommandModel | required / non-null | {} |
| actions | ActionModel | required / non-null | {} |
| teams | TeamIdentityModel | required / non-null | {} |
| selection | SelectionState | required / non-null | {} |
| savedTeamId | string | required / non-null | {} |

Method `requestAction(string, string, legacyMap) → ActionResult`.

### RacingContext

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| contentId | string | required / non-null | {} |
| contextVersion | int | required / non-null | {"const": 1} |
| surfaceInstanceId | string | required / non-null | {} |
| appearanceRevision | int | required / non-null | {"minimum": 0} |
| dataRevision | int | required / non-null | {"minimum": 0} |
| style | ThemeStyle | required / non-null | {} |
| lifecycle | SurfaceLifecycle | required / non-null | {} |
| viewport | Rect | required / non-null | {} |
| safeArea | Rect | required / non-null | {} |
| commands | CommandModel | required / non-null | {} |
| actions | ActionModel | required / non-null | {} |
| kind | string | required / non-null | {"enum": ["f1", "motogp"]} |
| source | SourceState | required / non-null | {} |
| racing | RacingData | required / non-null | {} |
| event | RacingEventData | required / nullable | {} |
| session | RacingSessionData | required / nullable | {} |
| tabs | TabModel | required / non-null | {} |
| selection | SelectionState | required / non-null | {} |
| detailOperation | OperationState | required / non-null | {} |

Method `requestAction(string, string, legacyMap) → ActionResult`.

### DriverContext

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| contentId | string | required / non-null | {} |
| contextVersion | int | required / non-null | {"const": 1} |
| surfaceInstanceId | string | required / non-null | {} |
| appearanceRevision | int | required / non-null | {"minimum": 0} |
| dataRevision | int | required / non-null | {"minimum": 0} |
| style | ThemeStyle | required / non-null | {} |
| lifecycle | SurfaceLifecycle | required / non-null | {} |
| viewport | Rect | required / non-null | {} |
| safeArea | Rect | required / non-null | {} |
| commands | CommandModel | required / non-null | {} |
| actions | ActionModel | required / non-null | {} |
| kind | string | required / non-null | {"enum": ["f1", "motogp"]} |
| driver | DriverData | required / non-null | {} |
| source | SourceState | required / non-null | {} |
| live | bool | required / non-null | {} |
| tabs | TabModel | required / non-null | {} |
| selection | SelectionState | required / non-null | {} |
| detailOperation | OperationState | required / non-null | {} |

Method `requestAction(string, string, legacyMap) → ActionResult`.

### SceneContext

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| contentId | string | required / non-null | {} |
| contextVersion | int | required / non-null | {"const": 1} |
| surfaceInstanceId | string | required / non-null | {} |
| appearanceRevision | int | required / non-null | {"minimum": 0} |
| dataRevision | int | required / non-null | {"minimum": 0} |
| style | ThemeStyle | required / non-null | {} |
| lifecycle | SurfaceLifecycle | required / non-null | {} |
| viewport | Rect | required / non-null | {} |
| safeArea | Rect | required / non-null | {} |
| commands | CommandModel | required / non-null | {} |
| actions | ActionModel | required / non-null | {} |
| actor | ActorSnapshot | required / non-null | {} |
| configuration | SceneConfiguration | required / non-null | {} |
| occupiedRegions | array | required / non-null | {"items": "Rect", "maxItems": 64} |
| notification | NotificationEvent | required / nullable | {} |
| clock | ClockState | required / non-null | {} |
| motionPolicy | MotionPolicy | required / non-null | {} |
| suspended | bool | required / non-null | {} |

Method `requestAction(string, string, legacyMap) → ActionResult`.

### NotificationContext

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| apiVersion | int | required / non-null | {"const": 1} |
| contentId | string | required / non-null | {} |
| mode | string | required / non-null | {} |
| style | ThemeStyle | required / non-null | {} |
| visualStyle | NotificationStyle | required / non-null | {} |
| active | bool | required / non-null | {} |
| interactive | bool | required / non-null | {} |
| exiting | bool | required / non-null | {} |
| preview | bool | required / non-null | {} |
| ready | bool | required / non-null | {} |
| error | string | required / non-null | {} |
| viewportWidth | int | required / non-null | {"minimum": 0} |
| viewportHeight | int | required / non-null | {"minimum": 0} |
| event | legacyMap | required / non-null | {} |
| items | array | required / non-null | {"items": "legacyMap"} |
| selectedEventId | string | required / non-null | {} |
| unreadCount | int | required / non-null | {"minimum": 0} |
| sourceStatus | string | required / non-null | {} |
| scrollOffset | real | required / non-null | {"minimum": 0} |
| scrollMaximum | real | required / non-null | {"minimum": 0} |
| occupiedRegions | array | required / non-null | {"items": "Rect", "maxItems": 64} |
| appearanceRevision | int | required / non-null | {"minimum": 0} |
| safeArea | Rect | required / non-null | {} |
| actions | array | required / non-null | {"items": "string"} |
| commandHints | array | required / non-null | {"items": "legacyMap"} |
| guideText | string | required / non-null | {} |
| sourceText | string | required / non-null | {} |
| validityText | string | required / non-null | {} |
| iconId | string | required / non-null | {} |
| eventData | NotificationEvent | optional / nullable | {} |
| itemModel | NotificationEventModel | optional / non-null | {} |
| commands | CommandModel | optional / non-null | {} |
| sourceMetadata | SourceState | optional / nullable | {} |

Method `requestAction(string, string, legacyMap) → bool`.

Method `request(string, string, legacyMap) → ActionResult`.

Method `settleMotion() → void`.

Method `formatStamp(scalar) → string`.

Signal `settleMotionRequested()`.

## DTOs

### Point

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| x | real | required / non-null | {} |
| y | real | required / non-null | {} |

### Rect

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| x | real | required / non-null | {} |
| y | real | required / non-null | {} |
| width | real | required / non-null | {"minimum": 0} |
| height | real | required / non-null | {"minimum": 0} |

### SourceState

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| status | string | required / non-null | {"enum": ["active", "updating", "stale", "offline", "error", "unavailable", "pending"]} |
| sourceId | string | required / non-null | {} |
| sourceLabel | string | required / non-null | {} |
| updatedAt | real | required / nullable | {"unit": "epochSeconds"} |
| checkedAt | real | required / nullable | {"unit": "epochSeconds"} |
| hasData | bool | required / non-null | {} |
| isStale | bool | required / non-null | {} |
| errorCode | string | required / non-null | {} |
| error | string | required / non-null | {} |
| dataRevision | string | required / non-null | {} |

### NumericValue

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| available | bool | required / non-null | {} |
| value | real | required / nullable | {} |
| unit | string | required / non-null | {} |
| displayText | string | required / non-null | {} |
| sourceRevision | string | required / non-null | {} |

### ScalarValue

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| available | bool | required / non-null | {} |
| value | scalar | required / nullable | {} |
| unit | string | required / non-null | {} |
| displayText | string | required / non-null | {} |

### SurfaceLifecycle

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| state | string | required / non-null | {"enum": ["preparing", "active", "suspended", "exiting", "disposed"]} |
| active | bool | required / non-null | {} |
| interactive | bool | required / non-null | {} |
| preview | bool | required / non-null | {} |
| generation | int | required / non-null | {"minimum": 0} |

### ClockState

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| epoch | real | required / non-null | {"unit": "epochSeconds"} |
| timeText | string | required / non-null | {} |
| dateText | string | required / non-null | {} |
| timezone | string | required / non-null | {} |
| locale | string | required / non-null | {} |
| night | bool | required / non-null | {} |

### SelectionState

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| selectedId | string | required / non-null | {} |
| tabId | string | required / non-null | {} |
| anchorId | string | required / non-null | {} |
| offset | real | required / non-null | {"minimum": 0} |
| index | int | required / non-null | {"minimum": -1} |
| count | int | required / non-null | {"minimum": 0} |

### OperationState

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| requestId | string | required / non-null | {} |
| status | string | required / non-null | {"enum": ["idle", "accepted", "pending", "completed", "failed", "rejected"]} |
| errorCode | string | required / non-null | {} |
| message | string | required / non-null | {} |

### ActionResult

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| accepted | bool | required / non-null | {} |
| requestId | string | required / non-null | {} |
| status | string | required / non-null | {"enum": ["accepted", "pending", "completed", "failed", "rejected"]} |
| errorCode | string | required / non-null | {} |

### Command

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| key | int | required / non-null | {"minimum": 1, "maximum": 9} |
| actionId | string | required / non-null | {} |
| targetId | string | required / non-null | {} |
| label | string | required / non-null | {} |
| enabled | bool | required / non-null | {} |

### AvailableAction

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| enabled | bool | required / non-null | {} |
| reason | string | required / non-null | {} |

### Tab

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| label | string | required / non-null | {} |
| enabled | bool | required / non-null | {} |

### Family

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| label | string | required / non-null | {} |
| available | bool | required / non-null | {} |
| visible | bool | required / non-null | {} |
| views | TabModel | required / non-null | {} |

### NavigationSnapshot

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| familyId | string | required / non-null | {} |
| viewId | string | required / non-null | {} |
| overlayId | string | required / non-null | {} |
| familyPosition | int | required / non-null | {"minimum": 0} |
| familyCount | int | required / non-null | {"minimum": 0} |
| viewPosition | int | required / non-null | {"minimum": 0} |
| viewCount | int | required / non-null | {"minimum": 0} |

### ShellLayout

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| header | Rect | required / non-null | {} |
| content | Rect | required / non-null | {} |
| guide | Rect | required / non-null | {} |
| sceneSafeRegions | array | required / non-null | {"items": "Rect", "maxItems": 64} |

### UiStatus

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| urgent | bool | required / non-null | {} |
| recovery | bool | required / non-null | {} |
| quiet | bool | required / non-null | {} |
| night | bool | required / non-null | {} |
| diagnostics | bool | required / non-null | {} |

### AppearanceDraftSummary

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| editing | bool | required / non-null | {} |
| themeId | string | required / non-null | {} |
| paletteMode | string | required / non-null | {"enum": ["auto", "day", "night"]} |
| motionMode | string | required / non-null | {"enum": ["normal", "reduced", "off"]} |
| textScale | real | required / non-null | {"minimum": 0.85, "maximum": 1.1} |
| readyToApply | bool | required / non-null | {} |
| status | string | required / non-null | {} |
| error | string | required / non-null | {} |

### MenuRow

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| title | string | required / non-null | {} |
| detail | string | required / non-null | {} |
| enabled | bool | required / non-null | {} |
| actionId | string | required / non-null | {} |
| targetId | string | required / non-null | {} |

### SettingOption

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| label | string | required / non-null | {} |
| value | scalar | required / nullable | {} |

### SettingRow

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| title | string | required / non-null | {} |
| detail | string | required / non-null | {} |
| control | string | required / non-null | {"enum": ["action", "toggle", "choice", "number", "theme", "transfer"]} |
| value | ScalarValue | required / non-null | {} |
| enabled | bool | required / non-null | {} |
| reason | string | required / non-null | {} |
| actionId | string | required / non-null | {} |
| targetId | string | required / non-null | {} |
| minimum | real | required / nullable | {} |
| maximum | real | required / nullable | {} |
| step | real | required / nullable | {} |
| options | SettingOptionModel | required / non-null | {} |

### InfoRow

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| title | string | required / non-null | {} |
| value | ScalarValue | required / non-null | {} |
| detail | string | required / non-null | {} |
| sourceId | string | required / non-null | {} |

### WeatherForecast

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| date | string | required / non-null | {"format": "date"} |
| dayText | string | required / non-null | {} |
| code | int | required / non-null | {"minimum": -1} |
| description | string | required / non-null | {} |
| high | NumericValue | required / non-null | {} |
| low | NumericValue | required / non-null | {} |
| rainProbability | NumericValue | required / non-null | {} |

### WeatherData

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| source | SourceState | required / non-null | {} |
| location | string | required / non-null | {} |
| code | int | required / non-null | {"minimum": -1} |
| description | string | required / non-null | {} |
| temperature | NumericValue | required / non-null | {} |
| feelsLike | NumericValue | required / non-null | {} |
| humidity | NumericValue | required / non-null | {} |
| precipitation | NumericValue | required / non-null | {} |
| rainProbability | NumericValue | required / non-null | {} |
| windSpeed | NumericValue | required / non-null | {} |
| windDirection | NumericValue | required / non-null | {} |
| windDirectionText | string | required / non-null | {} |
| gusts | NumericValue | required / non-null | {} |
| observationAt | real | required / nullable | {"unit": "epochSeconds"} |
| forecast | WeatherForecastModel | required / non-null | {} |

### NextEventData

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| title | string | required / non-null | {} |
| category | string | required / non-null | {} |
| startsAt | real | required / nullable | {"unit": "epochSeconds"} |
| whenText | string | required / non-null | {} |
| source | SourceState | required / non-null | {} |

### AccountWindow

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| label | string | required / non-null | {} |
| usedPercent | NumericValue | required / non-null | {} |
| windowDurationMinutes | NumericValue | required / non-null | {} |
| resetsAt | real | required / nullable | {"unit": "epochSeconds"} |
| severity | string | required / non-null | {"enum": ["normal", "warning", "critical", "unavailable"]} |

### AccountData

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| source | SourceState | required / non-null | {} |
| plan | string | required / non-null | {} |
| windows | AccountWindowModel | required / non-null | {} |
| resetCredits | NumericValue | required / non-null | {} |
| warningThreshold | int | required / non-null | {"minimum": 1, "maximum": 100} |
| criticalThreshold | int | required / non-null | {"minimum": 1, "maximum": 100} |

### TeamIdentity

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| name | string | required / non-null | {} |
| shortName | string | required / non-null | {} |
| crestId | string | required / non-null | {} |

### MatchEvent

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| kind | string | required / non-null | {} |
| minute | NumericValue | required / non-null | {} |
| teamId | string | required / non-null | {} |
| playerId | string | required / non-null | {} |
| playerName | string | required / non-null | {} |
| text | string | required / non-null | {} |

### MatchStatistic

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| label | string | required / non-null | {} |
| home | NumericValue | required / non-null | {} |
| away | NumericValue | required / non-null | {} |

### LineupPlayer

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| name | string | required / non-null | {} |
| shirtNumber | NumericValue | required / non-null | {} |
| role | string | required / non-null | {} |
| group | string | required / non-null | {} |
| inMinute | NumericValue | required / non-null | {} |
| outMinute | NumericValue | required / non-null | {} |

### Lineup

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| teamId | string | required / non-null | {} |
| formation | string | required / non-null | {} |
| coach | string | required / non-null | {} |
| players | LineupPlayerModel | required / non-null | {} |

### MatchData

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| competitionId | string | required / non-null | {} |
| competitionName | string | required / non-null | {} |
| season | string | required / non-null | {} |
| roundId | string | required / non-null | {} |
| source | SourceState | required / non-null | {} |
| providerMatchId | string | required / non-null | {} |
| status | string | required / non-null | {"enum": ["scheduled", "live", "finished", "postponed", "cancelled", "suspended", "unavailable"]} |
| rawStatus | string | required / non-null | {} |
| home | TeamIdentity | required / non-null | {} |
| away | TeamIdentity | required / non-null | {} |
| homeScore | NumericValue | required / non-null | {} |
| awayScore | NumericValue | required / non-null | {} |
| kickoffAt | real | required / nullable | {"unit": "epochSeconds"} |
| whenText | string | required / non-null | {} |
| minute | NumericValue | required / non-null | {} |
| pendingVAR | bool | required / non-null | {} |
| venue | string | required / non-null | {} |
| events | MatchEventModel | required / non-null | {} |
| statistics | MatchStatisticModel | required / non-null | {} |
| lineups | LineupModel | required / non-null | {} |
| detailLoading | bool | required / non-null | {} |
| detailError | string | required / non-null | {} |
| detailFetchedAt | real | required / nullable | {"unit": "epochSeconds"} |

### Standing

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| entityId | string | required / non-null | {} |
| name | string | required / non-null | {} |
| position | NumericValue | required / non-null | {} |
| played | NumericValue | required / non-null | {} |
| points | NumericValue | required / non-null | {} |
| wins | NumericValue | required / non-null | {} |
| draws | NumericValue | required / non-null | {} |
| losses | NumericValue | required / non-null | {} |
| goalsFor | NumericValue | required / non-null | {} |
| goalsAgainst | NumericValue | required / non-null | {} |
| goalDifference | NumericValue | required / non-null | {} |

### Round

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| label | string | required / non-null | {} |

### SportData

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| source | SourceState | required / non-null | {} |
| competitionId | string | required / non-null | {} |
| competitionName | string | required / non-null | {} |
| season | string | required / non-null | {} |
| calendarScope | string | required / non-null | {} |
| matches | MatchModel | required / non-null | {} |
| standings | StandingModel | required / non-null | {} |
| teams | TeamIdentityModel | required / non-null | {} |
| rounds | RoundModel | required / non-null | {} |
| activeMatchIds | array | required / non-null | {"items": "string"} |
| favouriteTeamId | string | required / non-null | {} |
| hasLiveView | bool | required / non-null | {} |
| liveVerified | bool | required / non-null | {} |
| goalsEnabled | bool | required / non-null | {} |

### TeamData

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| identity | TeamIdentity | required / non-null | {} |
| source | SourceState | required / non-null | {} |
| calendarScope | string | required / non-null | {} |
| fixtures | MatchModel | required / non-null | {} |
| squad | LineupPlayerModel | required / non-null | {} |
| info | InfoRowModel | required / non-null | {} |
| standing | Standing | required / nullable | {} |
| recordText | string | required / non-null | {} |
| cacheError | string | required / non-null | {} |

### FantasyBonus

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| label | string | required / non-null | {} |
| count | NumericValue | required / non-null | {} |
| points | NumericValue | required / non-null | {} |

### FantasyPlayer

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| name | string | required / non-null | {} |
| role | string | required / non-null | {} |
| shirtNumber | NumericValue | required / non-null | {} |
| group | string | required / non-null | {} |
| inMinute | NumericValue | required / non-null | {} |
| outMinute | NumericValue | required / non-null | {} |
| vote | NumericValue | required / non-null | {} |
| fantavote | NumericValue | required / non-null | {} |
| voteText | string | required / non-null | {} |
| fantavoteText | string | required / non-null | {} |
| withoutVote | bool | required / non-null | {} |
| bonuses | FantasyBonusModel | required / non-null | {} |

### FantasyTeam

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| name | string | required / non-null | {} |
| players | FantasyPlayerModel | required / non-null | {} |
| total | NumericValue | required / non-null | {} |

### FantasyData

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| source | SourceState | required / non-null | {} |
| matchId | string | required / non-null | {} |
| provisional | bool | required / non-null | {} |
| liveVerified | bool | required / non-null | {} |
| loading | bool | required / non-null | {} |
| teams | FantasyTeamModel | required / non-null | {} |
| message | string | required / non-null | {} |
| warning | string | required / non-null | {} |
| liveNotice | string | required / non-null | {} |
| cacheError | string | required / non-null | {} |

### RacingTiming

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| driverId | string | required / non-null | {} |
| driverName | string | required / non-null | {} |
| position | NumericValue | required / non-null | {} |
| lap | NumericValue | required / non-null | {} |
| time | NumericValue | required / non-null | {} |
| gap | NumericValue | required / non-null | {} |
| interval | NumericValue | required / non-null | {} |
| speed | NumericValue | required / non-null | {} |
| tyre | string | required / non-null | {} |
| compound | string | required / non-null | {} |
| status | string | required / non-null | {} |
| team | string | required / non-null | {} |
| points | NumericValue | required / non-null | {} |

### PitStop

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| lap | NumericValue | required / non-null | {} |
| duration | NumericValue | required / non-null | {} |
| stopNumber | NumericValue | required / non-null | {} |
| timeText | string | required / non-null | {} |

### LapTime

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| lap | NumericValue | required / non-null | {} |
| time | NumericValue | required / non-null | {} |
| position | NumericValue | required / non-null | {} |

### Stint

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| compound | string | required / non-null | {} |
| startLap | NumericValue | required / non-null | {} |
| endLap | NumericValue | required / non-null | {} |
| tyreAge | NumericValue | required / non-null | {} |

### DriverData

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| name | string | required / non-null | {} |
| team | string | required / non-null | {} |
| nationality | string | required / non-null | {} |
| number | NumericValue | required / non-null | {} |
| timing | RacingTiming | required / nullable | {} |
| detailRows | InfoRowModel | required / non-null | {} |
| pitStops | PitStopModel | required / non-null | {} |
| laps | LapTimeModel | required / non-null | {} |
| stints | StintModel | required / non-null | {} |

### RacingSessionData

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| kind | string | required / non-null | {} |
| name | string | required / non-null | {} |
| startsAt | real | required / nullable | {"unit": "epochSeconds"} |
| endsAt | real | required / nullable | {"unit": "epochSeconds"} |
| status | string | required / non-null | {} |
| results | RacingTimingModel | required / non-null | {} |
| info | InfoRowModel | required / non-null | {} |
| source | SourceState | required / non-null | {} |

### RacingEventData

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| name | string | required / non-null | {} |
| roundId | string | required / non-null | {} |
| startsAt | real | required / nullable | {"unit": "epochSeconds"} |
| endsAt | real | required / nullable | {"unit": "epochSeconds"} |
| circuit | string | required / non-null | {} |
| sessions | RacingSessionModel | required / non-null | {} |
| info | InfoRowModel | required / non-null | {} |
| summary | InfoRowModel | required / non-null | {} |
| source | SourceState | required / non-null | {} |

### RaceMessage

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| text | string | required / non-null | {} |
| issuedAt | real | required / nullable | {"unit": "epochSeconds"} |
| severity | string | required / non-null | {} |

### RacingLiveData

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| source | SourceState | required / non-null | {} |
| active | bool | required / non-null | {} |
| rows | RacingTimingModel | required / non-null | {} |
| messages | RaceMessageModel | required / non-null | {} |
| info | InfoRowModel | required / non-null | {} |

### RacingData

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| source | SourceState | required / non-null | {} |
| kind | string | required / non-null | {"enum": ["f1", "motogp"]} |
| year | int | required / non-null | {"minimum": 1900, "maximum": 9999} |
| events | RacingEventModel | required / non-null | {} |
| standings | StandingModel | required / non-null | {} |
| constructors | StandingModel | required / non-null | {} |
| live | RacingLiveData | required / non-null | {} |
| detailLoading | bool | required / non-null | {} |
| detailError | string | required / non-null | {} |
| partialError | string | required / non-null | {} |

### NotificationEvent

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| id | string | required / non-null | {} |
| revision | string | required / non-null | {} |
| rank | int | required / non-null | {"minimum": 0} |
| category | string | required / non-null | {} |
| severity | string | required / non-null | {} |
| weatherSeverity | string | required / non-null | {} |
| title | string | required / non-null | {} |
| body | string | required / non-null | {} |
| sourceId | string | required / non-null | {} |
| sourceLabel | string | required / non-null | {} |
| issuedAt | real | required / nullable | {"unit": "epochSeconds"} |
| expiresAt | real | required / nullable | {"unit": "epochSeconds"} |
| seen | bool | required / non-null | {} |
| bannerSize | string | required / non-null | {"enum": ["small", "large"]} |
| source | SourceState | required / nullable | {} |

### MotionPolicy

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| mode | string | required / non-null | {"enum": ["normal", "reduced", "off"]} |
| suspended | bool | required / non-null | {} |
| urgent | bool | required / non-null | {} |

### ActorSnapshot

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| actorId | string | required / non-null | {} |
| pose | string | required / non-null | {} |
| locomotion | string | required / non-null | {} |
| sequence | int | required / non-null | {"minimum": 0} |
| paused | bool | required / non-null | {} |
| anchor | Point | required / non-null | {} |
| motionMode | string | required / non-null | {"enum": ["normal", "reduced", "off"]} |

### SceneConfiguration

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| enabled | bool | required / non-null | {} |
| rendererId | string | required / non-null | {} |
| mode | string | required / non-null | {"enum": ["actor", "canvas"]} |

### ThemeStyle

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| background | color | required / non-null | {} |
| backgroundOverlay | color | required / non-null | {} |
| surface | color | required / non-null | {} |
| surfaceFocused | color | required / non-null | {} |
| border | color | required / non-null | {} |
| divider | color | required / non-null | {} |
| textPrimary | color | required / non-null | {} |
| textSecondary | color | required / non-null | {} |
| accent | color | required / non-null | {} |
| bannerSurface | color | required / non-null | {} |
| debugSurface | color | required / non-null | {} |
| demoSurface | color | required / non-null | {} |
| radiusCard | int | required / non-null | {} |
| radiusRow | int | required / non-null | {} |
| radiusPill | int | required / non-null | {} |
| radiusButton | int | required / non-null | {} |
| spacing | int | required / non-null | {} |
| listRows | int | required / non-null | {} |
| borderWidth | int | required / non-null | {} |
| focusWidth | int | required / non-null | {} |
| textScale | real | required / non-null | {} |
| uiFamily | string | required / non-null | {} |
| numbersFamily | string | required / non-null | {} |
| displayFamily | string | required / non-null | {} |
| bodyWeight | int | required / non-null | {} |
| headingWeight | int | required / non-null | {} |
| font18 | int | required / non-null | {} |
| font19 | int | required / non-null | {} |
| font20 | int | required / non-null | {} |
| font21 | int | required / non-null | {} |
| font22 | int | required / non-null | {} |
| font23 | int | required / non-null | {} |
| font24 | int | required / non-null | {} |
| font25 | int | required / non-null | {} |
| font26 | int | required / non-null | {} |
| font27 | int | required / non-null | {} |
| font28 | int | required / non-null | {} |
| font29 | int | required / non-null | {} |
| font30 | int | required / non-null | {} |
| font31 | int | required / non-null | {} |
| font32 | int | required / non-null | {} |
| font33 | int | required / non-null | {} |
| font34 | int | required / non-null | {} |
| font35 | int | required / non-null | {} |
| font36 | int | required / non-null | {} |
| font37 | int | required / non-null | {} |
| font39 | int | required / non-null | {} |
| font40 | int | required / non-null | {} |
| font45 | int | required / non-null | {} |
| font46 | int | required / non-null | {} |
| font47 | int | required / non-null | {} |
| font52 | int | required / non-null | {} |
| font56 | int | required / non-null | {} |
| font65 | int | required / non-null | {} |
| font69 | int | required / non-null | {} |
| font139 | int | required / non-null | {} |
| font152 | int | required / non-null | {} |
| variant | string | required / non-null | {} |
| font44 | int | required / non-null | {} |
| compactRows | int | required / non-null | {} |
| overviewRows | int | required / non-null | {} |
| fantasyRows | int | required / non-null | {} |
| clockWeight | int | required / non-null | {} |
| radiusPanel | int | required / non-null | {} |
| radiusBadge | int | required / non-null | {} |
| radiusDense | int | required / non-null | {} |
| radiusMarker | int | required / non-null | {} |
| hairlineWidth | int | required / non-null | {} |
| semantic | SemanticPalette | required / non-null | {} |

### NotificationStyle

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| background | color | required / non-null | {} |
| backgroundOverlay | color | required / non-null | {} |
| surface | color | required / non-null | {} |
| surfaceFocused | color | required / non-null | {} |
| border | color | required / non-null | {} |
| divider | color | required / non-null | {} |
| textPrimary | color | required / non-null | {} |
| textSecondary | color | required / non-null | {} |
| accent | color | required / non-null | {} |
| bannerSurface | color | required / non-null | {} |
| debugSurface | color | required / non-null | {} |
| demoSurface | color | required / non-null | {} |
| radiusCard | int | required / non-null | {} |
| radiusRow | int | required / non-null | {} |
| radiusPill | int | required / non-null | {} |
| radiusButton | int | required / non-null | {} |
| spacing | int | required / non-null | {} |
| listRows | int | required / non-null | {} |
| borderWidth | int | required / non-null | {} |
| focusWidth | int | required / non-null | {} |
| textScale | real | required / non-null | {} |
| uiFamily | string | required / non-null | {} |
| numbersFamily | string | required / non-null | {} |
| displayFamily | string | required / non-null | {} |
| bodyWeight | int | required / non-null | {} |
| headingWeight | int | required / non-null | {} |
| font18 | int | required / non-null | {} |
| font19 | int | required / non-null | {} |
| font20 | int | required / non-null | {} |
| font21 | int | required / non-null | {} |
| font22 | int | required / non-null | {} |
| font23 | int | required / non-null | {} |
| font24 | int | required / non-null | {} |
| font25 | int | required / non-null | {} |
| font26 | int | required / non-null | {} |
| font27 | int | required / non-null | {} |
| font28 | int | required / non-null | {} |
| font29 | int | required / non-null | {} |
| font30 | int | required / non-null | {} |
| font31 | int | required / non-null | {} |
| font32 | int | required / non-null | {} |
| font33 | int | required / non-null | {} |
| font34 | int | required / non-null | {} |
| font35 | int | required / non-null | {} |
| font36 | int | required / non-null | {} |
| font37 | int | required / non-null | {} |
| font39 | int | required / non-null | {} |
| font40 | int | required / non-null | {} |
| font45 | int | required / non-null | {} |
| font46 | int | required / non-null | {} |
| font47 | int | required / non-null | {} |
| font52 | int | required / non-null | {} |
| font56 | int | required / non-null | {} |
| font65 | int | required / non-null | {} |
| font69 | int | required / non-null | {} |
| font139 | int | required / non-null | {} |
| font152 | int | required / non-null | {} |
| variant | string | required / non-null | {} |
| font44 | int | required / non-null | {} |
| compactRows | int | required / non-null | {} |
| overviewRows | int | required / non-null | {} |
| fantasyRows | int | required / non-null | {} |
| clockWeight | int | required / non-null | {} |
| radiusPanel | int | required / non-null | {} |
| radiusBadge | int | required / non-null | {} |
| radiusDense | int | required / non-null | {} |
| radiusMarker | int | required / non-null | {} |
| hairlineWidth | int | required / non-null | {} |
| semantic | SemanticPalette | required / non-null | {} |
| prefix | string | required / non-null | {} |
| surfaceColor | color | required / non-null | {} |
| noticeFocusedSurface | color | required / non-null | {} |
| titleColor | color | required / non-null | {} |
| bodyColor | color | required / non-null | {} |
| sourceColor | color | required / non-null | {} |
| noticeAccent | color | required / non-null | {} |
| noticeBorder | color | required / non-null | {} |
| noticeRadius | int | required / non-null | {} |
| noticeBorderWidth | int | required / non-null | {} |
| padding | int | required / non-null | {} |
| gap | int | required / non-null | {} |
| panelWidth | int | required / non-null | {} |
| panelHeight | int | required / non-null | {} |
| insetX | int | required / non-null | {} |
| insetY | int | required / non-null | {} |
| anchor | string | required / non-null | {} |
| titleSize | int | required / non-null | {} |
| bodySize | int | required / non-null | {} |
| sourceSize | int | required / non-null | {} |
| guideSize | int | required / non-null | {} |
| titleFamily | string | required / non-null | {} |
| bodyFamily | string | required / non-null | {} |
| sourceFamily | string | required / non-null | {} |
| guideFamily | string | required / non-null | {} |
| titleWeight | int | required / non-null | {} |
| noticeBodyWeight | int | required / non-null | {} |
| titleLines | int | required / non-null | {} |
| bodyLines | int | required / non-null | {} |
| showIcon | bool | required / non-null | {} |
| showSource | bool | required / non-null | {} |
| noticeRows | int | required / non-null | {} |
| layoutY | real | required / non-null | {} |
| mode | string | required / non-null | {"enum": ["small", "large", "urgent", "badge", "inbox", "detail"]} |
| guideColor | color | required / non-null | {} |
| badgeTextColor | color | required / non-null | {} |
| focusedTitleColor | color | required / non-null | {} |
| focusedBodyColor | color | required / non-null | {} |
| focusedSourceColor | color | required / non-null | {} |

### SemanticPalette

| Read-only field | Type | Optional/nullable | Constraints |
| --- | --- | --- | --- |
| accentTextOnCanvas | color | required / non-null | {} |
| accentTextOnOverlay | color | required / non-null | {} |
| accentTextOnCard | color | required / non-null | {} |
| accentTextOnFocused | color | required / non-null | {} |
| warningOnCanvas | color | required / non-null | {} |
| warningOnOverlay | color | required / non-null | {} |
| warningOnCard | color | required / non-null | {} |
| warningOnFocused | color | required / non-null | {} |
| criticalOnCanvas | color | required / non-null | {} |
| criticalOnOverlay | color | required / non-null | {} |
| criticalOnCard | color | required / non-null | {} |
| criticalOnFocused | color | required / non-null | {} |
| accountCriticalOnCanvas | color | required / non-null | {} |
| accountCriticalOnOverlay | color | required / non-null | {} |
| accountCriticalOnCard | color | required / non-null | {} |
| accountCriticalOnFocused | color | required / non-null | {} |

## Models

| Model | Row type | Identity |
| --- | --- | --- |
| CommandModel | Command | id |
| ActionModel | AvailableAction | id |
| TabModel | Tab | id |
| FamilyModel | Family | id |
| MenuRowModel | MenuRow | id |
| SettingRowModel | SettingRow | id |
| SettingOptionModel | SettingOption | id |
| InfoRowModel | InfoRow | id |
| WeatherForecastModel | WeatherForecast | id |
| AccountWindowModel | AccountWindow | id |
| TeamIdentityModel | TeamIdentity | id |
| MatchEventModel | MatchEvent | id |
| MatchStatisticModel | MatchStatistic | id |
| LineupPlayerModel | LineupPlayer | id |
| LineupModel | Lineup | id |
| MatchModel | MatchData | id |
| StandingModel | Standing | id |
| RoundModel | Round | id |
| FantasyBonusModel | FantasyBonus | id |
| FantasyPlayerModel | FantasyPlayer | id |
| FantasyTeamModel | FantasyTeam | id |
| RacingTimingModel | RacingTiming | id |
| PitStopModel | PitStop | id |
| LapTimeModel | LapTime | id |
| StintModel | Stint | id |
| RacingSessionModel | RacingSessionData | id |
| RacingEventModel | RacingEventData | id |
| RaceMessageModel | RaceMessage | id |
| NotificationEventModel | NotificationEvent | id |
| SourceModel | SourceState | sourceId |

## Actions

Shape and per-surface allowlist checks do not authorize an action in the live app.

The A1 broker must also check lifecycle, generation, urgent priority and backend state.

| Action | Target | Required arguments |
| --- | --- | --- |
| navigation.home | optional | {} |
| navigation.back | optional | {} |
| navigation.menu | optional | {} |
| navigation.inbox | optional | {} |
| navigation.family.step | optional | {"direction": {"type": "int", "enum": [-1, 1]}} |
| navigation.view.step | optional | {"direction": {"type": "int", "enum": [-1, 1]}} |
| selection.move | optional | {"direction": {"type": "int", "enum": [-1, 1]}} |
| selection.select | required | {} |
| tabs.select | required | {} |
| details.open | required | {} |
| details.scroll | optional | {"delta": {"type": "real"}} |
| details.refresh | optional | {} |
| settings.activate | required | {} |
| settings.adjust | required | {"direction": {"type": "int", "enum": [-1, 1]}} |
| sources.refresh | required | {} |
| appearance.preview | required | {} |
| appearance.apply | optional | {} |
| appearance.cancel | optional | {} |
| appearance.reset | optional | {} |
| appearance.reload | optional | {} |
| appearance.import | optional | {} |
| appearance.export | optional | {} |
| appearance.notificationPreview | optional | {"mode": {"type": "string", "enum": ["small", "large", "urgent", "badge", "inbox", "detail"]}} |
| openInbox | optional | {} |
| selectEvent | required | {} |
| moveSelection | optional | {"direction": {"type": "int", "enum": [-1, 1]}} |
| openDetails | required | {} |
| scrollDetails | optional | {"delta": {"type": "real"}} |
| dismiss | required | {} |
| back | optional | {} |
| home | optional | {} |
| menu.activate | required | {} |

## Semantic roles

The usage graph is a contract. New foreground resolution and runtime contrast checks require A1/G21.

| Usage | Foreground role | Background token | Minimum | Kind |
| --- | --- | --- | --- | --- |
| accentTextOnCanvas | accentTextOnCanvas | colors.background | 4.5 | text |
| accentTextOnOverlay | accentTextOnOverlay | colors.backgroundOverlay | 4.5 | text |
| accentTextOnCard | accentTextOnCard | colors.surface | 4.5 | text |
| accentTextOnFocused | accentTextOnFocused | colors.surfaceFocused | 4.5 | text |
| warningOnCanvas | warningOnCanvas | colors.background | 4.5 | text |
| warningOnOverlay | warningOnOverlay | colors.backgroundOverlay | 4.5 | text |
| warningOnCard | warningOnCard | colors.surface | 4.5 | text |
| warningOnFocused | warningOnFocused | colors.surfaceFocused | 4.5 | text |
| criticalOnCanvas | criticalOnCanvas | colors.background | 4.5 | text |
| criticalOnOverlay | criticalOnOverlay | colors.backgroundOverlay | 4.5 | text |
| criticalOnCard | criticalOnCard | colors.surface | 4.5 | text |
| criticalOnFocused | criticalOnFocused | colors.surfaceFocused | 4.5 | text |
| accountCriticalOnCanvas | accountCriticalOnCanvas | colors.background | 4.5 | text |
| accountCriticalOnOverlay | accountCriticalOnOverlay | colors.backgroundOverlay | 4.5 | text |
| accountCriticalOnCard | accountCriticalOnCard | colors.surface | 4.5 | text |
| accountCriticalOnFocused | accountCriticalOnFocused | colors.surfaceFocused | 4.5 | text |
| focus-colors.surface | focusIndicator | colors.surface | 3 | indicator |
| focus-colors.surfaceFocused | focusIndicator | colors.surfaceFocused | 3 | indicator |
| focus-colors.backgroundOverlay | focusIndicator | colors.backgroundOverlay | 3 | indicator |
| warningIndicator-urgent | warningIndicator | notifications.urgent.surface | 3 | indicator |
| criticalIndicator-urgent | criticalIndicator | notifications.urgent.surface | 3 | indicator |
| notifications.small.guideColor | notifications.small.guideColor | notifications.small.surface | 4.5 | text |
| notifications.small.badgeTextColor | notifications.small.badgeTextColor | notifications.small.surface | 4.5 | text |
| notifications.small.titleColor | notifications.small.titleColor | notifications.small.surface | 4.5 | text |
| notifications.small.bodyColor | notifications.small.bodyColor | notifications.small.surface | 4.5 | text |
| notifications.small.sourceColor | notifications.small.sourceColor | notifications.small.surface | 4.5 | text |
| notifications.small.focusedTitleColor | notifications.small.focusedTitleColor | notifications.small.surface | 4.5 | text |
| notifications.small.focusedBodyColor | notifications.small.focusedBodyColor | notifications.small.surface | 4.5 | text |
| notifications.small.focusedSourceColor | notifications.small.focusedSourceColor | notifications.small.surface | 4.5 | text |
| notifications.small.focus | focusIndicator | notifications.small.surface | 3 | indicator |
| notifications.large.guideColor | notifications.large.guideColor | notifications.large.surface | 4.5 | text |
| notifications.large.badgeTextColor | notifications.large.badgeTextColor | notifications.large.surface | 4.5 | text |
| notifications.large.titleColor | notifications.large.titleColor | notifications.large.surface | 4.5 | text |
| notifications.large.bodyColor | notifications.large.bodyColor | notifications.large.surface | 4.5 | text |
| notifications.large.sourceColor | notifications.large.sourceColor | notifications.large.surface | 4.5 | text |
| notifications.large.focusedTitleColor | notifications.large.focusedTitleColor | notifications.large.surface | 4.5 | text |
| notifications.large.focusedBodyColor | notifications.large.focusedBodyColor | notifications.large.surface | 4.5 | text |
| notifications.large.focusedSourceColor | notifications.large.focusedSourceColor | notifications.large.surface | 4.5 | text |
| notifications.large.focus | focusIndicator | notifications.large.surface | 3 | indicator |
| notifications.urgent.guideColor | notifications.urgent.guideColor | notifications.urgent.surface | 4.5 | text |
| notifications.urgent.badgeTextColor | notifications.urgent.badgeTextColor | notifications.urgent.surface | 4.5 | text |
| notifications.urgent.titleColor | notifications.urgent.titleColor | notifications.urgent.surface | 4.5 | text |
| notifications.urgent.bodyColor | notifications.urgent.bodyColor | notifications.urgent.surface | 4.5 | text |
| notifications.urgent.sourceColor | notifications.urgent.sourceColor | notifications.urgent.surface | 4.5 | text |
| notifications.urgent.focusedTitleColor | notifications.urgent.focusedTitleColor | notifications.urgent.surface | 4.5 | text |
| notifications.urgent.focusedBodyColor | notifications.urgent.focusedBodyColor | notifications.urgent.surface | 4.5 | text |
| notifications.urgent.focusedSourceColor | notifications.urgent.focusedSourceColor | notifications.urgent.surface | 4.5 | text |
| notifications.urgent.focus | focusIndicator | notifications.urgent.surface | 3 | indicator |
| notifications.badge.guideColor | notifications.badge.guideColor | notifications.badge.surface | 4.5 | text |
| notifications.badge.badgeTextColor | notifications.badge.badgeTextColor | notifications.badge.surface | 4.5 | text |
| notifications.badge.titleColor | notifications.badge.titleColor | notifications.badge.surface | 4.5 | text |
| notifications.badge.bodyColor | notifications.badge.bodyColor | notifications.badge.surface | 4.5 | text |
| notifications.badge.sourceColor | notifications.badge.sourceColor | notifications.badge.surface | 4.5 | text |
| notifications.badge.focusedTitleColor | notifications.badge.focusedTitleColor | notifications.badge.surface | 4.5 | text |
| notifications.badge.focusedBodyColor | notifications.badge.focusedBodyColor | notifications.badge.surface | 4.5 | text |
| notifications.badge.focusedSourceColor | notifications.badge.focusedSourceColor | notifications.badge.surface | 4.5 | text |
| notifications.badge.focus | focusIndicator | notifications.badge.surface | 3 | indicator |
| notifications.inbox.guideColor | notifications.inbox.guideColor | notifications.inbox.surface | 4.5 | text |
| notifications.inbox.badgeTextColor | notifications.inbox.badgeTextColor | notifications.inbox.surface | 4.5 | text |
| notifications.inbox.titleColor | notifications.inbox.titleColor | notifications.inbox.surface | 4.5 | text |
| notifications.inbox.bodyColor | notifications.inbox.bodyColor | notifications.inbox.surface | 4.5 | text |
| notifications.inbox.sourceColor | notifications.inbox.sourceColor | notifications.inbox.surface | 4.5 | text |
| notifications.inbox.focusedTitleColor | notifications.inbox.focusedTitleColor | notifications.inbox.focusedSurface | 4.5 | text |
| notifications.inbox.focusedBodyColor | notifications.inbox.focusedBodyColor | notifications.inbox.focusedSurface | 4.5 | text |
| notifications.inbox.focusedSourceColor | notifications.inbox.focusedSourceColor | notifications.inbox.focusedSurface | 4.5 | text |
| notifications.inbox.focus | focusIndicator | notifications.inbox.focusedSurface | 3 | indicator |
| notifications.detail.guideColor | notifications.detail.guideColor | notifications.detail.surface | 4.5 | text |
| notifications.detail.badgeTextColor | notifications.detail.badgeTextColor | notifications.detail.surface | 4.5 | text |
| notifications.detail.titleColor | notifications.detail.titleColor | notifications.detail.surface | 4.5 | text |
| notifications.detail.bodyColor | notifications.detail.bodyColor | notifications.detail.surface | 4.5 | text |
| notifications.detail.sourceColor | notifications.detail.sourceColor | notifications.detail.surface | 4.5 | text |
| notifications.detail.focusedTitleColor | notifications.detail.focusedTitleColor | notifications.detail.surface | 4.5 | text |
| notifications.detail.focusedBodyColor | notifications.detail.focusedBodyColor | notifications.detail.surface | 4.5 | text |
| notifications.detail.focusedSourceColor | notifications.detail.focusedSourceColor | notifications.detail.surface | 4.5 | text |
| notifications.detail.focus | focusIndicator | notifications.detail.surface | 3 | indicator |
