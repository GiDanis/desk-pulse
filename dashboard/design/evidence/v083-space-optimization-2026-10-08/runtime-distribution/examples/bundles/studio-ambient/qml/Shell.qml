import QtQuick
import SmartPC.ThemeApi 2.0

Item {
    id: root
    required property ShellContext context
    readonly property bool ready: heading.text.length > 0
    readonly property bool contentReady: ready
    readonly property string error: ""
    function settleMotion() { }
    Rectangle { x: 0; y: 0; width: parent.width; height: 7; color: root.context.style.accent }
    Text { id: heading; x: 44; y: 28; width: parent.width - 280; text: root.context.currentFamilyId.toUpperCase() + " / " + root.context.currentViewId; color: root.context.style.semantic.accentTextOnCanvas; font.family: root.context.style.uiFamily; font.pixelSize: 29; font.weight: Font.Medium; maximumLineCount: 1; elide: Text.ElideRight }
    Text { x: parent.width - 205; y: 35; width: 160; text: root.context.uiStatus.quiet ? "QUIETE" : root.context.uiStatus.night ? "NOTTE" : "SMARTPC"; color: root.context.style.textSecondary; font.family: root.context.style.uiFamily; font.pixelSize: 20; horizontalAlignment: Text.AlignRight }
}
