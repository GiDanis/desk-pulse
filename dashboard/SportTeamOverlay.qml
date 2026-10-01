import QtQuick

Item {
    id: root
    required property var dashboard
    readonly property bool picker: dashboard.overlay === "sportTeamPicker"
    readonly property bool matches: !picker && dashboard.teamTab < 2
    readonly property var teamInfo: dashboard.teamData
    readonly property var teamStatus: dashboard.teamState
    readonly property int selected: picker ? dashboard.teamPickerIndex : dashboard.teamIndex
    readonly property int start: Math.floor(Math.max(0, selected) / 3) * 3
    readonly property var rows: picker ? dashboard.teamPickerRows : dashboard.teamRows
    function value(v) { return v == null ? "—" : v }
    function title(row) {
        if (picker) return (row.id === dashboard.sportData.favourite ? "★  " : "") + row.name
        if (matches) return row.homeTeam + " – " + row.awayTeam
        if (dashboard.teamTab === 2) return row.title || ""
        return (row.shirtNumber == null ? "" : row.shirtNumber + "  ") + row.name
    }
    function subtitle(row) {
        if (picker) return row.id ? "Serie A · calendario di tutte le competizioni" : "Rimuovi la preferita dal dispositivo"
        if (matches) return row.when + " · " + row.competitionName + " · " + row.side
        if (dashboard.teamTab === 2) return row.value || ""
        return row.role + " · " + value(row.age) + " anni · " + (row.country || "—")
    }
    Rectangle { anchors.fill: parent; color: dashboard.color }
    Text { x: 44; y: 30; width: 872; text: picker ? "SCEGLI LA SQUADRA PREFERITA" : (teamInfo.name || "LA MIA SQUADRA") + " · " + (teamInfo.season || ""); color: dashboard.accent; font.pixelSize: 35; font.bold: true; elide: Text.ElideRight }
    Repeater {
        model: picker ? [] : ["CALENDARIO", "RISULTATI", "INFO", "ROSA"]
        delegate: Rectangle {
            required property string modelData
            required property int index
            x: 44 + index * 222; y: 87; width: 206; height: 43; radius: 7
            color: index === dashboard.teamTab ? "#28403f" : dashboard.panel
            border.color: index === dashboard.teamTab ? dashboard.accent : dashboard.edge
            border.width: index === dashboard.teamTab ? 2 : 1
            Text { anchors.centerIn: parent; text: modelData; color: index === dashboard.teamTab ? dashboard.accent : dashboard.muted; font.pixelSize: 23; font.bold: true }
        }
    }
    Rectangle {
        visible: root.matches; x: 44; y: 143; width: 872; height: 43; radius: 7
        color: root.selected === -1 ? "#28403f" : "transparent"; border.width: 2
        border.color: root.selected === -1 ? dashboard.accent : "transparent"
        Text { x: 16; anchors.verticalCenter: parent.verticalCenter; text: dashboard.teamSerieAOnly ? "SOLO SERIE A" : "TUTTE LE COMPETIZIONI"; color: dashboard.ink; font.pixelSize: 24; font.bold: true }
        Text { x: 440; width: 414; anchors.verticalCenter: parent.verticalCenter; horizontalAlignment: Text.AlignRight; text: root.selected === -1 ? "4/6 FILTRO · 8 PARTITE" : "2 IN ALTO PER IL FILTRO"; color: dashboard.muted; font.pixelSize: 20 }
    }
    Text { visible: picker; x: 44; y: 113; width: 872; text: "2/8 SCEGLI · 5 SALVA · Nessuna per rimuovere la preferita"; color: dashboard.muted; font.pixelSize: 24 }
    Text { visible: !picker && !matches; x: 44; y: 153; width: 872; text: dashboard.teamTab === 3 ? (teamInfo.squad || []).length + " giocatori pubblicati dalla fonte" : "Profilo del club · " + (teamInfo.calendarScope === "league" ? "dati Serie A " + (teamInfo.season || "") : "stagione corrente"); color: dashboard.muted; font.pixelSize: 23 }
    Repeater {
        model: root.rows.slice(root.start, root.start + 3)
        delegate: Rectangle {
            required property var modelData
            required property int index
            y: 200 + index * 102; x: 44; width: 872; height: 90; radius: 9
            color: root.start + index === root.selected ? "#28403f" : dashboard.panel
            border.color: root.start + index === root.selected ? dashboard.accent : dashboard.edge
            border.width: root.start + index === root.selected ? 3 : 1
            Text { x: 18; y: 10; width: root.matches ? 677 : 825; text: root.title(modelData); color: dashboard.ink; font.pixelSize: 29; font.bold: true; elide: Text.ElideRight }
            Text { x: 18; y: 53; width: modelData.action ? 643 : 832; text: root.subtitle(modelData); color: dashboard.muted; font.pixelSize: 22; elide: Text.ElideRight }
            Text { x: 716; y: root.matches ? 16 : 54; width: 134; horizontalAlignment: Text.AlignRight; text: root.matches ? modelData.status === "scheduled" ? "VS" : (modelData.scoreText || "—") : modelData.action || ""; color: dashboard.accent; font.pixelSize: root.matches ? 30 : 20; font.bold: true }
        }
    }
    Text { visible: !rows.length; x: 44; y: 220; width: 872; text: !dashboard.sportData.favourite ? "Nessuna squadra preferita · 5 per sceglierla" : dashboard.teamTab === 3 ? "Rosa non disponibile dalla fonte" : teamStatus.status === "updating" ? "Caricamento squadra…" : "Nessuna partita pubblicata per questa selezione"; color: dashboard.ink; font.pixelSize: 30; wrapMode: Text.WordWrap }
    Text { x: 44; y: 525; width: 872; text: (root.rows.length ? (Math.max(0, selected) + 1) + "/" + rows.length + " · " : "") + (picker ? "5 SALVA PREFERITA" : "2/8 SCORRI · 4/6 " + (selected === -1 && matches ? "FILTRO" : "SCHEDE") + (matches ? " · 5 APRI" : dashboard.teamTab === 2 && selected === 0 ? " · 5 CAMBIA SQUADRA" : dashboard.teamTab === 2 && selected === 1 ? " · 5 AGGIORNA" : "")); color: dashboard.muted; font.pixelSize: 23 }
    Text { visible: !picker; x: 44; y: 556; width: 872; text: teamInfo.cacheError || teamStatus.error || (teamInfo.calendarScope === "league" ? "Calendario parziale · solo Serie A disponibile" : "Fonte FotMob · " + (teamStatus.updatedAt ? new Date(teamStatus.updatedAt * 1000).toLocaleString(Qt.locale("it_IT"), "dd/MM hh:mm") : "dati in attesa") + (teamStatus.status === "stale" || teamStatus.status === "offline" ? " · Dati salvati" : "")); color: teamStatus.error || teamInfo.calendarScope === "league" ? "#efbd75" : dashboard.muted; font.pixelSize: 20; elide: Text.ElideRight }
    Text { x: 44; y: 592; text: "1 INDIETRO      7 HOME"; color: dashboard.accent; font.pixelSize: 23 }
}
