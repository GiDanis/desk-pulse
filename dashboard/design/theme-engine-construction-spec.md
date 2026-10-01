# Specifiche di Costruzione: Theme Engine di DeskPulse

**Revisione 1.0 · 1 ottobre 2026**  
Documento di architettura software e ingegnerizzazione per la costruzione del **Theme Engine modulare** di DeskPulse / SmartPC (Qt 6 Quick / QML / PySide6 su Allwinner A733 con GPU PowerVR BXM-4-64).

---

## 1. Obiettivi Ingegneristici & Requisiti

La costruzione del Theme Engine deve rispettare 5 vincoli non negoziabili:

1. **Aggiunta di nuovi temi a costo quasi-zero:** Per creare un nuovo tema deve bastare aggiungere un singolo file di circa 40 righe (es. `ProfileCyberdeck.qml`), senza toccare i moduli applicativi (Oggi, Meteo, Sport, Casa, PC) e senza toccare la logica dei comandi da tastierino.
2. **Supporto per modifiche "profonde":** Il motore non deve cambiare solo i colori, ma deve permettere a ciascun tema di modificare **tipografia, gerarchia pesi, raggi degli angoli (da 0 a 18 px), spessori dei bordi e flairs grafici (decorazioni hardware, dot-grid, griglie tecniche)**.
3. **Commutazione istantanea a runtime (Zero-Restart):** Il cambio tema nel menu `9 → Aspetto` deve avvenire a caldo in un singolo frame (~16 ms), preservando lo stato della navigazione, il modulo attivo, la partita o il dato visualizzato.
4. **Zero Overhead prestazionale su GPU PowerVR:** Nessun ricaricamento di componenti pesanti, nessun flickering FBO. Il Scene Graph di Qt Quick deve solo aggiornare i binding di colore e trasformazione a 60 FPS costanti con RAM < 90 MB.
5. **Persistenza affidabile su MicroSD:** Lo stato del tema deve essere salvato tramite `state.py` su `QSettings` in modo atomico, senza usurare la scheda flash con scritture inutili.

---

## 2. Architettura del Motore: Il Pattern "Facade + Strategy"

Invece di un "god-object" monolitico con decine di switch-case ingarbugliati, il Theme Engine adotta il pattern **Facade + Profile Strategy**:

```mermaid
flowchart TD
    subgraph Facade Unica
        TE["Theme.qml (Singleton Facade)"]
    end

    subgraph Profili Pluggabili (Strategy)
        P1["profiles/ProfileBase.qml (Neo-Retro)"]
        P2["profiles/ProfileFunctional.qml (Braun)"]
        P3["profiles/ProfileHardware.qml (Nothing)"]
        P4["profiles/ProfileCozy.qml (Nordic)"]
        P5["profiles/ProfileCyberdeck.qml (Dev Studio)"]
    end

    subgraph Consumatori QML
        C1["InfoCard.qml"]
        C2["HomeNow.qml"]
        C3["SportOverlay.qml"]
        C4["SettingsPanel.qml"]
        C5["DashboardOverlay.qml"]
    end

    TE -->|"currentProfile"| P1
    TE -.->|"selezionabile"| P2
    TE -.->|"selezionabile"| P3
    TE -.->|"selezionabile"| P4
    TE -.->|"selezionabile"| P5

    C1 -->|"Theme.surface"| TE
    C2 -->|"Theme.textPrimary"| TE
    C3 -->|"Theme.surfaceFocused"| TE
    C4 -->|"Theme.radiusCard"| TE
    C5 -->|"Theme.divider"| TE
```

### Perché questa struttura vince?
* **Disaccoppiamento totale:** I componenti dell'interfaccia (`InfoCard`, `WeatherNow`, `SportView`) dialogano **solo ed esclusivamente con `Theme.proprietà`**. Non sanno quale tema sia attivo.
* **Profili isolati:** Ogni profilo è un `QtObject` snello che esporta lo stesso contratto di proprietà. Modificare o creare un tema non rischia di rompere gli altri.
* **Attenuazione Notte integrata per tema:** Ogni profilo decide autonomamente come comportarsi di notte. Ad esempio, il profilo *Functional* di notte attenua i bianchi senza toccare il fondo nero, mentre il profilo *Base* scurisce la superficie e attenua il verde acqua.

