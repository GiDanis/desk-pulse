import QtQuick
import ".."
import "../themes"

HomeNow {
    required property var context
    dashboard: context.controller
    style: context.style
}
