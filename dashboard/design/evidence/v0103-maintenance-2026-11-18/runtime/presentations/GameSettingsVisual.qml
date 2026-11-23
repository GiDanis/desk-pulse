import QtQuick

Item {
    id: root
    required property var ctx
    readonly property var visual: ctx.style
    readonly property var settings: ctx.game.settings || ({})
    readonly property var rows: ctx.rows || []
    readonly property real factor: visual.textScale
    readonly property int selected: ctx.selectedIndex || 0
    readonly property var last: rows[rows.length-1] || ({})
    readonly property bool footer: last.id === "start" || last.id === "apply"
    readonly property int count: rows.length-(footer ? 1 : 0)
    readonly property int page: Math.floor(Math.min(selected,Math.max(0,count-1))/3)
    readonly property real rowsTop: settings.tabs ? height>600 ? 176 : 156 : height>600 ? 136 : 112
    readonly property real rowHeight: Math.min(104,(height-rowsTop-118)/3)
    function action(id) { if (ctx.lifecycle.interactive) ctx.requestAction("game.option.activate",id,{}) }
    Rectangle { anchors.fill:parent;color:root.visual.background }
    Row {
        x:24;y:12;spacing:16;visible:!!root.settings.tabs
        Repeater { model:[{id:"session",label:"Sessione"},{id:"training",label:"Allenamento"},{id:"management",label:"Gestione"}]
            delegate:Rectangle {
                required property var modelData
                width:(root.width-80)/3;height:48;radius:root.visual.radiusPill
                color:root.settings.section===modelData.id ? root.visual.surfaceFocused : root.visual.surface
                Text { anchors.fill:parent;text:parent.modelData.label;color:root.settings.section===parent.modelData.id ? root.visual.accent : root.visual.textPrimary;font.family:root.visual.uiFamily;font.pixelSize:23*root.factor;font.weight:root.settings.section===parent.modelData.id ? Font.DemiBold : Font.Normal;horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter }
                MouseArea { anchors.fill:parent;onClicked:root.action("section:"+parent.modelData.id) }
            }
        }
    }
    Text { x:24;y:root.settings.tabs ? 70 : 12;width:parent.width-48;height:42;text:root.settings.title || "Impostazioni";color:root.visual.textPrimary;font.family:root.visual.uiFamily;font.pixelSize:28*root.factor;font.weight:Font.DemiBold;elide:Text.ElideRight;verticalAlignment:Text.AlignVCenter }
    Text { objectName:"gameSettingsState";x:24;y:root.settings.tabs ? 114 : 58;width:parent.width-48;height:root.rowsTop-y-6;text:root.settings.subtitle || "";color:root.visual.textSecondary;font.family:root.visual.uiFamily;font.pixelSize:19*root.factor;wrapMode:Text.Wrap;maximumLineCount:2;elide:Text.ElideRight }
    Repeater {
        model:3
        delegate:Rectangle {
            id: entry
            required property int index
            readonly property int realIndex:root.page*3+index
            readonly property var row:root.rows[realIndex] || ({})
            readonly property bool picked:realIndex===root.selected
            visible:realIndex<root.count && row.id !== undefined
            objectName:"gameListRow"+realIndex
            x:24;y:root.rowsTop+index*(root.rowHeight+8);width:root.width-48;height:root.rowHeight
            radius:root.visual.radiusRow;color:picked ? root.visual.surfaceFocused : root.visual.surface
            border.color:picked ? root.visual.accent : root.visual.border;border.width:picked ? 3 : 1
            opacity:row.enabled===false ? .65 : 1
            Text { x:18;y:8;width:parent.width-312;height:34;text:entry.row.title || "";color:root.visual.textPrimary;font.family:root.visual.uiFamily;font.pixelSize:25*root.factor;font.weight:Font.DemiBold;elide:Text.ElideRight;verticalAlignment:Text.AlignVCenter }
            Rectangle { x:parent.width-292;y:4;width:274;height:40;color:"transparent";radius:root.visual.radiusButton;border.color:root.visual.accent;border.width:root.settings.editing && entry.picked ? 2 : 0 }
            Text { objectName:"gameSettingValue"+entry.realIndex;x:parent.width-282;y:8;width:264;height:34;text:entry.row.value || "";color:entry.picked ? root.visual.accent : root.visual.textPrimary;font.family:root.visual.numbersFamily;font.pixelSize:23*root.factor;horizontalAlignment:Text.AlignRight;elide:Text.ElideRight;verticalAlignment:Text.AlignVCenter }
            Text { objectName:"gameSettingDescription"+entry.realIndex;x:18;y:44;width:parent.width-36;height:parent.height-50;text:entry.row.description || "";color:root.visual.textSecondary;font.family:root.visual.uiFamily;font.pixelSize:19*root.factor;wrapMode:Text.Wrap;maximumLineCount:2;elide:Text.ElideRight }
            MouseArea { anchors.fill:parent;enabled:entry.row.enabled!==false;onClicked:root.action(entry.row.id) }
        }
    }
    Rectangle {
        id: primary
        visible:root.footer
        objectName:"gameSettingsPrimary"
        x:24;y:parent.height-100;width:parent.width-48;height:80;radius:root.visual.radiusButton
        color:root.selected===root.rows.length-1 ? root.visual.surfaceFocused : root.visual.surface
        border.color:root.selected===root.rows.length-1 ? root.visual.accent : root.visual.border
        border.width:root.selected===root.rows.length-1 ? 3 : 1
        opacity:root.last.enabled===false ? .65 : 1
        Text { x:18;y:8;width:parent.width-150;height:32;text:root.last.title || "";color:root.visual.textPrimary;font.family:root.visual.uiFamily;font.pixelSize:24*root.factor;font.weight:Font.DemiBold;elide:Text.ElideRight }
        Text { x:18;y:43;width:parent.width-36;height:29;text:root.last.description || "";color:root.visual.textSecondary;font.family:root.visual.uiFamily;font.pixelSize:18*root.factor;elide:Text.ElideRight }
        Text { x:parent.width-156;y:8;width:138;height:32;text:root.last.value || "";color:root.visual.accent;font.family:root.visual.uiFamily;font.pixelSize:22*root.factor;horizontalAlignment:Text.AlignRight;elide:Text.ElideRight }
        MouseArea { anchors.fill:parent;enabled:root.last.enabled!==false;onClicked:root.action(root.last.id) }
    }
    Text { x:24;y:root.footer ? parent.height-128 : parent.height-52;width:parent.width-48;height:26;visible:root.count>3;text:(root.page+1)+" / "+Math.ceil(root.count/3);color:root.visual.textSecondary;font.family:root.visual.numbersFamily;font.pixelSize:18*root.factor;horizontalAlignment:Text.AlignRight }
}
