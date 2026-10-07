pragma ComponentBehavior: Bound
import QtQuick

Item {
    id: root
    property var context: null
    property var tabs: null
    property string currentLabel: ""
    readonly property var style: context ? context.style : null
    implicitHeight: 44
    Row {
        spacing: 8
        Repeater {
            model: root.tabs
            delegate: Rectangle {
                id: tab
                required property var item
                readonly property bool selected: root.context && root.context.selection && item.id === root.context.selection.tabId
                width: Math.max(40, (root.width - 8 * Math.max(0, root.tabs.count-1)) / Math.max(1,root.tabs.count)); height: 38
                color: root.style ? selected ? root.style.surfaceFocused : root.style.surface : "#FFFFFF"
                radius: 12
                border.width: selected ? 2 : 1
                border.color: root.style ? selected ? root.style.semantic.focusIndicator : root.style.border : "#CDD2DA"
                Label { id: label; anchors.fill: parent; anchors.margins: 8; themeStyle: root.style; size: 18; text: tab.item.label; maximumLineCount: 1; horizontalAlignment: Text.AlignHCenter }
                MouseArea { anchors.fill: parent; enabled: tab.item.enabled && !!root.context; onClicked: root.context.requestAction("tabs.select", tab.item.id, {}) }
            }
        }
    }
    Label { anchors.fill: parent; themeStyle: root.style; secondary: true; size: 20; text: root.currentLabel; visible: !root.tabs || root.tabs.count === 0; maximumLineCount: 1 }
}
