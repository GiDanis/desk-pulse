pragma ComponentBehavior: Bound
import QtQuick
import "Format.js" as Format
Card {
    id:root
    required property var eventData
    property var context:null
    property bool selected:false
    style:context ? context.style : null
    color:selected && style ? style.surfaceFocused : style ? style.surface : "#FFFFFF"
    border.width:selected ? 3 : 0
    border.color:style ? style.semantic.focusIndicator : "#0066CC"
    OutlineIcon { x:20;y:44;opticalSize:32;symbol:Format.noticeIcon(root.eventData);tint:root.style ? root.style.semantic.accentTextOnCard : "#0066CC" }
    Label {
        x:72;y:10;width:parent.width-94;height:30;themeStyle:root.style;size:22;secondary:true;maximumLineCount:1
        text:[root.eventData.cancelled || root.eventData.expired ? Format.noticeState(root.eventData) : root.eventData.seen ? "Letto" : "Non letto",Format.noticeCategory(root.eventData),root.eventData.sourceLabel,Format.stamp(root.eventData.issuedAt)].filter(Boolean).join(" · ")
    }
    Label { x:72;y:42;width:parent.width-94;height:42;themeStyle:root.style;size:28;font.weight:Font.Medium;text:root.eventData.title;maximumLineCount:1 }
    Label { x:72;y:86;width:parent.width-94;height:36;themeStyle:root.style;size:24;secondary:true;text:root.eventData.body;maximumLineCount:1 }
    MouseArea { anchors.fill:parent;enabled:root.context && root.context.interactive;onClicked:{root.context.request("selectEvent",root.eventData.id,{});root.context.request("openDetails",root.eventData.id,{})} }
}
