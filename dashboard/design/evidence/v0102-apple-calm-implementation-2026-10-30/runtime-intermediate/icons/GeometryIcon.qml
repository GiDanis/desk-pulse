import QtQuick
import QtQuick.Shapes
import "../themes"
import "AdditionalPaths.js" as Additional
Item {
    id: root
    property StyleFacade style: Theme
    property string iconId: "status.unavailable"
    property var descriptor: null
    property string symbol: "unknown"
    property color tint: style.accent
    property int opticalSize: 32
    width: opticalSize; height: opticalSize
    Shape {
        anchors.fill: parent
        scale: root.opticalSize/32; transformOrigin: Item.TopLeft
        ShapePath {
            strokeColor: root.tint; strokeWidth: 2; fillColor: "transparent"
            PathSvg { path: Additional.paths[root.symbol] || ({home:"M4 14 L16 4 L28 14 M7 12 L7 28 L25 28 L25 12 M13 28 L13 19 L19 19 L19 28",back:"M22 5 L10 16 L22 27",alerts:"M16 3 L30 28 L2 28 Z M16 11 L16 19 M16 23 L16 25",clear:"M24 16 A8 8 0 1 1 8 16 A8 8 0 1 1 24 16 M16 1 L16 5 M16 27 L16 31 M1 16 L5 16 M27 16 L31 16 M5 5 L8 8 M24 24 L27 27 M5 27 L8 24 M24 8 L27 5",cloudy:"M7 24 C0 24 1 15 7 15 C6 5 24 4 25 15 C32 14 32 24 25 24 Z",rain:"M5 21 C0 21 1 13 7 13 C7 4 24 4 25 13 C31 13 31 21 25 21 Z M10 24 L8 30 M19 24 L17 30 M27 24 L25 30",snow:"M16 3 L16 29 M4 9 L28 23 M4 23 L28 9 M12 5 L16 9 L20 5 M12 27 L16 23 L20 27",fog:"M3 8 L29 8 M7 16 L25 16 M3 24 L29 24",storm:"M3 17 C0 9 10 4 16 9 C22 2 33 9 29 17 M19 12 L10 22 L18 22 L13 31",star:"M16 3 L20 12 L30 13 L22 20 L25 30 L16 24 L7 30 L10 20 L2 13 L12 12 Z",settings:"M16 4 L20 4 L22 9 L27 11 L28 16 L27 21 L22 23 L20 28 L12 28 L10 23 L5 21 L4 16 L5 11 L10 9 L12 4 Z M21 16 A5 5 0 1 1 11 16 A5 5 0 1 1 21 16",offline:"M5 5 L27 27 M5 14 Q16 2 27 14 M10 19 Q16 12 22 19 M15 25 L17 25",stale:"M28 16 A12 12 0 1 1 16 4 M16 7 L16 16 L23 16 M16 4 L23 4 L23 11",temperature:"M13 6 A3 3 0 0 1 19 6 L19 20 A6 6 0 1 1 13 20 Z M16 12 L16 24",plug:"M9 2 L9 10 M23 2 L23 10 M6 10 L26 10 L26 18 Q26 23 20 23 L20 29 L12 29 L12 23 Q6 23 6 18 Z",light:"M8 12 A8 8 0 1 1 24 12 Q24 18 20 20 L20 25 L12 25 L12 20 Q8 18 8 12 M12 29 L20 29",motion:"M16 3 A3 3 0 1 1 16 9 A3 3 0 1 1 16 3 M15 11 L13 20 L7 29 M13 20 L21 29 M15 12 L23 17 M15 12 L7 17",unknown:"M11 11 C11 3 25 3 23 13 L17 18 L17 22 M17 26 L17 28"})[root.symbol] || "M11 11 C11 3 25 3 23 13 L17 18 L17 22 M17 26 L17 28" }
        }
    }
}