---

## 3. Struttura del File System

```text
dashboard/
  ├── themes/
  │    ├── qmldir                     # Registrazione singleton per il motore QML
  │    ├── Theme.qml                  # Facade centrale con fallback sicuri
  │    └── profiles/
  │         ├── ProfileBase.qml        # Tema 1: Neo-Retro sobrio (Default)
  │         ├── ProfileFunctional.qml  # Tema 2: Braun / Dieter Rams Bauhaus
  │         ├── ProfileHardware.qml    # Tema 3: Nothing / Teenage Engineering
  │         ├── ProfileCozy.qml        # Tema 4: Nordic Companion & Mascotte
  │         └── ProfileCyberdeck.qml   # Tema 5: Dev Studio & Telemetria
  └── fonts/
       ├── fonts.qrc                  # Compilazione risorse o caricamento locale
       ├── Inter-Regular.ttf          # Testo e microcopy ad alta densità (330 PPI)
       ├── Inter-SemiBold.ttf         # Titoli card e pulsanti
       └── JetBrainsMono-Bold.ttf     # Cifre tabulari orologio, statistiche e quote
```

---

## 4. Il Contratto Semantico Completo dei Token

Tutti i profili implementano la seguente specifica di token, suddivisa in 5 categorie funzionali:

### A. Superfici & Sfondi (Surfaces)
| Token | Tipo | Descrizione semantica |
| :--- | :--- | :--- |
| `background` | `color` | Sfondo generale a tutto schermo dell'applicazione |
| `backgroundOverlay` | `color` | Sfondo modale per menu, impostazioni e popup |
| `surface` | `color` | Superficie normale a riposo per card e pannelli |
| `surfaceAlt` | `color` | Superficie interna di contrasto per tabelle o sottoblocchi |
| `surfaceFocused` | `color` | Sfondo della riga, card o tab che ha attualmente il focus da tastierino |
| `surfacePressed` | `color` | Micro-stato transitorio di conferma tasto OK (`5`) |

### B. Confini, Bordi & Geometrie (Borders & Shapes)
| Token | Tipo | Descrizione semantica |
| :--- | :--- | :--- |
| `border` | `color` | Bordo discreto delle card a riposo |
| `borderFocused` | `color` | Bordo ad altissimo contrasto per l'elemento con focus |
| `divider` | `color` | Linea orizzontale o verticale millimetrica di separazione |
| `borderWidth` | `int` | Spessore del bordo a riposo (1 o 2 px) |
| `borderWidthFocused`| `int` | Spessore del bordo con focus attivo (2 o 3 px) |
| `radiusCard` | `int` | Raggio di curvatura delle schede dati (da 2 px in Braun a 18 px in Cozy) |
| `radiusPill` | `int` | Raggio per badge, tag di stato e indicatori |
| `radiusButton` | `int` | Raggio per selettori e righe di menu |

### C. Tipografia & Gerarchia Dimensionale
| Token | Tipo | Descrizione semantica |
| :--- | :--- | :--- |
| `fontFamilyBody` | `string` | Nome famiglia per testi, titoli e menu (es. `"Inter"`) |
| `fontFamilyNumbers`| `string` | Nome famiglia a spaziatura tabulare fissa per orologi e statistiche |
| `fontHeroSize` | `int` | Dimensione orologio Home (144–156 px tabulare) |
| `fontTitleSize` | `int` | Intestazione principale di modulo (32–36 px) |
| `fontHeadingSize` | `int` | Titolo card e indicatori turno (24–26 px) |
| `fontBodySize` | `int` | Testo primario, valori meteo e punteggi (20–22 px) |
| `fontCaptionSize` | `int` | Microtesti, timestamp e note di stato (17–19 px) |

