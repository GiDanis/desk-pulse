import QtQuick
import "themes"
import "components"

Surface {
    id: card
    property string heading: ""
    property string value: ""
    property string detail: ""
    property bool compact: false
    property bool night: false
    radius: card.style.radiusCard
    color: card.style.surface
    border.color: card.style.border
    border.width: card.style.borderWidth
    AppText { style: card.style; x: card.style.spacing; y: 17; text: card.heading; color: card.style.accentTextOnCard; font.pixelSize: card.style.font24; font.weight: (true ) ? card.style.headingWeight : card.style.bodyWeight}
    AppText { style: card.style; x: card.style.spacing; y: Math.max(48,(card.height-95)/2); width: parent.width - 2 * card.style.spacing; text: card.value; color: card.style.textPrimary; font.pixelSize: card.value.length > 15 && card.width < 600 ? card.style.font30 : card.width < 400 ? card.style.font34 : card.compact ? card.style.font47 : card.style.font65; elide: Text.ElideRight }
    AppText { style: card.style; x: card.style.spacing; y: card.height-36; width: parent.width - 2 * card.style.spacing; text: card.detail; color: card.style.textSecondary; font.pixelSize: card.compact ? card.style.font18 : card.style.font20; elide: Text.ElideRight }
}
