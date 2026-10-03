import QtQuick
import "FallbackAppearance.js" as Fallback

StyleFacade {
    property string mode: "small"
    readonly property string prefix: "notifications." + mode + "."
    readonly property var notificationTokens: appearance ? tokens : Fallback.base.tokens
    readonly property color surfaceColor: notificationTokens[prefix+"surface"]
    readonly property color noticeFocusedSurface: notificationTokens[prefix+"focusedSurface"] || surfaceColor
    readonly property color titleColor: notificationTokens[prefix+"titleColor"]
    readonly property color bodyColor: notificationTokens[prefix+"bodyColor"]
    readonly property color sourceColor: notificationTokens[prefix+"sourceColor"]
    readonly property color noticeAccent: notificationTokens[prefix+"accent"]
    readonly property color noticeBorder: notificationTokens[prefix+"borderColor"]
    readonly property int noticeRadius: notificationTokens[prefix+"radius"]
    readonly property int noticeBorderWidth: notificationTokens[prefix+"borderWidth"]
    readonly property int padding: notificationTokens[prefix+"padding"]
    readonly property int gap: notificationTokens[prefix+"gap"]
    readonly property int panelWidth: notificationTokens[prefix+"width"]
    readonly property int panelHeight: notificationTokens[prefix+"height"]
    readonly property int insetX: notificationTokens[prefix+"insetX"]
    readonly property int insetY: notificationTokens[prefix+"insetY"]
    readonly property string anchor: notificationTokens[prefix+"anchor"]
    readonly property int titleSize: Math.round(notificationTokens[prefix+"titleSize"] * textScale)
    readonly property int bodySize: Math.round(notificationTokens[prefix+"bodySize"] * textScale)
    readonly property int sourceSize: Math.round(notificationTokens[prefix+"sourceSize"] * textScale)
    readonly property int guideSize: Math.round(notificationTokens[prefix+"guideSize"] * textScale)
    readonly property string titleFamily: notificationTokens[prefix+"titleFamily"] || uiFamily
    readonly property string bodyFamily: notificationTokens[prefix+"bodyFamily"] || uiFamily
    readonly property string sourceFamily: notificationTokens[prefix+"sourceFamily"] || uiFamily
    readonly property string guideFamily: notificationTokens[prefix+"guideFamily"] || uiFamily
    readonly property int titleWeight: notificationTokens[prefix+"titleWeight"]
    readonly property int noticeBodyWeight: notificationTokens[prefix+"noticeBodyWeight"]
    readonly property int titleLines: notificationTokens[prefix+"titleLines"]
    readonly property int bodyLines: notificationTokens[prefix+"bodyLines"]
    readonly property bool showIcon: notificationTokens[prefix+"showIcon"]
    readonly property bool showSource: notificationTokens[prefix+"showSource"]
    readonly property int noticeRows: notificationTokens[prefix+"rows"]
    readonly property real layoutY: anchor === "top" ? insetY : anchor === "bottom" ? 640-panelHeight-insetY : (640-panelHeight)/2+insetY
}
