pragma ComponentBehavior: Bound
import QtQuick

Card {
    id: root
    property string title: ""
    property string value: "—"
    property string detail: ""
    property string symbol: ""
    property int valueSize: 36
    readonly property bool compact:height<170
    OutlineIcon { x:18; y:20; opticalSize:28; symbol:root.symbol; tint:root.style ? root.style.semantic.accentTextOnCard : "#0066CC"; visible:!!root.symbol }
    Label { x:root.symbol ? 58 : 18; y:root.compact ? 6 : 12; width:parent.width-x-18; height:root.compact ? 38 : 54; themeStyle:root.style; secondary:true; size:23; text:root.title; maximumLineCount:2 }
    Label { x:18; y:root.compact ? 50 : 70; width:parent.width-36; height:Math.max(1,parent.height-y-(root.detail && !root.compact ? 40 : 10)); themeStyle:root.style; size:root.valueSize; font.family:root.style ? root.style.numbersFamily : "Sans Serif"; font.weight:Font.DemiBold; text:root.value; maximumLineCount:1 }
    Label { x:18; y:parent.height-38; width:parent.width-36; height:30; themeStyle:root.style; secondary:true; size:21; text:root.detail; visible:!!text && !root.compact; maximumLineCount:1 }
}
