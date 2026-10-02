import QtQuick
import "../themes"
QtObject {
    readonly property int apiVersion: 1
    property string contentId: ""
    property var controller: null
    property StyleFacade style: Theme
    property bool active: false
    property bool interactive: false
    property int viewportWidth: 872
    property int viewportHeight: 455
    readonly property string clockText: controller ? controller.timeText() : ""
    readonly property string dateText: controller ? controller.dateText() : ""
    readonly property var model: controller ? ({weather: controller.weather, account: controller.account,
        nextEvent: controller.nextEvent, sport: controller.sport, racing: controller.racing,
        team: controller.teamState, now: controller.now}) : ({})
    readonly property var selection: controller ? ({familyId: controller.familyId, sportId: controller.sportFocusedId,
        teamId: controller.teamFocusedId, racingId: controller.racingFocusedId, fantasyId: controller.fantasyFocusedId,
        view: controller.viewName(), overlay: controller.overlay}) : ({})
    function activate(actionId, argument) {
        if (!interactive || !controller) return false
        if (actionId === "open") controller.activateKey(5)
        else if (actionId === "back") controller.back()
        else if (actionId === "home") controller.home()
        else if (actionId === "move") controller.activateKey(argument)
        else return false
        return true
    }
}
