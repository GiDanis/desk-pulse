import QtQuick
import "themes"
import "components"

Item {
    id: root
    property StyleFacade style: Theme
    required property var dashboard
    readonly property bool picker: dashboard.overlay === "sportTeamPicker"
    readonly property bool matches: !picker && dashboard.teamTab < 2
    readonly property var teamInfo: dashboard.teamData
    readonly property var teamStatus: dashboard.teamState
    readonly property int selected: picker ? dashboard.teamPickerIndex : dashboard.teamIndex
    readonly property int start: Math.floor(Math.max(0, selected) / root.style.compactRows) * root.style.compactRows
    readonly property var rows: picker ? dashboard.teamPickerRows : dashboard.teamRows
    function value(v) { return v == null ? "—" : v }
    function title(row) {
        if (picker) return row.name
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
    AppText { style: root.style; x: 44; y: 30; width: 872; text: picker ? "SCEGLI LA SQUADRA PREFERITA" : (teamInfo.name || "LA MIA SQUADRA") + " · " + (teamInfo.season || ""); color: root.style.accentTextOnOverlay; font.pixelSize: root.style.font35; font.weight: (true) ? root.style.headingWeight : root.style.bodyWeight; elide: Text.ElideRight }
    Repeater {
        model: picker ? [] : ["CALENDARIO", "RISULTATI", "INFO", "ROSA"]
        delegate: SelectableRow { style: root.style; selectedState: index === dashboard.teamTab;
            required property string modelData
            required property int index
            x: 44 + index * 222; y: 87; width: 206; height: 43; radius: root.style.radiusPill
            color: index === dashboard.teamTab ? root.style.surfaceFocused : root.style.surface
            border.color: index === dashboard.teamTab ? root.style.focusIndicator : root.style.border
            border.width: index === dashboard.teamTab ? root.style.borderWidth : root.style.hairlineWidth
            AppText { style: root.style; anchors.centerIn: parent; text: modelData; color: index === dashboard.teamTab ? root.style.accentTextOnFocused : root.style.textSecondary; font.pixelSize: root.style.font23; font.weight: (true ) ? root.style.headingWeight : root.style.bodyWeight}
        }
    }
    Rectangle {
        visible: root.matches; x: 44; y: 143; width: 872; height: 43; radius: root.style.radiusPill
        color: root.selected === -1 ? root.style.surfaceFocused : "transparent"; border.width: root.style.borderWidth
        border.color: root.selected === -1 ? root.style.focusIndicator : "transparent"
        AppText { style: root.style; x: 16; anchors.verticalCenter: parent.verticalCenter; text: dashboard.teamSerieAOnly ? "SOLO SERIE A" : "TUTTE LE COMPETIZIONI"; color: root.style.textPrimary; font.pixelSize: root.style.font24; font.weight: (true ) ? root.style.headingWeight : root.style.bodyWeight}
        AppText { style: root.style; x: 440; width: 414; anchors.verticalCenter: parent.verticalCenter; horizontalAlignment: Text.AlignRight; text: root.selected === -1 ? "4/6 FILTRO · 8 PARTITE" : "2 IN ALTO PER IL FILTRO"; color: root.style.textSecondary; font.pixelSize: root.style.font20 }
    }
    AppText { style: root.style; visible: picker; x: 44; y: 113; width: 872; text: "2/8 SCEGLI · 5 SALVA · Nessuna per rimuovere la preferita"; color: root.style.textSecondary; font.pixelSize: root.style.font24 }
    AppText { style: root.style; visible: !picker && !matches; x: 44; y: 153; width: 872; text: dashboard.teamTab === 3 ? (teamInfo.squad || []).length + " giocatori pubblicati dalla fonte" : "Profilo del club · " + (teamInfo.calendarScope === "league" ? "dati Serie A " + (teamInfo.season || "") : "stagione corrente"); color: root.style.textSecondary; font.pixelSize: root.style.font23 }
    Repeater {
        model: root.rows.slice(root.start, root.start + root.style.compactRows)
        delegate: SelectableRow { style: root.style; selectedState: root.start + index === root.selected;
            required property var modelData
            required property int index
            y: 200 + index * 102; x: 44; width: 872; height: 90; radius: root.style.radiusRow
            color: root.start + index === root.selected ? root.style.surfaceFocused : root.style.surface
            border.color: root.start + index === root.selected ? root.style.focusIndicator : root.style.border
            border.width: root.start + index === root.selected ? root.style.focusWidth : root.style.hairlineWidth
            AppIcon { style: root.style; x: 18; y: 15; opticalSize: 22; iconId: "sport.favourite"; visible: root.picker && modelData.id === dashboard.sportData.favourite }
            AppText { style: root.style; x: root.picker && modelData.id === dashboard.sportData.favourite ? 49 : 18; y: 10; width: root.matches ? 677 : 794; text: root.title(modelData); color: root.style.textPrimary; font.pixelSize: root.style.font29; font.weight: (true) ? root.style.headingWeight : root.style.bodyWeight; elide: Text.ElideRight }
            AppText { style: root.style; x: 18; y: 53; width: modelData.action ? 643 : 832; text: root.subtitle(modelData); color: root.style.textSecondary; font.pixelSize: root.style.font22; elide: Text.ElideRight }
            AppText { style: root.style; x: 716; y: root.matches ? 16 : 54; width: 134; horizontalAlignment: Text.AlignRight; text: root.matches ? modelData.status === "scheduled" ? "VS" : (modelData.scoreText || "—") : modelData.action || ""; color: root.style.accentTextOnOverlay; font.pixelSize: root.matches ? root.style.font30 : root.style.font20; font.weight: (true ) ? root.style.headingWeight : root.style.bodyWeight}
        }
    }
    AppText { style: root.style; visible: !rows.length; x: 44; y: 220; width: 872; text: !dashboard.sportData.favourite ? "Nessuna squadra preferita · 5 per sceglierla" : dashboard.teamTab === 3 ? "Rosa non disponibile dalla fonte" : teamStatus.status === "updating" ? "Caricamento squadra…" : "Nessuna partita pubblicata per questa selezione"; color: root.style.textPrimary; font.pixelSize: root.style.font30; wrapMode: Text.WordWrap }
    AppText { style: root.style; x: 44; y: 525; width: 872; text: (root.rows.length ? (Math.max(0, selected) + 1) + "/" + rows.length + " · " : "") + (picker ? "5 SALVA PREFERITA" : "2/8 SCORRI · 4/6 " + (selected === -1 && matches ? "FILTRO" : "SCHEDE") + (matches ? " · 5 APRI" : dashboard.teamTab === 2 && selected === 0 ? " · 5 CAMBIA SQUADRA" : dashboard.teamTab === 2 && selected === 1 ? " · 5 AGGIORNA" : "")); color: root.style.textSecondary; font.pixelSize: root.style.font23 }
    AppText { style: root.style; visible: !picker; x: 44; y: 556; width: 872; text: teamInfo.cacheError || teamStatus.error || (teamInfo.calendarScope === "league" ? "Calendario parziale · solo Serie A disponibile" : "Fonte FotMob · " + (teamStatus.updatedAt ? new Date(teamStatus.updatedAt * 1000).toLocaleString(Qt.locale("it_IT"), "dd/MM hh:mm") : "dati in attesa") + (teamStatus.status === "stale" || teamStatus.status === "offline" ? " · Dati salvati" : "")); color: teamStatus.error || teamInfo.calendarScope === "league" ? root.style.warningOnOverlay : root.style.textSecondary; font.pixelSize: root.style.font20; elide: Text.ElideRight }
    KeyGuide { style: root.style; x: 44; y: 592; color: root.style.accentTextOnOverlay; font.pixelSize: root.style.font23 }
}