### D. Colori dei Testi & Ruoli di Stato
| Token | Tipo | Descrizione semantica |
| :--- | :--- | :--- |
| `textPrimary` | `color` | Testo dominante ad alto contrasto (WCAG > 7:1) |
| `textSecondary` | `color` | Testo descrittivo secondario (WCAG > 4.5:1) |
| `textMuted` | `color` | Testo de-enfatizzato, unità di misura fisse e etichette tasti |
| `accent` | `color` | Colore identitario del tema (verde acqua, giallo ambra, rosso Nothing) |
| `warning` | `color` | Indicatore di dato salvato/offline, ritardo, allerta gialla |
| `critical` | `color` | Errore critico, quota AI oltre il 95%, allerta meteo rossa |
| `liveStatus` | `color` | Indicatore pulsante di partita in corso o telemetria attiva |

### E. Dinamica & Flairs Specifici (Personalità)
| Token | Tipo | Descrizione semantica |
| :--- | :--- | :--- |
| `motionDuration` | `int` | Durata animazioni di transizione (0 ms se disattivate, 160–180 ms normale) |
| `showHardwareAccents` | `bool` | Se `true`, disegna viti o indicatori tecnici serigrafati (tema Hardware) |
| `showTelemetryBadge` | `bool` | Se `true`, mostra header compatto con CPU/FPS (tema Cyberdeck) |
| `companionVisible` | `bool` | Se la mascotte ha spazio visivo nella Home (tema Cozy) |

---

## 5. Implementazione del Codice di Riferimento

### 1. `dashboard/themes/qmldir`
```text
singleton Theme 1.0 Theme.qml
```

### 2. `dashboard/themes/Theme.qml` (Facade Centrale)
```qml
pragma Singleton
import QtQuick
import "profiles"

QtObject {
    id: root

    // Stato controllato dal backend Python
    property string activeProfile: "base"
    property bool isNight: false
    property bool animationsEnabled: true

    // Metadati dei profili per il menu Impostazioni
    readonly property var availableProfiles: [
        { id: "base",       name: "Neo-Retro Base", detail: "Sobrio · verde acqua e navy scuro" },
        { id: "functional", name: "Braun Functional", detail: "Bauhaus · contrasto puro e giallo ambra" },
        { id: "hardware",   name: "Nothing Hardware", detail: "Dot-matrix · accenti rosso vermiglio" },
        { id: "cozy",       name: "Nordic Companion", detail: "Toni pastello caldi e compagno animato" },
        { id: "cyberdeck",  name: "Dev Cyberdeck", detail: "Fosforo verde e telemetria studio" }
    ]

    // Istanze dei singoli profili
    readonly property ProfileBase profileBase: ProfileBase { isNight: root.isNight }
    readonly property ProfileFunctional profileFunctional: ProfileFunctional { isNight: root.isNight }
    readonly property ProfileHardware profileHardware: ProfileHardware { isNight: root.isNight }
    readonly property ProfileCozy profileCozy: ProfileCozy { isNight: root.isNight }
    readonly property ProfileCyberdeck profileCyberdeck: ProfileCyberdeck { isNight: root.isNight }

    // Risoluzione dinamica del profilo attivo
    readonly property var current: {
        if (activeProfile === "functional") return profileFunctional
        if (activeProfile === "hardware")   return profileHardware
        if (activeProfile === "cozy")       return profileCozy
        if (activeProfile === "cyberdeck")  return profileCyberdeck
        return profileBase
    }

    // Proxy trasparente delle proprietà verso l'esterno
    readonly property color background:         current.background
    readonly property color backgroundOverlay:  current.backgroundOverlay
    readonly property color surface:            current.surface
    readonly property color surfaceAlt:         current.surfaceAlt
    readonly property color surfaceFocused:     current.surfaceFocused
    readonly property color surfacePressed:     current.surfacePressed

    readonly property color border:             current.border
    readonly property color borderFocused:     current.borderFocused
    readonly property color divider:            current.divider
    readonly property int borderWidth:          current.borderWidth
    readonly property int borderWidthFocused:  current.borderWidthFocused
    readonly property int radiusCard:           current.radiusCard
    readonly property int radiusPill:           current.radiusPill
    readonly property int radiusButton:         current.radiusButton

    readonly property color textPrimary:        current.textPrimary
    readonly property color textSecondary:      current.textSecondary
    readonly property color textMuted:          current.textMuted
    readonly property color accent:             current.accent
    readonly property color warning:            current.warning
    readonly property color critical:           current.critical
    readonly property color liveStatus:         current.liveStatus

    readonly property string fontFamilyBody:    fontBodyLoader.status === FontLoader.Ready ? fontBodyLoader.name : "sans-serif"
    readonly property string fontFamilyNumbers: fontNumbersLoader.status === FontLoader.Ready ? fontNumbersLoader.name : "monospace"

    readonly property int fontHeroSize:         152
    readonly property int fontTitleSize:        35
    readonly property int fontHeadingSize:      24
    readonly property int fontBodySize:         21
    readonly property int fontCaptionSize:      18

    readonly property int motionDuration:       animationsEnabled ? current.motionDuration : 0
    readonly property bool showHardwareAccents: current.showHardwareAccents
    readonly property bool showTelemetryBadge:  current.showTelemetryBadge
    readonly property bool companionVisible:    current.companionVisible

    // Caricamento sicuro dei font locali con fallback dichiarato
    FontLoader { id: fontBodyLoader; source: "qrc:/fonts/Inter-Regular.ttf" }
    FontLoader { id: fontNumbersLoader; source: "qrc:/fonts/JetBrainsMono-Bold.ttf" }
}
```

