import QtQuick

Item {
    id: root
    required property var ctx
    readonly property bool ready: !!ctx
    readonly property var visual: ctx.style
    readonly property var g: ctx.game
    readonly property bool overlay: ctx.contentId === "game.driver.details"
    readonly property real factor: visual.textScale
    readonly property var rows: ctx.rows || []
    readonly property int selected: ctx.selectedIndex || 0
    readonly property int pageSize: 3
    function action(id) { if (ctx.lifecycle.interactive) ctx.requestAction("game.option.activate",id,{}) }
    Rectangle { anchors.fill:parent;visible:root.overlay;color:root.visual.background }
    Item {
        anchors.fill:parent;anchors.margins:root.overlay ? 32 : 0
        Text { objectName:"pilotHeading";x:0;y:4;width:parent.width;height:46;text:root.g.selectedDriverName || "PILOTA";font.family:root.visual.uiFamily;font.pixelSize:30*root.factor;color:root.visual.textPrimary;elide:Text.ElideRight;verticalAlignment:Text.AlignVCenter }
        Row {
            x:0;y:65;spacing:24
            Repeater { model:root.ctx.section==="reset" ? [{id:"reset",label:"Gestisci apprendimento"}] : [{id:"summary",label:"Sintesi"},{id:"parameters",label:"Metodo"},{id:"history",label:"Storico"},{id:"results",label:"Risultati"}]
                delegate:Text {
                    required property var modelData
                    text:modelData.label;font.family:root.visual.uiFamily;font.pixelSize:21*root.factor;color:(root.ctx.section===modelData.id || modelData.id==="results" && root.ctx.section.indexOf("Results")>0) ? root.visual.accent : root.visual.textSecondary
                    MouseArea { anchors.fill:parent;onClicked:root.action("dossier:"+parent.modelData.id) }
                }
            }
        }
        Repeater {
            model:Math.min(root.pageSize,root.rows.length)
            delegate:Rectangle {
                id: entry
                required property int index
                readonly property int realIndex:Math.floor(root.selected/root.pageSize)*root.pageSize+index
                readonly property var row:root.rows[realIndex] || ({})
                objectName:"pilotRow"+realIndex
                visible:row.title!==undefined
                x:0;y:112+index*112;width:parent.width;height:102;radius:root.visual.radiusRow;color:root.visual.surface
                border.color:realIndex===root.selected ? root.visual.accent : root.visual.border;border.width:realIndex===root.selected ? 2 : 1
                Text { x:18;y:6;width:parent.width*0.50-18;height:32;text:entry.row.title || "";font.family:root.visual.uiFamily;font.pixelSize:23*root.factor;color:root.visual.textPrimary;elide:Text.ElideRight;verticalAlignment:Text.AlignVCenter }
                Text { x:parent.width*0.50;y:6;width:parent.width*0.50-18;height:32;text:entry.row.value || "";font.family:root.visual.numbersFamily;font.pixelSize:21*root.factor;color:root.visual.textPrimary;elide:Text.ElideRight;horizontalAlignment:Text.AlignRight;verticalAlignment:Text.AlignVCenter }
                Text { objectName:"pilotDescription"+entry.realIndex;x:18;y:42;width:parent.width-36;height:52;text:entry.row.description || "";font.family:root.visual.uiFamily;font.pixelSize:18*root.factor;color:root.visual.textSecondary;wrapMode:Text.Wrap;elide:Text.ElideRight;maximumLineCount:2 }
                MouseArea { anchors.fill:parent;onClicked:root.action(entry.row.id || "") }
            }
        }
        Text { visible:root.rows.length===0;x:0;y:132;width:parent.width;height:90;text:root.ctx.section==="results" ? "Nessun risultato registrato" : "Nessuna sessione registrata";font.family:root.visual.uiFamily;font.pixelSize:24*root.factor;color:root.visual.textSecondary;wrapMode:Text.Wrap }
        Text { x:0;y:parent.height-44;width:parent.width;height:42;text:root.rows.length ? (Math.floor(root.selected/root.pageSize)+1)+" / "+Math.ceil(root.rows.length/root.pageSize)+(root.overlay ? "" : " · 5 apre la scheda") : "";font.family:root.visual.numbersFamily;font.pixelSize:19*root.factor;color:root.visual.textSecondary;verticalAlignment:Text.AlignVCenter }
    }
}
