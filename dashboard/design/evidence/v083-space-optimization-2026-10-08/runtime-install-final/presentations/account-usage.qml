import QtQuick
import ".."
import "../themes"

AccountChatGPT {
    required property var context
    dashboard: context.controller
    style: context.style
}
