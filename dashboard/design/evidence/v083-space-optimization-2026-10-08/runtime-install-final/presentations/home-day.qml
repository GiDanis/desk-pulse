import QtQuick
import ".."
import "../themes"

HomeDay {
    required property var context
    dashboard: context.controller
    style: context.style
}
