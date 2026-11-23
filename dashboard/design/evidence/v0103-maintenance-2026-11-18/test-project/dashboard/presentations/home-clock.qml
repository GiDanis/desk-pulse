import QtQuick
import ".."
import "../components"

Item {
    required property var context
    readonly property var style: context.style
    AppText { x:0; y:12; width:parent.width; height:48; style:parent.style; text:context.dateText; font.pixelSize:25; horizontalAlignment:Text.AlignHCenter; color:style.textSecondary }
    AppText { x:0; y:65; width:parent.width; height:250; style:parent.style; text:context.clockText; font.pixelSize:230; font.family:style.numbersFamily; horizontalAlignment:Text.AlignHCenter; color:style.textPrimary; fontSizeMode:Text.Fit; minimumPixelSize:140 }
    AppText { x:0; y:parent.height-94; width:parent.width; height:70; style:parent.style; text:context.controller ? (context.controller.weatherData.temperature || "Meteo non disponibile") + " · " + context.controller.weatherStatus() : "Meteo non disponibile"; font.pixelSize:28; horizontalAlignment:Text.AlignHCenter; color:style.textSecondary; wrapMode:Text.WordWrap }
}
