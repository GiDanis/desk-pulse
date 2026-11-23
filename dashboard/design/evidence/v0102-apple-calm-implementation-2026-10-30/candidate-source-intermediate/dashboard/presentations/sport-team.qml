import QtQuick
import ".."
import "../themes"

SportTeamView {
    required property var context
    dashboard: context.controller
    style: context.style
}
