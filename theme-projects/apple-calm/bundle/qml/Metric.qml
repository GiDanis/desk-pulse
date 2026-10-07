pragma ComponentBehavior: Bound
import QtQuick

Card {
    id: root
    property string title: ""
    property string value: "—"
    property string detail: ""
    property string symbol: ""
    property int valueSize: 36
    OutlineIcon { x:18; y:20; opticalSize:28; symbol:root.symbol; tint:root.style ? root.style.semantic.accentTextOnCard : "#0066CC"; visible:!!root.symbol }
    Label { x:root.symbol ? 58 : 18; y:12; width:parent.width-x-18; height:42; themeStyle:root.style; secondary:true; size:20; text:root.title; maximumLineCount:1 }
    Label { x:18; y:57; width:parent.width-36; height:parent.height-(root.detail ? 99 : 69); themeStyle:root.style; size:root.valueSize; font.family:root.style ? root.style.numbersFamily : "Sans Serif"; font.weight:Font.DemiBold; text:root.value; maximumLineCount:1 }
    Label { x:18; y:parent.height-38; width:parent.width-36; height:30; themeStyle:root.style; secondary:true; size:18; text:root.detail; visible:!!text; maximumLineCount:1 }
}
