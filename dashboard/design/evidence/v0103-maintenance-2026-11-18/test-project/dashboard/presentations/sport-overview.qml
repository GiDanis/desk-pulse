import QtQuick
import ".."
import "../themes"

SportView {
    required property var context
    dashboard: context.controller
    style: context.style
}
