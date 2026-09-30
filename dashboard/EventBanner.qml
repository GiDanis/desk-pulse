import QtQuick

Item {
    required property var dashboard
    property bool large: false
    objectName: "eventBanner"
    x: 44; y: large ? 106 : 459; width: 872; height: large ? 446 : 93

    Rectangle {
        visible: parent.large
        x: -44; y: -16; width: 960; height: 462
        color: dashboard.color
    }

    Rectangle {
        anchors.fill: parent
        radius: 10
        color: "#29423f"
        border.color: dashboard.accent
        border.width: 3
    }
    Text {
        visible: parent.large
        x: 26; y: 21; width: 820
        text: "AVVISO"
        color: dashboard.accent; font.pixelSize: 25; font.bold: true
    }
    Text {
        id: bannerTitle
        x: parent.large ? 26 : 21; y: parent.large ? 69 : 11
        width: parent.large ? 820 : 660
        text: dashboard.bannerEvent.title || ""
        color: dashboard.ink; font.pixelSize: parent.large ? 44 : 29; font.bold: true
        wrapMode: parent.large ? Text.WordWrap : Text.NoWrap
        maximumLineCount: parent.large ? 2 : 1
        elide: Text.ElideRight
    }
    Text {
        x: parent.large ? 26 : 22
        y: parent.large ? bannerTitle.y + bannerTitle.height + 20 : 52
        width: parent.large ? 820 : 720
        text: dashboard.bannerEvent.detail || ""
        color: dashboard.muted; font.pixelSize: parent.large ? 30 : 21
        wrapMode: parent.large ? Text.WordWrap : Text.NoWrap
        maximumLineCount: parent.large ? 3 : 1
        elide: Text.ElideRight
    }
    Text {
        visible: parent.large
        x: 26; y: parent.height - 91; width: 820
        text: "Fonte: " + (dashboard.bannerEvent.sourceLabel || dashboard.bannerEvent.source || "") +
              " · Emesso " + dashboard.eventStamp(dashboard.bannerEvent.issuedAt)
        color: dashboard.muted; font.pixelSize: 22
        elide: Text.ElideRight
    }
    Text {
        x: parent.large ? 26 : 735; y: parent.large ? parent.height - 48 : 27
        width: parent.large ? 820 : 118
        text: "3 AVVISI"
        color: dashboard.accent; font.pixelSize: parent.large ? 25 : 20; font.bold: true
        horizontalAlignment: parent.large ? Text.AlignLeft : Text.AlignRight
    }
}