### 3. Esempio Profilo 1: `dashboard/themes/profiles/ProfileBase.qml`
```qml
import QtQuick

QtObject {
    required property bool isNight

    readonly property color background:        isNight ? "#0b1219" : "#101923"
    readonly property color backgroundOverlay: "#0b1219"
    readonly property color surface:           isNight ? "#14232c" : "#1c2d38"
    readonly property color surfaceAlt:        isNight ? "#1b2c36" : "#243743"
    readonly property color surfaceFocused:    "#28403f"
    readonly property color surfacePressed:    "#31504e"

    readonly property color border:            isNight ? "#29424b" : "#35525d"
    readonly property color borderFocused:    isNight ? "#69bfa8" : "#6de0be"
    readonly property color divider:           "#31505b"
    readonly property int borderWidth:         2
    readonly property int borderWidthFocused: 2
    readonly property int radiusCard:          13
    readonly property int radiusPill:          16
    readonly property int radiusButton:        8

    readonly property color textPrimary:       isNight ? "#cddbd8" : "#e9f1ef"
    readonly property color textSecondary:     isNight ? "#93a9ae" : "#b3c2c7"
    readonly property color textMuted:         isNight ? "#5c747c" : "#728a92"
    readonly property color accent:            isNight ? "#69bfa8" : "#6de0be"
    readonly property color warning:           "#efbd75"
    readonly property color critical:          "#f08779"
    readonly property color liveStatus:        "#6de0be"

    readonly property int motionDuration:      180
    readonly property bool showHardwareAccents: false
    readonly property bool showTelemetryBadge: false
    readonly property bool companionVisible:   false
}
```

### 4. Esempio Profilo 2: `dashboard/themes/profiles/ProfileFunctional.qml` (Braun Bauhaus)
```qml
import QtQuick

QtObject {
    required property bool isNight

    // Minimalismo rigoroso, angoli quasi retti, accento ambra Braun
    readonly property color background:        "#151515"
    readonly property color backgroundOverlay: "#101010"
    readonly property color surface:           isNight ? "#1e1e1e" : "#242424"
    readonly property color surfaceAlt:        "#2c2c2c"
    readonly property color surfaceFocused:    "#383838"
    readonly property color surfacePressed:    "#444444"

    readonly property color border:            "#333333"
    readonly property color borderFocused:    "#f5a623"
    readonly property color divider:           "#3d3d3d"
    readonly property int borderWidth:         1
    readonly property int borderWidthFocused: 2
    readonly property int radiusCard:          3   // Angolo quasi retto Dieter Rams
    readonly property int radiusPill:          4
    readonly property int radiusButton:        2

    readonly property color textPrimary:       isNight ? "#d8d8d6" : "#f0f0ee"
    readonly property color textSecondary:     isNight ? "#8c8c8a" : "#a0a09e"
    readonly property color textMuted:         "#666664"
    readonly property color accent:            "#f5a623" // Giallo ambra iconico Braun
    readonly property color warning:           "#e09b30"
    readonly property color critical:          "#d9534f"
    readonly property color liveStatus:        "#f5a623"

    readonly property int motionDuration:      120 // Transizioni più secche e scattanti
    readonly property bool showHardwareAccents: false
    readonly property bool showTelemetryBadge: false
    readonly property bool companionVisible:   false
}
```

