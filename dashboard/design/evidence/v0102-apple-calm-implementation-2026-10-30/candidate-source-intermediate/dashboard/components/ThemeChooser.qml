pragma ComponentBehavior: Bound
import QtQuick
import "../themes"
Item {
    id: root
    required property var controller
    property StyleFacade style: Theme
    readonly property var rows: controller.themeService ? controller.themeService.themeInventory : []
    property string focusedId: ""
    onRowsChanged: {
        const retained=rows.findIndex(row=>row.id===focusedId)
        if (retained>=0) controller.themeChoiceIndex=retained
        else controller.themeChoiceIndex=Math.max(0,Math.min(rows.length-1,controller.themeChoiceIndex))
    }
    Connections {
        target:root.controller
        function onThemeChoiceIndexChanged() {
            const row=root.rows[root.controller.themeChoiceIndex]
            if (row) root.focusedId=row.id
        }
    }
    readonly property var operation: controller.themeOperation
    readonly property var selectedRow: rows[controller.themeChoiceIndex] || ({})
    readonly property var incidentRow: selectedRow.selectable === false ? selectedRow :
        (selectedRow.revisions || []).find(row=>row.state==="blocked" || row.state==="invalid") || ({})
    readonly property bool showIncident: selectedRow.selectable === false || !!incidentRow.reason
    visible: controller.overlay === "themeChooser" && !controller.urgentEvent.id
    objectName: "themeChooser"
    Rectangle { anchors.fill: parent; color: root.style.background }
    Rectangle { anchors.fill: parent; color: root.style.backgroundOverlay }
    AppText { style: root.style; x:24; y:13; text:"Aspetto"; font.pixelSize:root.style.font31; color:root.style.textPrimary }
    Rectangle { x:24; y:55; width:912; height:1; color:root.style.border }
    AppText { style:root.style; x:24; y:76; text:"Scegli il tema"; font.pixelSize:root.style.font37; color:root.style.textPrimary; font.weight:root.style.headingWeight }
    AppText { style:root.style; x:24; y:121; width:912; text:root.controller.themeService && root.controller.themeService.dirty ? "Attiva il tema con le regolazioni compatibili della bozza" : "Il tema scelto viene attivato e salvato"; font.pixelSize:root.style.font22; color:root.style.textSecondary; elide:Text.ElideRight }
    ListView {
        id:list
        objectName:"themeChoiceList"
        x:24; y:164; width:912; height:root.showIncident ? 318 : root.operation.message && !root.operation.busy ? 420 : 460
        clip:true; spacing:12; boundsBehavior:Flickable.StopAtBounds
        model:root.rows
        currentIndex:root.controller.themeChoiceIndex
        onCurrentIndexChanged: {
            Qt.callLater(function() {list.positionViewAtIndex(list.currentIndex,ListView.Contain)})
        }
        delegate: SelectableRow {
            required property var modelData
            required property int index
            style:root.style
            selectedState:index===root.controller.themeChoiceIndex
            objectName:"themeChoice"+index
            width:list.width-(list.contentHeight>list.height ? 10 : 0)
            height:Math.max(126*root.style.textScale,(list.height-24)/Math.min(3,Math.max(1,list.count)))
            radius:root.style.radiusCard
            color:selectedState ? root.style.surfaceFocused : root.style.surface
            border.color:selectedState ? root.style.focusIndicator : root.style.border
            border.width:selectedState ? root.style.focusWidth : root.style.hairlineWidth
            AppIcon { style:root.style; x:20; y:24; iconId:"system.display"; opticalSize:32 }
            AppText { style:root.style; x:68; y:16; width:parent.width-240; text:modelData.name; font.pixelSize:root.style.font32; color:root.style.textPrimary; font.weight:root.style.headingWeight; elide:Text.ElideRight }
            AppText { style:root.style; x:68; y:65; width:parent.width-88; text:!modelData.selectable ? (modelData.state==="blocked" ? "Bloccato dopo un errore · " : "Pacchetto non disponibile · ")+(modelData.reason || "Verifica richiesta") : root.controller.themeService && modelData.id===root.controller.themeService.activeThemeId ? "Tema attualmente visibile" : modelData.coverageSummary || "Tema disponibile sul dispositivo"; font.pixelSize:root.style.font22; color:root.style.textSecondary; elide:Text.ElideRight }
            AppText { style:root.style; anchors.right:parent.right; anchors.rightMargin:20; y:21; text:root.operation.busy && root.operation.targetId===modelData.id ? "Verifica…" : !modelData.selectable ? (modelData.state==="blocked" ? "Verifica" : "Errore") : root.controller.themeService && modelData.id===root.controller.themeService.savedThemeId ? "Attivo" : selectedState ? "Attiva" : ""; font.pixelSize:root.style.font25; color:root.style.accentTextOnCard }
            MouseArea { anchors.fill:parent; onClicked:root.controller.activateThemeChoice(parent.index) }
        }
    }
    AppText {
        style:root.style; x:24; y:494; width:912; height:92; visible:root.showIncident
        text:(root.incidentRow.version || "Versione non registrata")+" bloccata · "+
             (root.incidentRow.failedAt ? new Date(root.incidentRow.failedAt*1000).toLocaleString(Qt.locale("it_IT")) : "Data non registrata")+
             "\n"+(root.incidentRow.reason || "Pacchetto non disponibile")
        font.pixelSize:root.style.font20; color:root.style.textSecondary
        wrapMode:Text.WordWrap; maximumLineCount:3; elide:Text.ElideRight
    }
    AppText { style:root.style; x:24; y:592; width:912; visible:!!root.operation.message && !root.operation.busy; text:root.operation.message || ""; font.pixelSize:root.style.font22; color:root.style.textSecondary; elide:Text.ElideRight }
}
