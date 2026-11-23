import QtQuick

Item {
    id: hud
    objectName:"gameTimingHud"
    property var timing: ({})
    property string pilot: ""
    property var learning: ({})
    property real factor: 1
    property color ink: "white"
    property color muted: "gray"
    property color accent: "cyan"
    property string uiFont: "Sans Serif"
    property string numberFont: "Sans Serif"
    readonly property var last:timing.last || ({})
    readonly property var pb:timing.personal || ({})
    readonly property bool preview:timing.source === "preview"
    readonly property bool candidate:preview && learning.previewRole === "candidate"
    function lap(value) {
        if (value === null || value === undefined) return "—"
        const ms=Math.round(Number(value)*1000)
        return Math.floor(ms/60000)+":"+String(Math.floor(ms%60000/1000)).padStart(2,"0")+","+String(ms%1000).padStart(3,"0")
    }
    function delta(value) {
        if (value === null || value === undefined) return "—"
        return (Number(value)<-0.0005 ? "−" : "+")+Math.abs(Number(value)).toFixed(3).replace(".",",")
    }
    Text { x:0;y:0;width:parent.width;height:28*hud.factor;text:hud.pilot+" · "+(hud.candidate ? "Candidato · prova "+hud.learning.previewTrial : hud.preview ? "Campione in anteprima" : hud.timing.source === "qualifica" ? "Qualifica" : "Gara");horizontalAlignment:Text.AlignHCenter;elide:Text.ElideRight;color:hud.muted;font.family:hud.uiFont;font.pixelSize:20*hud.factor }
    Repeater {
        model:2
        delegate:Item {
            required property int index
            x:index*hud.width/2;y:36*hud.factor;width:hud.width/2;height:76*hud.factor
            Text { width:parent.width;height:26*hud.factor;text:index===0 ? hud.candidate ? "Migliore prove" : hud.preview ? "PB anteprima" : hud.pb.policy && hud.pb.policy !== hud.timing.policy ? "PB · altro modello" : "Personale" : hud.last.partial ? "Parziale" : hud.last.standingStart ? "Lancio" : "Ultimo giro";color:hud.muted;horizontalAlignment:Text.AlignHCenter;font.family:hud.uiFont;font.pixelSize:20*hud.factor }
            Text { y:28*hud.factor;width:parent.width;height:45*hud.factor;text:hud.lap(index===0 ? hud.pb.time : hud.last.time);color:hud.ink;horizontalAlignment:Text.AlignHCenter;font.family:hud.numberFont;font.pixelSize:34*hud.factor;fontSizeMode:Text.HorizontalFit;minimumPixelSize:26 }
        }
    }
    Text { x:hud.width/2;y:108*hud.factor;width:hud.width/2;height:24*hud.factor;text:hud.last.clean === false ? "Non valido" : hud.last.standingStart ? "Escluso dal personale" : hud.last.personalDelta !== null && hud.last.personalDelta !== undefined ? hud.delta(hud.last.personalDelta)+" s" : "";horizontalAlignment:Text.AlignHCenter;color:hud.last.personalDelta<0 ? hud.accent : hud.muted;font.family:hud.numberFont;font.pixelSize:18*hud.factor }
    Rectangle { x:0;y:139*hud.factor;width:parent.width;height:1;color:hud.muted;opacity:0.22 }
    Repeater {
        model:3
        delegate:Item {
            required property int index
            x:index*hud.width/3;y:147*hud.factor;width:hud.width/3;height:54*hud.factor
            readonly property var value:(hud.timing.deltas || [])[index]
            Text { width:parent.width;height:25*hud.factor;text:"S"+(index+1);color:hud.muted;horizontalAlignment:Text.AlignHCenter;font.family:hud.uiFont;font.pixelSize:19*hud.factor }
            Text { y:25*hud.factor;width:parent.width;height:30*hud.factor;text:hud.delta(parent.value);color:parent.value!==null && parent.value!==undefined && Number(parent.value)<0 ? hud.accent : hud.ink;horizontalAlignment:Text.AlignHCenter;font.family:hud.numberFont;font.pixelSize:24*hud.factor }
        }
    }
    Text { x:0;y:207*hud.factor;width:parent.width;height:25*hud.factor;text:hud.candidate ? "Rete "+hud.learning.previewUpdate+" · "+(hud.learning.lastDecision ? "Verifica "+hud.learning.verification+" · "+(hud.learning.lastDelta === null ? "giri insufficienti" : hud.delta(hud.learning.lastDelta)+" s") : "Nessuna verifica conclusa") : "G"+(hud.timing.sectorLap || 1)+" · "+(hud.timing.referenceLabel || "Settori da misurare");color:hud.muted;horizontalAlignment:Text.AlignHCenter;elide:Text.ElideRight;font.family:hud.uiFont;font.pixelSize:17*hud.factor }
}
