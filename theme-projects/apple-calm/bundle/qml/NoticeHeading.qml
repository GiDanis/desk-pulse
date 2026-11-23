pragma ComponentBehavior: Bound
import QtQuick
import "Format.js" as Format
Item {
    id:root
    property var themeStyle:null
    property var eventData:null
    property string heading:eventData ? eventData.title : "Avviso"
    property bool showIcon:true
    property bool compact:false
    property real trailingWidth:0
    property color accent:themeStyle ? themeStyle.semantic.accentTextOnCard : "#0066CC"
    implicitHeight:78
    OutlineIcon { x:0;y:root.compact ? 6 : 16;opticalSize:36;symbol:Format.noticeIcon(root.eventData);tint:root.accent;visible:root.showIcon }
    Label { objectName:"notificationTitle";x:root.showIcon ? 56 : 0;y:0;width:parent.width-x-root.trailingWidth;height:44;themeStyle:root.themeStyle;size:28;font.weight:Font.DemiBold;text:root.heading;maximumLineCount:1 }
    Label {
        x:root.showIcon ? 56 : 0;y:42;width:parent.width-x;height:32
        themeStyle:root.themeStyle;size:22;secondary:true;maximumLineCount:1;visible:!root.compact
        text:root.eventData ? [Format.noticePriority(root.eventData) || Format.noticeCategory(root.eventData),root.eventData.sourceLabel,Format.stamp(root.eventData.issuedAt),root.eventData.cancelled || root.eventData.expired ? Format.noticeState(root.eventData) : ""].filter(Boolean).join(" · ") : "Centro avvisi"
    }
}
