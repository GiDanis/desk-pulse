pragma ComponentBehavior: Bound
import QtQuick
import "Format.js" as Format
PageCanvas {
    id:root
    title:"Account"
    subtitle:ctx && ctx.account ? ctx.account.plan || "Piano non disponibile" : "Account non disponibile"
    source:ctx && ctx.account ? ctx.account.source : null
    readonly property var windows:{ if (!ctx) return [];ctx.dataRevision;return ctx.account ? Format.list(ctx.account.windows) : [] }
    readonly property int first:ctx ? Math.max(0,Math.min(windows.length-2,ctx.selection.index)) : 0
    readonly property real creditHeight:164
    readonly property real usageHeight:bodyHeight-creditHeight-16
    readonly property var credits:ctx && ctx.account ? ctx.account.credits : null
    Row {
        y:root.bodyTop;spacing:16
        Repeater {
            model:root.windows.slice(root.first,root.first+2)
            delegate:Card {
                id:windowCard
                required property var modelData
                objectName:"accountUsageCard"+index
                required property int index
                readonly property color emphasis:modelData.severity==="critical" ? root.style.semantic.accountCriticalOnCard : modelData.severity==="warning" ? root.style.semantic.warningOnCard : root.style.semantic.accentTextOnCard
                width:(root.width-16)/(root.windows.length===1 ? 1 : 2)+(root.windows.length===1 ? 16 : 0);height:root.usageHeight;style:root.style
                OutlineIcon { x:22;y:22;symbol:"account";opticalSize:32;tint:windowCard.emphasis }
                Label { x:70;y:14;width:parent.width-92;height:42;themeStyle:root.style;size:26;font.weight:Font.DemiBold;text:Format.windowLabel(windowCard.modelData);maximumLineCount:1 }
                Label { x:22;y:66;width:parent.width-44;height:83;themeStyle:root.style;size:65;font.weight:Font.DemiBold;text:Format.number(windowCard.modelData.usedPercent)+(windowCard.modelData.usedPercent.available && Format.number(windowCard.modelData.usedPercent).indexOf("%")<0 ? "%" : "");maximumLineCount:1 }
                Label { x:22;y:148;width:parent.width-44;height:30;themeStyle:root.style;secondary:true;size:20;text:windowCard.modelData.usedPercent.available ? "Utilizzato" : "Utilizzo non disponibile";maximumLineCount:1 }
                Rectangle { x:22;y:parent.height-85;width:parent.width-44;height:8;radius:4;color:root.style.border
                    Rectangle { width:parent.width*(windowCard.modelData.usedPercent.available ? Math.min(100,Math.max(0,windowCard.modelData.usedPercent.value))/100 : 0);height:parent.height;radius:4;color:windowCard.emphasis }
                }
                Label { x:22;y:parent.height-63;width:parent.width-44;height:53;themeStyle:root.style;secondary:true;size:20;text:windowCard.modelData.resetsAt===null ? "Reset non disponibile" : "Reset "+Format.stamp(windowCard.modelData.resetsAt);maximumLineCount:2 }
            }
        }
    }
    Label { y:root.bodyTop;width:parent.width;height:root.usageHeight;themeStyle:root.style;secondary:true;size:26;text:"Nessuna finestra di utilizzo disponibile";visible:root.windows.length===0;horizontalAlignment:Text.AlignHCenter }
    Row {
        y:root.bodyTop+root.usageHeight+16;spacing:16
        Metric { objectName:"accountCreditsCard";width:(root.width-16)/2;height:root.creditHeight;style:root.style;title:"Crediti disponibili";value:root.credits ? root.credits.unlimited ? "Illimitati" : Format.scalar(root.credits.balance) : "—";valueSize:30 }
        Metric { width:(root.width-16)/2;height:root.creditHeight;style:root.style;title:"Reset disponibili";value:root.ctx && root.ctx.account ? Format.number(root.ctx.account.resetCredits) : "—";valueSize:30 }
    }
}
