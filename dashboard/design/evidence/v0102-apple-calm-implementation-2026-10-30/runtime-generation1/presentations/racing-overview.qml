import QtQuick
import ".."
import "../themes"

MotorsportView {
    required property var context
    dashboard: context.controller
    style: context.style
}
