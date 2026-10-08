import QtQuick
import SmartPC.ThemeApi 2.0

Item {
    id: root
    required property SurfaceContext context
    // Complete mandatory data/commands and lifecycle before allowing readiness.
    readonly property bool ready: false
    readonly property string error: "Renderer da completare dal brief"
    function settleMotion() { /* Stop animations, timers, media; show useful final state. */ }
}
