import QtQuick
import ".."
import "../themes"

WeatherNow {
    required property var context
    dashboard: context.controller
    style: context.style
}
