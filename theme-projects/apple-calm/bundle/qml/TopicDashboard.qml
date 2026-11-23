pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.7

Item {
    id: root
    property var ctx: null
    readonly property var visualStyle: ctx ? ctx.style : null
    readonly property var summary: ctx ? ctx.dashboardSummary : null
    readonly property bool ready: !!ctx && width>0 && height>0
    readonly property bool contentReady: ready
    readonly property var cards: { if (!ctx || !summary) return [];ctx.dataRevision;const out=[];for (let i=0;i<summary.cards.count;i++) out.push(summary.cards.get(i));return out }
    readonly property bool spacious: visualStyle && visualStyle.textScale>1.05 && cards.length>3 && summary.id!=="casa-preferiti"
    readonly property bool compact:height<500
    readonly property int count:compact ? Math.min(2,cards.length) : spacious ? 3 : cards.length
    function bounds(i) {
        if(compact)return Qt.rect(i*464,0,cards.length===1 ? 912 : 448,504)
        if (spacious) return i===0 ? Qt.rect(0,0,400,504) : Qt.rect(416,(i-1)*260,496,244)
        const r=cards[i].rect;return Qt.rect(r.x,r.y,r.width,r.height)
    }
    function openDetails() { if (ctx && ctx.lifecycle.interactive) ctx.requestAction("details.open",ctx.contentId,{}) }
    Text {
        id:heading
        x:0;y:0;width:root.width*0.46;height:42
        text:root.summary ? root.summary.title : "Dashboard"
        color:root.visualStyle ? root.visualStyle.textPrimary : "white"
        font.family:root.visualStyle ? root.visualStyle.uiFamily : "Sans Serif"
        font.pixelSize:32*(root.visualStyle ? root.visualStyle.textScale : 1)
        elide:Text.ElideRight;verticalAlignment:Text.AlignVCenter
    }
    Text {
        x:Math.min(heading.width,Math.ceil(heading.contentWidth))+24;y:0;width:Math.max(0,root.width-x);height:42;horizontalAlignment:Text.AlignRight
        text:root.summary ? root.summary.subtitle : ""
        color:root.visualStyle ? root.visualStyle.textSecondary : "gray"
        font.family:root.visualStyle ? root.visualStyle.uiFamily : "Sans Serif"
        font.pixelSize:22*(root.visualStyle ? root.visualStyle.textScale : 1)
        elide:Text.ElideRight;verticalAlignment:Text.AlignVCenter
    }
    Repeater {
        model:root.count
        delegate:Rectangle {
            id:tile
            required property int index
            readonly property var entry:root.cards[index]
            readonly property rect area:root.bounds(index)
            readonly property bool tall:!root.compact && area.height>300
            readonly property real factor:root.visualStyle ? root.visualStyle.textScale : 1
            objectName:"dashboardCard"+index
            x:area.x*root.width/912;y:48+area.y*(root.height-48)/504
            width:area.width*root.width/912;height:area.height*(root.height-48)/504
            radius:root.visualStyle ? root.visualStyle.radiusCard : 24
            color:root.visualStyle ? root.visualStyle.surface : "#202228"
            border.width:0
            border.color:root.visualStyle ? root.visualStyle.border : "gray"
            OutlineIcon { x:20;y:22;opticalSize:30;symbol:tile.entry.icon;tint:root.visualStyle ? root.visualStyle.semantic.accentTextOnCard : "#0066CC" }
            Text {
                x:62;y:14;width:parent.width-x-20;height:tile.tall ? 74 : 60
                text:tile.entry.title;color:root.visualStyle ? root.visualStyle.textSecondary : "gray"
                font.family:root.visualStyle ? root.visualStyle.uiFamily : "Sans Serif";font.pixelSize:(tile.width<300 ? 23 : 25)*tile.factor
                wrapMode:Text.Wrap;maximumLineCount:2;elide:Text.ElideRight;verticalAlignment:Text.AlignVCenter
            }
            Text {
                id:subject
                x:24;y:tile.tall ? 106 : 76;width:parent.width-48;height:tile.tall ? 110 : 54
                visible:tile.tall && text.length>0;text:tile.entry.subtitle
                color:root.visualStyle ? root.visualStyle.textPrimary : "white"
                font.family:root.visualStyle ? root.visualStyle.uiFamily : "Sans Serif";font.pixelSize:(tile.tall ? 32 : 25)*tile.factor
                wrapMode:Text.Wrap;maximumLineCount:2;elide:Text.ElideRight;verticalAlignment:Text.AlignVCenter
            }
            Item {
                x:24;y:tile.tall ? (subject.visible ? 232 : 154) : 76;width:parent.width-48;height:tile.tall ? 118 : 80
                visible:tile.entry.id!=="history"
                readonly property bool hasUnit: unit.text.length>0
                readonly property bool unitFits: hasUnit && value.implicitWidth+unit.implicitWidth+10<=width
                Text {
                    id:value
                    width:parent.unitFits ? implicitWidth : parent.width
                    height:parent.hasUnit && !parent.unitFits ? implicitHeight : parent.height
                    text:tile.entry.value
                    color:root.visualStyle ? tile.entry.previous ? root.visualStyle.semantic.warningOnCard : root.visualStyle.textPrimary : "white"
                    font.family:root.visualStyle ? root.visualStyle.numbersFamily : "Sans Serif";font.weight:Font.DemiBold
                    font.features:({tnum:1})
                    font.pixelSize:Math.min(tile.entry.valueSize,(text.length>12 ? (tile.width<300 ? 25 : 28) : text.length>8 && tile.width<300 ? 30 : tile.entry.valueSize))*tile.factor
                    wrapMode:Text.Wrap;maximumLineCount:2;elide:Text.ElideRight;verticalAlignment:Text.AlignVCenter
                }
                Text {
                    id:unit
                    x:parent.unitFits ? value.width+10 : 0
                    y:parent.unitFits ? value.baselineOffset-baselineOffset : value.height+4
                    text:tile.entry.unit;color:root.visualStyle ? root.visualStyle.textSecondary : "gray"
                    font.family:root.visualStyle ? root.visualStyle.uiFamily : "Sans Serif";font.pixelSize:24*tile.factor
                    visible:parent.hasUnit
                }
            }
            Text {
                x:24;y:parent.height-(tile.tall ? 124 : 68);width:parent.width-48;height:tile.tall ? 106 : 54
                text:[tile.entry.previous && root.summary.id!=="casa-preferiti" ? "Precedente" : "",
                    tile.entry.detail,(!tile.tall && tile.width>300 ? tile.entry.subtitle : "")].filter(Boolean).join(" · ")
                color:root.visualStyle ? root.visualStyle.textSecondary : "gray"
                font.family:root.visualStyle ? root.visualStyle.uiFamily : "Sans Serif";font.pixelSize:(tile.width<300 ? 21 : 23)*tile.factor
                wrapMode:Text.Wrap;maximumLineCount:tile.tall ? 3 : 2;elide:Text.ElideRight;verticalAlignment:Text.AlignBottom
            }
            Loader {
                x:24;y:82;width:parent.width-48;height:72
                active:tile.entry.id==="history" && !!root.summary.chart
                sourceComponent:Component { MiniHistory { chart:root.summary ? root.summary.chart : null;visualStyle:root.visualStyle } }
            }
            Text {
                x:24;y:160;width:parent.width-48;height:30;visible:tile.entry.id==="history" && !root.compact
                text:"↓ Download   ↑ Upload tratteggiato";font.pixelSize:22*tile.factor
                font.family:root.visualStyle ? root.visualStyle.uiFamily : "Sans Serif";color:root.visualStyle ? root.visualStyle.textSecondary : "gray"
            }
            MouseArea { anchors.fill:parent;enabled:root.ctx && root.ctx.lifecycle.interactive;onClicked:root.openDetails() }
        }
    }
}
