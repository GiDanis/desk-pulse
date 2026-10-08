import QtQuick
import ".."
import "../themes"

WeatherForecast {
    required property var context
    dashboard: context.controller
    style: context.style
}
