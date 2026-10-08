import QtQuick

QtObject {
    id: styleFacade
    property var appearance: null
    readonly property QtObject semantic: SemanticPaletteFacade { facade: styleFacade }
    property bool fallbackNight: false
    readonly property var fallbackTokens: ({"colors.background":"#101923","colors.backgroundOverlay":"#0b1219","colors.surface":"#1c2d38","colors.surfaceFocused":"#28403f","colors.border":"#35525d","colors.divider":"#31505b","colors.textPrimary":"#e9f1ef","colors.textSecondary":"#b3c2c7","colors.accent":"#6de0be","colors.bannerSurface":"#29423f","colors.debugSurface":"#273e48","colors.demoSurface":"#304750","shape.radiusCard":13,"shape.radiusRow":9,"shape.radiusPill":7,"shape.radiusButton":6,"metrics.spacing":24,"metrics.listRows":4,"metrics.borderWidth":2,"metrics.focusWidth":3,"typography.textScale":1.0,"typography.uiFamily":"","typography.numbersFamily":"","typography.displayFamily":"","typography.bodyWeight":400,"typography.headingWeight":700,"typography.size18":18,"typography.size19":19,"typography.size20":20,"typography.size21":21,"typography.size22":22,"typography.size23":23,"typography.size24":24,"typography.size25":25,"typography.size26":26,"typography.size27":27,"typography.size28":28,"typography.size29":29,"typography.size30":30,"typography.size31":31,"typography.size32":32,"typography.size33":33,"typography.size34":34,"typography.size35":35,"typography.size36":36,"typography.size37":37,"typography.size39":39,"typography.size40":40,"typography.size45":45,"typography.size46":46,"typography.size47":47,"typography.size52":52,"typography.size56":56,"typography.size65":65,"typography.size69":69,"typography.size139":139,"typography.size152":152,"typography.size44":44,"metrics.compactRows":3,"metrics.overviewRows":3,"metrics.fantasyRows":5,"typography.clockWeight":300,"shape.radiusPanel":10,"shape.radiusBadge":8,"shape.radiusDense":5,"shape.radiusMarker":2,"metrics.hairlineWidth":1})
    readonly property var tokenSnapshot: tokens
    readonly property var tokens: appearance ? appearance.tokens : fallbackTokens
    readonly property color background: !appearance && fallbackNight ? "#0b1219" : tokens["colors.background"]
    readonly property color backgroundOverlay: tokens["colors.backgroundOverlay"]
    readonly property color surface: !appearance && fallbackNight ? "#14232c" : tokens["colors.surface"]
    readonly property color surfaceFocused: tokens["colors.surfaceFocused"]
    readonly property color border: !appearance && fallbackNight ? "#29424b" : tokens["colors.border"]
    readonly property color divider: tokens["colors.divider"]
    readonly property color textPrimary: !appearance && fallbackNight ? "#cddbd8" : tokens["colors.textPrimary"]
    readonly property color textSecondary: !appearance && fallbackNight ? "#93a9ae" : tokens["colors.textSecondary"]
    readonly property color accent: !appearance && fallbackNight ? "#69bfa8" : tokens["colors.accent"]
    readonly property color bannerSurface: !appearance && fallbackNight ? "#213735" : tokens["colors.bannerSurface"]
    readonly property color debugSurface: tokens["colors.debugSurface"]
    readonly property color demoSurface: tokens["colors.demoSurface"]
    readonly property int radiusCard: tokens["shape.radiusCard"]
    readonly property int radiusRow: tokens["shape.radiusRow"]
    readonly property int radiusPill: tokens["shape.radiusPill"]
    readonly property int radiusButton: tokens["shape.radiusButton"]
    readonly property int spacing: tokens["metrics.spacing"]
    readonly property int listRows: tokens["metrics.listRows"]
    readonly property int borderWidth: tokens["metrics.borderWidth"]
    readonly property int focusWidth: tokens["metrics.focusWidth"]
    readonly property real textScale: tokens["typography.textScale"]
    readonly property string uiFamily: tokens["typography.uiFamily"] || "DejaVu Sans"
    readonly property string numbersFamily: tokens["typography.numbersFamily"] || "DejaVu Sans"
    readonly property string displayFamily: tokens["typography.displayFamily"] || "DejaVu Sans"
    readonly property int bodyWeight: tokens["typography.bodyWeight"]
    readonly property int headingWeight: tokens["typography.headingWeight"]
    readonly property int font18: Math.round((tokens["typography.size18"]) * textScale)
    readonly property int font19: Math.round((tokens["typography.size19"]) * textScale)
    readonly property int font20: Math.round((tokens["typography.size20"]) * textScale)
    readonly property int font21: Math.round((tokens["typography.size21"]) * textScale)
    readonly property int font22: Math.round((tokens["typography.size22"]) * textScale)
    readonly property int font23: Math.round((tokens["typography.size23"]) * textScale)
    readonly property int font24: Math.round((tokens["typography.size24"]) * textScale)
    readonly property int font25: Math.round((tokens["typography.size25"]) * textScale)
    readonly property int font26: Math.round((tokens["typography.size26"]) * textScale)
    readonly property int font27: Math.round((tokens["typography.size27"]) * textScale)
    readonly property int font28: Math.round((tokens["typography.size28"]) * textScale)
    readonly property int font29: Math.round((tokens["typography.size29"]) * textScale)
    readonly property int font30: Math.round((tokens["typography.size30"]) * textScale)
    readonly property int font31: Math.round((tokens["typography.size31"]) * textScale)
    readonly property int font32: Math.round((tokens["typography.size32"]) * textScale)
    readonly property int font33: Math.round((tokens["typography.size33"]) * textScale)
    readonly property int font34: Math.round((tokens["typography.size34"]) * textScale)
    readonly property int font35: Math.round((tokens["typography.size35"]) * textScale)
    readonly property int font36: Math.round((tokens["typography.size36"]) * textScale)
    readonly property int font37: Math.round((tokens["typography.size37"]) * textScale)
    readonly property int font39: Math.round((tokens["typography.size39"]) * textScale)
    readonly property int font40: Math.round((tokens["typography.size40"]) * textScale)
    readonly property int font45: Math.round((tokens["typography.size45"]) * textScale)
    readonly property int font46: Math.round((tokens["typography.size46"]) * textScale)
    readonly property int font47: Math.round((tokens["typography.size47"]) * textScale)
    readonly property int font52: Math.round((tokens["typography.size52"]) * textScale)
    readonly property int font56: Math.round((tokens["typography.size56"]) * textScale)
    readonly property int font65: Math.round((tokens["typography.size65"]) * textScale)
    readonly property int font69: Math.round((tokens["typography.size69"]) * textScale)
    readonly property int font139: Math.round((tokens["typography.size139"]) * textScale)
    readonly property int font152: Math.round((tokens["typography.size152"]) * textScale)
    readonly property string variant: appearance ? appearance.variant : fallbackNight ? "night" : "day"
    readonly property int font44: Math.round(tokens["typography.size44"] * textScale)
    readonly property int compactRows: tokens["metrics.compactRows"]
    readonly property int overviewRows: tokens["metrics.overviewRows"]
    readonly property int fantasyRows: tokens["metrics.fantasyRows"]
    readonly property int clockWeight: tokens["typography.clockWeight"]
    readonly property int radiusPanel: tokens["shape.radiusPanel"]
    readonly property int radiusBadge: tokens["shape.radiusBadge"]
    readonly property int radiusDense: tokens["shape.radiusDense"]
    readonly property int radiusMarker: tokens["shape.radiusMarker"]
    readonly property int hairlineWidth: tokens["metrics.hairlineWidth"]
    readonly property color accentTextOnCanvas: tokens["semantic.accentTextOnCanvas"] || accent
    readonly property color accentTextOnOverlay: tokens["semantic.accentTextOnOverlay"] || accent
    readonly property color accentTextOnCard: tokens["semantic.accentTextOnCard"] || accent
    readonly property color accentTextOnFocused: tokens["semantic.accentTextOnFocused"] || accent
    readonly property color warningOnCanvas: tokens["semantic.warningOnCanvas"] || "#efbd75"
    readonly property color warningOnOverlay: tokens["semantic.warningOnOverlay"] || "#efbd75"
    readonly property color warningOnCard: tokens["semantic.warningOnCard"] || "#efbd75"
    readonly property color warningOnFocused: tokens["semantic.warningOnFocused"] || "#efbd75"
    readonly property color criticalOnCanvas: tokens["semantic.criticalOnCanvas"] || "#f08779"
    readonly property color criticalOnOverlay: tokens["semantic.criticalOnOverlay"] || "#f08779"
    readonly property color criticalOnCard: tokens["semantic.criticalOnCard"] || "#f08779"
    readonly property color criticalOnFocused: tokens["semantic.criticalOnFocused"] || "#f08779"
    readonly property color accountCriticalOnCanvas: tokens["semantic.accountCriticalOnCanvas"] || "#f28c82"
    readonly property color accountCriticalOnOverlay: tokens["semantic.accountCriticalOnOverlay"] || "#f28c82"
    readonly property color accountCriticalOnCard: tokens["semantic.accountCriticalOnCard"] || "#f28c82"
    readonly property color accountCriticalOnFocused: tokens["semantic.accountCriticalOnFocused"] || "#f28c82"
    readonly property color accentDecoration: tokens["semantic.accentDecoration"] || accent
    readonly property color focusIndicator: tokens["semantic.focusIndicator"] || accent
    readonly property color warningIndicator: tokens["semantic.warningIndicator"] || "#efbd75"
    readonly property color criticalIndicator: tokens["semantic.criticalIndicator"] || "#f08779"
}
