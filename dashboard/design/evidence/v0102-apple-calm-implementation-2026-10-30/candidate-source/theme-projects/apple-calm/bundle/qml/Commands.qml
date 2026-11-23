pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.0
import "Format.js" as Format

Item {
    id: root
    required property CommandsContext context
    readonly property var style: context.style
    readonly property bool ready: width > 0 && height > 0
    readonly property bool contentReady: ready
    readonly property string error: ""
    readonly property var mandatoryRegions: [{role:"title",x:32,y:24,width:896,height:60},{role:"body",x:32,y:130,width:896,height:401}]
    function settleMotion() { }
    Rectangle { anchors.fill:parent; color:root.style.backgroundOverlay }
    Label { x:32; y:24; width:896; height:50; themeStyle:root.style; size:34; font.weight:Font.DemiBold; text:"Comandi" }
    Label { x:32; y:79; width:896; height:32; themeStyle:root.style; size:20; secondary:true; text:"Il tastierino segue la schermata attiva"; maximumLineCount:1 }
    Label { x:32; y:150; width:896; height:260; themeStyle:root.style; size:26; secondary:true; text:"Guida comandi non disponibile"; visible:root.context.keyMap.count===0; horizontalAlignment:Text.AlignHCenter }
    Grid {
        x:32; y:130; spacing:16; columns:3
        Repeater {
            model:root.context.keyMap
            delegate: Card {
                id: keyCard
                required property var item
                width:288; height:123; style:root.style
                Label { x:18; y:18; width:52; height:69; themeStyle:root.style; size:40; font.weight:Font.DemiBold; text:String(keyCard.item.key); color:root.style.semantic.accentTextOnCard; maximumLineCount:1 }
                Label { x:82; y:18; width:188; height:69; themeStyle:root.style; size:21; text:keyCard.item.label; maximumLineCount:2 }
            }
        }
    }
}
