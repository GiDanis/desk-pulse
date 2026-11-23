import QtQuick
import "../../themes"
import "../../components"

Item {
    id: root
    required property var context
    readonly property NotificationStyle style: context.visualStyle
    NotificationText { id: heading; style: root.style; role: "guide"; font.pixelSize: root.context.style.font37; text: root.context.preview ? "ANTEPRIMA DETTAGLIO" : "DETTAGLIO AVVISO" }
    Flickable {
        id: scroll; objectName: "notificationScroll"
        x: root.style.padding; y: heading.height+2*root.style.gap
        width: root.width-2*x; height: Math.max(0,guide.y-root.style.gap-y)
        contentWidth: width; contentHeight: content.height
        contentY: Math.max(0,Math.min(root.context.scrollOffset,contentHeight-height))
        clip: true; boundsBehavior: Flickable.StopAtBounds; interactive: root.context.interactive
        onMovementEnded: root.context.requestAction("scrollDetails","",{offset:contentY})
        Column {
            id: content; width: scroll.width; spacing: root.style.gap
            NotificationText { objectName: "notificationTitle"; style: root.style; role: "title"; width: parent.width; text: root.context.event.title || "" }
            NotificationText { objectName: "notificationBody"; style: root.style; width: parent.width; text: root.context.event.detail || "" }
            NotificationText { objectName: "notificationSource"; style: root.style; role: "source"; visible: root.style.showSource; width: parent.width; text: root.context.sourceText+"\n"+root.context.validityText }
        }
    }
    Binding { target: root.context; property: "scrollMaximum"; value: Math.max(0,scroll.contentHeight-scroll.height) }
    NotificationText { id: guide; objectName: "notificationGuide"; style: root.style; role: "guide"; y: root.height-height-root.style.padding; width: root.width; text: root.context.guideText; maximumLineCount: 1; elide: Text.ElideRight }
}
