import QtQuick
import "themes"
import "components"

Item {
    id: visualRoot
    property StyleFacade style: Theme
    required property var dashboard
    property bool large: false
    property var renderedEvent: ({})
    readonly property var liveEvent: dashboard.bannerEvent
    onLiveEventChanged: if (liveEvent.id && (liveEvent.bannerSize === "large") === large) renderedEvent = liveEvent
    Component.onCompleted: if (liveEvent.id && (liveEvent.bannerSize === "large") === large) renderedEvent = liveEvent
    objectName: "eventBanner"
    x: 44; y: large ? 106 : 459; width: 872; height: large ? 446 : 93

    Rectangle {
        visible: parent.large
        x: -44; y: -16; width: 960; height: 462
        color: dashboard.color
    }

    Rectangle {
        anchors.fill: parent
        radius: visualRoot.style.radiusPanel
        color: visualRoot.style.bannerSurface
        border.color: visualRoot.style.accent
        border.width: visualRoot.style.focusWidth
    }
    AppText { style: visualRoot.style;
        visible: parent.large
        x: 26; y: 21; width: 820
        text: "AVVISO"
        color: visualRoot.style.accent; font.pixelSize: visualRoot.style.font25; font.weight: (true) ? visualRoot.style.headingWeight : visualRoot.style.bodyWeight
    }
    AppText { style: visualRoot.style;
        id: bannerTitle
        x: parent.large ? 26 : 21; y: parent.large ? 69 : 11
        width: parent.large ? 820 : 660
        text: renderedEvent.title || ""
        color: visualRoot.style.textPrimary; font.pixelSize: parent.large ? visualRoot.style.font44 : visualRoot.style.font29; font.weight: (true) ? visualRoot.style.headingWeight : visualRoot.style.bodyWeight
        wrapMode: parent.large ? Text.WordWrap : Text.NoWrap
        maximumLineCount: parent.large ? 2 : 1
        elide: Text.ElideRight
    }
    AppText { style: visualRoot.style;
        x: parent.large ? 26 : 22
        y: parent.large ? bannerTitle.y + bannerTitle.height + 20 : 52
        width: parent.large ? 820 : 720
        text: renderedEvent.detail || ""
        color: visualRoot.style.textSecondary; font.pixelSize: parent.large ? visualRoot.style.font30 : visualRoot.style.font21
        wrapMode: parent.large ? Text.WordWrap : Text.NoWrap
        maximumLineCount: parent.large ? 3 : 1
        elide: Text.ElideRight
    }
    AppText { style: visualRoot.style;
        visible: parent.large
        x: 26; y: parent.height - 91; width: 820
        text: "Fonte: " + (renderedEvent.sourceLabel || renderedEvent.source || "") +
              " · Emesso " + dashboard.eventStamp(renderedEvent.issuedAt)
        color: visualRoot.style.textSecondary; font.pixelSize: visualRoot.style.font22
        elide: Text.ElideRight
    }
    AppText { style: visualRoot.style;
        x: parent.large ? 26 : 735; y: parent.large ? parent.height - 48 : 27
        width: parent.large ? 820 : 118
        text: "3 AVVISI"
        color: visualRoot.style.accent; font.pixelSize: parent.large ? visualRoot.style.font25 : visualRoot.style.font20; font.weight: (true) ? visualRoot.style.headingWeight : visualRoot.style.bodyWeight
        horizontalAlignment: parent.large ? Text.AlignLeft : Text.AlignRight
    }
}
