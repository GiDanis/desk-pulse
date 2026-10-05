import QtQuick
import "../themes"
Item {
    id: root
    property StyleFacade style: Theme
    property string iconId: "status.unavailable"
    property color tint: style.accent
    property int opticalSize: 32
    property var appearance: style.appearance
    property var resourceService: Theme.service
    property string resourceLease: ""
    property string resourceError: ""
    function releaseResource() { if (resourceLease && resourceService) resourceService.releaseRevision(resourceLease); resourceLease="" }
    Component.onDestruction: releaseResource()
    readonly property var descriptor: appearance && appearance.icons[iconId] ? appearance.icons[iconId] : "unknown"
    readonly property string backend: typeof descriptor === "string" ? "geometry" : descriptor.backend
    readonly property string symbol: typeof descriptor === "string" ? descriptor : descriptor.symbol || "unknown"
    readonly property string lastError: resourceError || (assetImage.status === Image.Error ? "Icona non disponibile: " + iconId : "")
    readonly property string assetFile: {
        if (!appearance || backend !== "image") return ""
        const asset = appearance.assets.find(a => a.id === descriptor.asset)
        return asset ? "file://" + asset.file : ""
    }
    width: opticalSize; height: opticalSize
    Text { anchors.fill: parent; visible: root.backend === "glyph"; font.family: root.backend === "glyph" ? root.descriptor.family : ""; font.pixelSize: root.opticalSize; text: root.backend === "glyph" ? root.descriptor.glyph : ""; color: root.tint; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
    Image { id: assetImage; anchors.fill: parent; visible: root.backend === "image" && status === Image.Ready; source: root.assetFile; sourceSize: Qt.size(root.opticalSize,root.opticalSize); fillMode: Image.PreserveAspectFit; asynchronous: true; cache: true }
    Loader {
        id: renderer
        anchors.fill: parent
        active: root.visible && (root.backend === "geometry" || root.backend === "component" || root.backend === "image" && assetImage.status !== Image.Ready)
        readonly property string rendererId: root.backend === "component" ? root.descriptor.renderer : "builtin.geometry"
        readonly property var rendererDescriptor: root.appearance ? root.appearance.iconRegistry[rendererId] : null
        readonly property string rendererKey: rendererDescriptor ? rendererDescriptor.rendererKey || rendererDescriptor.file : "builtin.geometry"
        onRendererKeyChanged: load()
        readonly property string rendererFile: root.appearance && root.appearance.iconRegistry[rendererId] ? root.appearance.iconRegistry[rendererId].file : "icons/GeometryIcon.qml"
        onActiveChanged: if (active) load()
        Component.onCompleted: if (active) load()
        function load() {
            if (!active) return
            root.releaseResource()
            root.resourceError=""
            if (root.resourceService && rendererDescriptor && rendererDescriptor.rendererIdentity) root.resourceLease=root.resourceService.acquireRevision(rendererDescriptor.rendererIdentity)
            if (rendererDescriptor && rendererDescriptor.rendererIdentity && root.resourceService && !root.resourceLease) {
                root.resourceError="Risorsa icona non disponibile: "+root.iconId
                setSource("")
                return
            }
            setSource((root.appearance && root.appearance.iconRegistry[rendererId] ? root.appearance.iconRegistry[rendererId].sourceUrl : "") || Qt.resolvedUrl("../" + rendererFile), {style: root.style, iconId: root.iconId, descriptor: root.descriptor, symbol: assetImage.status === Image.Error ? "unknown" : root.symbol, tint: root.tint, opticalSize: root.opticalSize})
        }
        onLoaded: {
            item.iconId = Qt.binding(function() { return root.iconId })
            item.descriptor = Qt.binding(function() { return root.descriptor })
            item.style = Qt.binding(function() { return root.style })
            item.symbol = Qt.binding(function() { return assetImage.status === Image.Error ? "unknown" : root.symbol })
            item.tint = Qt.binding(function() { return root.tint })
            item.opticalSize = Qt.binding(function() { return root.opticalSize })
        }
    }
}