---

## 6. Come si collegano i Componenti Esistenti

Dopo l'introduzione di `Theme.qml`, la modifica dei componenti QML esistenti diventa immediata e naturale:

### Prima (Hardcoded):
```qml
// InfoCard.qml
Rectangle {
    color: card.night ? "#14232c" : "#1c2d38"
    border.color: card.night ? "#29424b" : "#35525d"
    radius: 13
    Text { text: card.heading; color: card.night ? "#69bfa8" : "#6de0be" }
}
```

### Dopo (Tokenizzato con Theme Engine):
```qml
// InfoCard.qml
import QtQuick
import "themes"

Rectangle {
    color: Theme.surface
    border.color: Theme.border
    border.width: Theme.borderWidth
    radius: Theme.radiusCard
    Text { 
        text: card.heading
        color: Theme.accent
        font.family: Theme.fontFamilyBody
        font.pixelSize: Theme.fontHeadingSize
    }
}
```

---

## 7. Integrazione con Python (`state.py`)

In [`dashboard/state.py`](file:///home/giuseppe/Documenti/Workspace/SmartPC/dashboard/state.py), aggiungiamo la gestione della preferenza persistente:

```python
# In __init__:
self._active_theme: str = str(self._settings.value("activeTheme", "base"))

# Signal e Property:
activeThemeChanged = Signal(str)

@Property(str, notify=activeThemeChanged)
def activeTheme(self) -> str:
    return self._active_theme

@Slot(str)
def setActiveTheme(self, theme_id: str) -> None:
    valid_themes = {"base", "functional", "hardware", "cozy", "cyberdeck"}
    if theme_id not in valid_themes:
        theme_id = "base"
    if theme_id != self._active_theme:
        self._active_theme = theme_id
        self._settings.setValue("activeTheme", theme_id)
        self._settings.sync()
        self.activeThemeChanged.emit(theme_id)
```

In [`dashboard/Main.qml`](file:///home/giuseppe/Documenti/Workspace/SmartPC/dashboard/Main.qml):
```qml
import "themes"

Window {
    id: app
    // Sincronizzazione automatica bidirezionale
    Binding { target: Theme; property: "activeProfile"; value: dashboardState ? dashboardState.activeTheme : "base" }
    Binding { target: Theme; property: "isNight"; value: app.night }
    Binding { target: Theme; property: "animationsEnabled"; value: dashboardState ? dashboardState.animationsEnabled : true }
    
    color: Theme.background
    // ...
}
```

---

## 8. Piano di Collaudo & Metriche di Accettazione

| Test | Metodo di verifica | Criterio di successo |
| :--- | :--- | :--- |
| **Avvio e Fallback** | Avviare con tema inesistente (`activeTheme: "alien"`) | Ricade silenziosamente su `base` senza errori QML |
| **Commutazione a caldo** | Cambiare da Base a Functional dal menu `Aspetto` | Cambio colore e raggi in < 20 ms senza riavvio della finestra |
| **Test automatici esistenti** | Eseguire `python3 dashboard/check_dashboard.py` | 100% test superati senza rottura dei contratti |
| **Test Sport & Motorsport** | Eseguire `python3 dashboard/check_sport_ui.py` | Interfaccia sport funzionante con i nuovi token |
| **FPS e Memoria (Board)** | Eseguire `benchmark.py` sull'Orange Pi Zero 3W | 60 FPS stabili durante lo scorrimento, RAM < 90 MB |
