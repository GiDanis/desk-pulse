pragma ComponentBehavior: Bound
import QtQuick
import "Format.js" as Format

PageCanvas {
    id: root
    title: "Account"
    subtitle: ctx && ctx.account ? ctx.account.plan || "Piano non disponibile" : "Account non disponibile"
    source: ctx && ctx.account ? ctx.account.source : null
    readonly property var windows: { if (!ctx) return []; ctx.dataRevision; return ctx.account ? Format.list(ctx.account.windows) : [] }
    readonly property int first: ctx ? Math.max(0, Math.min(windows.length-2,ctx.selection.index)) : 0
    Row {
        y:94; spacing:20
        Repeater {
            model:root.windows.slice(root.first,root.first+2)
            delegate: Card {
                id: windowCard
                required property var modelData
                readonly property color emphasis: windowCard.modelData.severity === "critical" ? root.style.semantic.accountCriticalOnCard : windowCard.modelData.severity === "warning" ? root.style.semantic.warningOnCard : root.style.semantic.accentTextOnCard
                width:(root.width-20)/2; height:312; style:root.style
                OutlineIcon { x:22; y:24; symbol:"account"; opticalSize:32; tint:parent.emphasis }
                Label { x:70; y:18; width:parent.width-92; height:44; themeStyle:root.style; size:26; font.weight:Font.DemiBold; text:windowCard.modelData.label; maximumLineCount:1 }
                Label { x:22; y:77; width:parent.width-44; height:91; themeStyle:root.style; size:65; font.weight:Font.DemiBold; text:Format.number(windowCard.modelData.usedPercent) + (windowCard.modelData.usedPercent.available && Format.number(windowCard.modelData.usedPercent).indexOf("%") < 0 ? "%" : ""); maximumLineCount:1 }
                Label { x:22; y:170; width:parent.width-44; height:30; themeStyle:root.style; secondary:true; size:20; text:windowCard.modelData.usedPercent.available ? "Utilizzato" : "Utilizzo non disponibile"; maximumLineCount:1 }
                Rectangle { x:22; y:214; width:parent.width-44; height:8; radius:4; color:root.style.border
                    Rectangle { width:parent.width*(windowCard.modelData.usedPercent.available ? Math.min(100,Math.max(0,windowCard.modelData.usedPercent.value))/100 : 0); height:parent.height; radius:4; color:windowCard.emphasis }
                }
                Label { x:22; y:244; width:parent.width-44; height:53; themeStyle:root.style; secondary:true; size:20; text:windowCard.modelData.resetsAt === null ? "Reset non disponibile" : "Reset " + Format.stamp(windowCard.modelData.resetsAt); maximumLineCount:2 }
            }
        }
    }
    Label { y:94; width:parent.width; height:312; themeStyle:root.style; secondary:true; size:26; text:"Nessuna finestra di utilizzo disponibile"; visible:root.windows.length===0; horizontalAlignment:Text.AlignHCenter }
}
