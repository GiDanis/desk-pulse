import QtQuick
import QtQuick.Shapes
Item {
    id: root
    required property string iconId
    required property color tint
    width: 32; height: 32
    Shape {
        anchors.fill: parent
        ShapePath {
            strokeColor: root.tint; strokeWidth: 2; fillColor: "transparent"
            PathSvg { path: ({
                "casa.temperature":"M13 6 A3 3 0 0 1 19 6 L19 20 A6 6 0 1 1 13 20 Z M16 12 L16 24 M23 9 L27 9 M23 15 L27 15",
                "casa.plug":"M9 2 L9 10 M23 2 L23 10 M6 10 L26 10 L26 18 Q26 23 20 23 L20 29 L12 29 L12 23 Q6 23 6 18 Z",
                "casa.light":"M8 12 A8 8 0 1 1 24 12 Q24 18 20 20 L20 25 L12 25 L12 20 Q8 18 8 12 M12 29 L20 29",
                "casa.motion":"M16 3 A3 3 0 1 1 16 9 A3 3 0 1 1 16 3 M15 11 L13 20 L7 29 M13 20 L21 29 M15 12 L23 17 M15 12 L7 17"
            })[root.iconId] || "M16 5 A11 11 0 1 1 16 27 A11 11 0 1 1 16 5 M16 10 L16 19 M16 23 L16 24" }
        }
    }
}
