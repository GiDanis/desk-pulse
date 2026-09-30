import QtQuick

Item {
    id: root
    required property var dashboard
    readonly property var account: dashboard.account
    readonly property var accountInfo: dashboard.accountData
    readonly property bool hasData: dashboard.accountWindows.length > 0
    readonly property bool current: account.status === "active"
    readonly property real highestUsage: hasData ? Math.max.apply(null, dashboard.accountWindows.map(w => w.usedPercent)) : 0

    function two(value) { return value < 10 ? "0" + value : "" + value }
    function stamp(seconds) {
        if (!seconds) return "—"
        const d = new Date(seconds * 1000)
        return two(d.getDate()) + "/" + two(d.getMonth() + 1) + " " + two(d.getHours()) + ":" + two(d.getMinutes())
    }
    function duration(minutes) {
        if (minutes % 10080 === 0) return (minutes / 10080) + " sett."
        if (minutes % 1440 === 0) return (minutes / 1440) + " giorni"
        if (minutes % 60 === 0) return (minutes / 60) + " ore"
        return minutes + " min"
    }
    function usageColor(used) {
        if (!current) return dashboard.muted
        if (used >= dashboard.accountCriticalPercent) return "#f28c82"
        if (used >= dashboard.accountWarningPercent) return "#efbd75"
        return dashboard.accent
    }

    Rectangle {
        x: 0; y: 0; width: 872; height: 88; radius: 9
        color: dashboard.panel; border.color: dashboard.edge
        Text { x: 20; y: 11; text: "PIANO"; color: dashboard.muted; font.pixelSize: 21; font.bold: true }
        Text {
            x: 20; y: 35; width: 290
            text: root.accountInfo.plan ? String(root.accountInfo.plan).toUpperCase() : "NON DISPONIBILE"
            color: dashboard.ink; font.pixelSize: root.accountInfo.plan ? 36 : 27; font.bold: true
        }
        Text {
            x: 332; y: 17; width: 518; horizontalAlignment: Text.AlignRight
            text: root.current ? "AGGIORNATO · " + root.stamp(root.account.updatedAt) :
                  root.account.status === "stale" ? "NON AGGIORNATO · " + root.stamp(root.account.updatedAt) :
                  root.account.status === "unavailable" ? "ACCOUNT NON DISPONIBILE" : "ERRORE DATI ACCOUNT"
            color: root.current ? dashboard.accent : "#efbd75"
            font.pixelSize: 22; font.bold: true
        }
        Text {
            x: 332; y: 49; width: 518; horizontalAlignment: Text.AlignRight
            text: "Fonte: " + root.account.source
            color: dashboard.muted; font.pixelSize: 21
        }
    }

    Text { x: 0; y: 103; text: "UTILIZZO DEL PIANO"; color: dashboard.accent; font.pixelSize: 24; font.bold: true }
    Text {
        x: 575; y: 105; width: 297; horizontalAlignment: Text.AlignRight
        visible: root.hasData && (dashboard.accountWindows.length > 2 || root.current && root.highestUsage >= dashboard.accountWarningPercent)
        text: root.current && root.highestUsage >= dashboard.accountCriticalPercent ?
                  "QUASI ESAURITO" + (dashboard.accountWindows.length > 2 ? " · 2/8" : "") :
              root.current && root.highestUsage >= dashboard.accountWarningPercent ?
                  "UTILIZZO ELEVATO" + (dashboard.accountWindows.length > 2 ? " · 2/8" : "") :
              "2/8 SCORRI · " + (dashboard.accountIndex + 1) + "/" + (dashboard.accountWindows.length - 1)
        color: root.current && root.highestUsage >= dashboard.accountWarningPercent
               ? root.usageColor(root.highestUsage) : dashboard.muted
        font.pixelSize: 19; font.bold: root.current && root.highestUsage >= dashboard.accountWarningPercent
    }
    Repeater {
        model: root.hasData ? dashboard.accountWindows.slice(dashboard.accountIndex, dashboard.accountIndex + 2) : []
        delegate: Rectangle {
            required property var modelData
            required property int index
            x: 0; y: 134 + index * 102; width: 872; height: 94; radius: 9
            color: dashboard.panel; border.color: dashboard.edge
            Text {
                x: 18; y: 11; width: 590
                text: modelData.label + " · " + root.duration(modelData.windowDurationMins)
                color: dashboard.ink; font.pixelSize: 27; font.bold: true; elide: Text.ElideRight
            }
            Text {
                x: 18; y: 49
                text: "Ripristino " + root.stamp(modelData.resetsAt)
                color: dashboard.muted; font.pixelSize: 21
            }
            Text {
                x: 605; y: 12; width: 248; horizontalAlignment: Text.AlignRight
                text: modelData.usedPercent + "% usato"
                color: root.usageColor(modelData.usedPercent)
                font.pixelSize: 26; font.bold: true
            }
            Rectangle { x: 606; y: 63; width: 246; height: 13; radius: 6; color: dashboard.edge }
            Rectangle {
                x: 606; y: 63; width: 246 * Math.min(100, modelData.usedPercent) / 100
                height: 13; radius: 6; color: root.usageColor(modelData.usedPercent)
            }
        }
    }
    Text {
        visible: !root.hasData; x: 0; y: 155; width: 850
        text: root.account.error || "Dati di utilizzo non ancora disponibili"
        color: dashboard.ink; font.pixelSize: 30; wrapMode: Text.WordWrap
    }

    Rectangle {
        x: 0; y: 342; width: 423; height: 76; radius: 9
        color: dashboard.panel; border.color: dashboard.edge
        Text { x: 18; y: 8; text: "CREDITI DISPONIBILI"; color: dashboard.muted; font.pixelSize: 20; font.bold: true }
        Text {
            x: 18; y: 34
            text: !root.hasData || !root.accountInfo.credits ? "DATO NON DISPONIBILE" :
                  root.accountInfo.credits.unlimited ? "ILLIMITATI" :
                  root.accountInfo.credits.balance !== "" ? root.accountInfo.credits.balance : "DATO NON DISPONIBILE"
            color: dashboard.ink; font.pixelSize: 26; font.bold: true
        }
    }
    Rectangle {
        x: 449; y: 342; width: 423; height: 76; radius: 9
        color: dashboard.panel; border.color: dashboard.edge
        Text { x: 18; y: 8; text: "RESET DEL LIMITE"; color: dashboard.muted; font.pixelSize: 20; font.bold: true }
        Text {
            x: 18; y: 34
            text: !root.hasData || root.accountInfo.resetCredits === null || root.accountInfo.resetCredits === undefined
                  ? "DATO NON DISPONIBILE" : root.accountInfo.resetCredits + " disponibili"
            color: dashboard.ink; font.pixelSize: 26; font.bold: true
        }
    }
}
