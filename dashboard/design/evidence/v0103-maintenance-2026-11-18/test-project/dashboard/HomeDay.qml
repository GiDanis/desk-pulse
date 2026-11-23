import QtQuick
import "themes"
import "components"
Item {
    id:visualRoot
    property StyleFacade style:Theme
    required property var dashboard
    width:872;height:455
    AppText { style:visualRoot.style;y:3;width:parent.width;text:dashboard.dateText();color:visualRoot.style.textPrimary;font.pixelSize:visualRoot.style.font46;elide:Text.ElideRight }
    InfoCard { style:visualRoot.style;x:0;y:94;width:parent.width;height:dashboard.hasEvent ? parent.height-267 : parent.height-94;heading:"IL TEMPO OGGI";value:dashboard.weatherData.temperature || "Meteo non disponibile";detail:(dashboard.weatherData.description || "")+" · "+dashboard.weatherStatus();compact:!dashboard.weatherData.temperature }
    InfoCard { style:visualRoot.style;x:0;y:parent.height-157;width:parent.width;height:157;visible:dashboard.hasEvent;heading:"PROSSIMO EVENTO";value:dashboard.nextEvent.title || "";detail:dashboard.nextEvent.when || dashboard.eventWhen(dashboard.nextEvent);compact:true }
}
