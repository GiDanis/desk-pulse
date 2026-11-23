import QtQuick
QtObject {
    required property var facade
    readonly property color accentTextOnCanvas: facade.accentTextOnCanvas
    readonly property color accentTextOnOverlay: facade.accentTextOnOverlay
    readonly property color accentTextOnCard: facade.accentTextOnCard
    readonly property color accentTextOnFocused: facade.accentTextOnFocused
    readonly property color warningOnCanvas: facade.warningOnCanvas
    readonly property color warningOnOverlay: facade.warningOnOverlay
    readonly property color warningOnCard: facade.warningOnCard
    readonly property color warningOnFocused: facade.warningOnFocused
    readonly property color criticalOnCanvas: facade.criticalOnCanvas
    readonly property color criticalOnOverlay: facade.criticalOnOverlay
    readonly property color criticalOnCard: facade.criticalOnCard
    readonly property color criticalOnFocused: facade.criticalOnFocused
    readonly property color accountCriticalOnCanvas: facade.accountCriticalOnCanvas
    readonly property color accountCriticalOnOverlay: facade.accountCriticalOnOverlay
    readonly property color accountCriticalOnCard: facade.accountCriticalOnCard
    readonly property color accountCriticalOnFocused: facade.accountCriticalOnFocused
    readonly property color accentDecoration: facade.accentDecoration
    readonly property color focusIndicator: facade.focusIndicator
    readonly property color warningIndicator: facade.warningIndicator
    readonly property color criticalIndicator: facade.criticalIndicator
}
