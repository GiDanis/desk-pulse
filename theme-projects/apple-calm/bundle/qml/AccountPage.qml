pragma ComponentBehavior: Bound
import QtQuick
import "Format.js" as Format
PageCanvas {
    id:root
    title:"Account"
    subtitle:ctx && ctx.account ? (ctx.account.plan || "Piano non disponibile")+" · snapshot" : "Account non disponibile"
    source:ctx && ctx.account ? ctx.account.source : null
    readonly property var windows:{if(!ctx)return [];ctx.dataRevision;return ctx.account ? Format.list(ctx.account.windows) : []}
    readonly property int first:ctx ? Math.max(0,Math.min(windows.length-2,ctx.selection.index)) : 0
    readonly property bool showCredits:bodyHeight>=420
    readonly property real creditHeight:128
    readonly property real usageHeight:bodyHeight-(showCredits ? creditHeight+16 : 0)
    readonly property var credits:ctx && ctx.account ? ctx.account.credits : null
    Row {
        y:root.bodyTop;spacing:16
        Repeater {
            model:root.windows.slice(root.first,root.first+2)
            delegate:Card {
                id:windowCard
                required property var modelData
                required property int index
                objectName:"accountUsageCard"+index
                readonly property var residual:Format.remaining(modelData.usedPercent)
                readonly property color emphasis:modelData.severity === "critical" ? root.style.semantic.accountCriticalOnCard : modelData.severity === "warning" ? root.style.semantic.warningOnCard : root.style.semantic.accentTextOnCard
                width:root.windows.length===1 ? root.width : (root.width-16)/2;height:root.usageHeight;style:root.style
                Label { x:22;y:10;width:parent.width-44;height:38;themeStyle:root.style;size:26;font.weight:Font.DemiBold;text:Format.windowLabel(windowCard.modelData);maximumLineCount:1 }
                Label { objectName:"accountRemaining"+windowCard.index;x:22;y:48;width:parent.width-44;height:80;themeStyle:root.style;size:65;font.family:root.style.numbersFamily;text:Format.percent(windowCard.residual);maximumLineCount:1 }
                Label { x:22;y:130;width:parent.width-44;height:32;themeStyle:root.style;secondary:true;size:24;text:windowCard.residual===null ? "Dato non disponibile" : "Residuo nello snapshot";maximumLineCount:1 }
                Rectangle {
                    x:22;y:parent.height-84;width:parent.width-44;height:8;radius:4;color:root.style.border;visible:windowCard.residual!==null && parent.height>=260
                    Rectangle { objectName:"accountRemainingBar"+windowCard.index;width:parent.width*(windowCard.residual===null ? 0 : windowCard.residual/100);height:parent.height;radius:4;color:windowCard.emphasis }
                }
                Label { x:22;y:parent.height>=260 ? parent.height-65 : 166;width:parent.width-44;height:54;visible:parent.height>=220;themeStyle:root.style;secondary:true;size:22;text:Format.stamp(windowCard.modelData.resetsAt) ? "Reset "+Format.stamp(windowCard.modelData.resetsAt) : "Reset non disponibile";maximumLineCount:2 }
            }
        }
    }
    Label { y:root.bodyTop;width:parent.width;height:root.usageHeight;themeStyle:root.style;secondary:true;size:26;text:"Nessuna finestra di utilizzo disponibile";visible:root.windows.length===0;horizontalAlignment:Text.AlignHCenter }
    Row {
        y:root.bodyTop+root.usageHeight+16;spacing:16;visible:root.showCredits
        Metric { objectName:"accountCreditsCard";width:(root.width-16)/2;height:root.creditHeight;style:root.style;title:"Crediti disponibili";value:root.credits ? root.credits.unlimited ? "Illimitati" : Format.scalar(root.credits.balance) : "—";valueSize:30 }
        Metric { width:(root.width-16)/2;height:root.creditHeight;style:root.style;title:"Reset disponibili";value:root.ctx && root.ctx.account ? Format.number(root.ctx.account.resetCredits) : "—";valueSize:30 }
    }
}
