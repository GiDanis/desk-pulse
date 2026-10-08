pragma Singleton
import QtQuick
import "FallbackAppearance.js" as Fallback

StyleFacade {
    property var service: null
    appearance: service ? service.resolvedAppearance : Fallback.make(fallbackNight)
    readonly property var presentations: appearance ? appearance.presentations : ({})
    readonly property var motion: appearance ? appearance.motion : ({})
    readonly property var icons: appearance ? appearance.icons : ({})
    readonly property string motionMode: appearance ? appearance.motionMode : "normal"
}
