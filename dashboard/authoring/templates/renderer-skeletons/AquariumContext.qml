import QtQuick
import SmartPC.ThemeApi 2.13

Item {
    id: root
    required property AquariumContext context
    // The application owns playback, safeArea, urgency and motion policy.
    // Render local assets from context.aquarium without provider I/O or timers
    // that continue when lifecycle.active is false. Never publish poses to Python.
    readonly property bool ready: false
    readonly property string error: "Renderer Acquario da completare dal brief"
    function settleMotion() { /* Stop the single scene clock and retain its pose. */ }
}
