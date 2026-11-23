import QtQuick
import "themes"
import "components"
Item {
    id:root
    property StyleFacade style:Theme
    required property var dashboard
    readonly property var account:dashboard.account
    readonly property var accountInfo:dashboard.accountData
    readonly property var windows:dashboard.accountWindows.slice(dashboard.accountIndex,dashboard.accountIndex+2)
    readonly property bool current:account.status==="active"
    readonly property real usageTop:112
    readonly property real usageHeight:height-usageTop-120
    function stamp(seconds) { return seconds===null || seconds===undefined ? "—" : Qt.formatDateTime(new Date(seconds*1000),"dd/MM hh:mm") }
    function duration(minutes) {
        if (typeof minutes!=="number" || !isFinite(minutes)) return "Durata non disponibile"
        if (minutes%10080===0 && minutes>0) return minutes/10080+" sett."
        if (minutes%1440===0 && minutes>0) return minutes/1440+" giorni"
        if (minutes%60===0 && minutes>0) return minutes/60+" ore"
        return minutes+" min"
    }
    function used(row) { return typeof row.usedPercent==="number" && isFinite(row.usedPercent) ? row.usedPercent : null }
    function usageColor(value) { return !current || value===null ? style.textSecondary : value>=dashboard.accountCriticalPercent ? style.accountCriticalOnCard : value>=dashboard.accountWarningPercent ? style.warningOnCard : style.accentTextOnCard }
    Rectangle {
        width:root.width;height:96;radius:root.style.radiusRow;color:root.style.surface;border.color:root.style.border
        AppText { style:root.style;x:20;y:11; text:"PIANO";color:root.style.textSecondary;font.pixelSize:root.style.font21;font.weight:root.style.headingWeight }
        AppText { style:root.style;x:20;y:40;width:parent.width*0.36;height:42;text:root.accountInfo.plan || "NON DISPONIBILE";color:root.style.textPrimary;font.pixelSize:root.style.font30;font.weight:root.style.headingWeight;elide:Text.ElideRight }
        AppText { style:root.style;x:parent.width*0.40;y:15;width:parent.width*0.60-20;horizontalAlignment:Text.AlignRight;text:root.current ? "AGGIORNATO · "+root.stamp(root.account.updatedAt) : root.account.status==="stale" || root.account.status==="offline" ? "DATI PRECEDENTI · "+root.stamp(root.account.updatedAt) : root.account.status==="updating" ? "AGGIORNAMENTO · ULTIMA LETTURA "+root.stamp(root.account.updatedAt) : "ACCOUNT NON DISPONIBILE";color:root.current ? root.style.accentTextOnCard : root.style.warningOnCard;font.pixelSize:root.style.font21;elide:Text.ElideRight }
        AppText { style:root.style;x:parent.width*0.40;y:52;width:parent.width*0.60-20;horizontalAlignment:Text.AlignRight;text:"Fonte: "+root.account.source;color:root.style.textSecondary;font.pixelSize:root.style.font21 }
    }
    Repeater {
        model:root.windows
        delegate:Rectangle {
            required property var modelData
            required property int index
            readonly property var used:root.used(modelData)
            x:index*(width+16);y:root.usageTop;width:root.windows.length===1 ? root.width : (root.width-16)/2;height:root.usageHeight;radius:root.style.radiusCard;color:root.style.surface;border.color:root.style.border
            AppText { style:root.style;x:20;y:14;width:parent.width-40;height:58;text:modelData.label || modelData.name || root.duration(modelData.windowDurationMins===undefined ? modelData.durationMins : modelData.windowDurationMins);color:root.style.textPrimary;font.pixelSize:root.style.font27;font.weight:root.style.headingWeight;wrapMode:Text.WordWrap;maximumLineCount:2;elide:Text.ElideRight }
            AppText { style:root.style;x:20;y:82;width:parent.width-40;text:parent.used===null ? "—" : parent.used+"%";color:root.usageColor(parent.used);font.pixelSize:root.style.font65;font.weight:root.style.headingWeight }
            AppText { style:root.style;x:20;y:164;width:parent.width-40;text:parent.used===null ? "Utilizzo non disponibile" : "Utilizzato";color:root.style.textSecondary;font.pixelSize:root.style.font22 }
            Rectangle { x:20;y:parent.height-80;width:parent.width-40;height:10;radius:4;color:root.style.border
                Rectangle { width:parent.width*(parent.parent.used===null ? 0 : Math.max(0,Math.min(100,parent.parent.used))/100);height:parent.height;radius:4;color:root.usageColor(parent.parent.used) }
            }
            AppText { style:root.style;x:20;y:parent.height-53;width:parent.width-40;height:45;text:modelData.resetsAt===null || modelData.resetsAt===undefined ? "Reset non disponibile" : "Ripristino "+root.stamp(modelData.resetsAt);color:root.style.textSecondary;font.pixelSize:root.style.font22;wrapMode:Text.WordWrap;maximumLineCount:2 }
        }
    }
    AppText { style:root.style;visible:root.windows.length===0;y:root.usageTop;width:root.width;text:root.account.error || "Dati di utilizzo non ancora disponibili";color:root.style.textPrimary;font.pixelSize:root.style.font30;wrapMode:Text.WordWrap }
    Rectangle {
        x:0;y:root.height-104;width:(root.width-16)/2;height:104;radius:root.style.radiusRow;color:root.style.surface;border.color:root.style.border
        AppText { style:root.style;x:20;y:12;width:parent.width-40;text:"CREDITI DISPONIBILI";color:root.style.textSecondary;font.pixelSize:root.style.font20;font.weight:root.style.headingWeight }
        AppText { style:root.style;x:20;y:52;width:parent.width-40;text:!root.accountInfo.credits ? "DATO NON DISPONIBILE" : root.accountInfo.credits.unlimited ? "ILLIMITATI" : root.accountInfo.credits.balance===null || root.accountInfo.credits.balance===undefined || root.accountInfo.credits.balance==="" ? "DATO NON DISPONIBILE" : String(root.accountInfo.credits.balance);color:root.style.textPrimary;font.pixelSize:root.style.font27;font.weight:root.style.headingWeight;elide:Text.ElideRight }
    }
    Rectangle {
        x:(root.width+16)/2;y:root.height-104;width:(root.width-16)/2;height:104;radius:root.style.radiusRow;color:root.style.surface;border.color:root.style.border
        AppText { style:root.style;x:20;y:12;width:parent.width-40;text:"RESET DEL LIMITE";color:root.style.textSecondary;font.pixelSize:root.style.font20;font.weight:root.style.headingWeight }
        AppText { style:root.style;x:20;y:52;width:parent.width-40;text:root.accountInfo.resetCredits===null || root.accountInfo.resetCredits===undefined ? "DATO NON DISPONIBILE" : root.accountInfo.resetCredits+" disponibili";color:root.style.textPrimary;font.pixelSize:root.style.font27;font.weight:root.style.headingWeight;elide:Text.ElideRight }
    }
}
