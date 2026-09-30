import QtQuick

Rectangle {
    id: card
    property string heading: ""
    property string value: ""
    property string detail: ""
    property bool compact: false
    property bool night: false
    radius: 13
    color: card.night ? "#14232c" : "#1c2d38"
    border.color: card.night ? "#29424b" : "#35525d"
    border.width: 2
    Text { x: 24; y: 17; text: card.heading; color: card.night ? "#69bfa8" : "#6de0be"; font.pixelSize: 24; font.bold: true }
    Text { x: 24; y: 48; width: parent.width - 48; text: card.value; color: card.night ? "#cddbd8" : "#e9f1ef"; font.pixelSize: card.value.length > 15 && card.width < 600 ? 30 : card.width < 400 ? 34 : card.compact ? 47 : 65; elide: Text.ElideRight }
    Text { x: 24; y: 121; width: parent.width - 48; text: card.detail; color: card.night ? "#93a9ae" : "#b3c2c7"; font.pixelSize: card.compact ? 18 : 20; elide: Text.ElideRight }
}
