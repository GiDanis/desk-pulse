pragma ComponentBehavior: Bound
import QtQuick
import SmartPC.ThemeApi 2.0
import "Format.js" as Format

Notice {
    id: root
    required property NotificationContext context
    ctx: context
    mode: "inbox"
}
