import QtQuick
// App-owned: a candidate's fonts, components and scene are never dependencies.
Rectangle {
    id:loading
    required property var controller
    property bool delayElapsed:false
    readonly property var operation:controller.themeOperation || ({})
    readonly property bool preparing:!!controller.themeCandidate.generation || !!operation.busy
    readonly property var tokens:operation.busy ? operation.palette || ({}) : controller.style.tokens
    readonly property color ink:tokens["colors.textPrimary"] || "#ffffff"
    readonly property color muted:tokens["colors.textSecondary"] || "#bdcbd3"
    readonly property color accent:tokens["colors.accent"] || "#6de0be"
    readonly property string phase:operation.busy ? operation.phase : "preparing"
    readonly property string motionMode:operation.busy ? operation.motionMode : controller.style.appearance.motionMode
    readonly property bool animate:visible && motionMode==="normal"
    objectName:"themeLoading"
    anchors.fill:parent
    color:tokens["colors.background"] || "#17242d"
    visible:preparing && delayElapsed && !controller.urgentEvent.id && controller.overlay!=="menu"
    onPreparingChanged: {delayElapsed=false;if(preparing) showDelay.restart();else showDelay.stop()}
    Timer {id:showDelay;interval:120;onTriggered:loading.delayElapsed=true}
    Text {x:24;y:13;text:"Aspetto";font.pixelSize:26;color:loading.ink}
    Rectangle {x:24;y:55;width:912;height:1;color:loading.muted;opacity:0.25}
    Rectangle {x:24;y:88;width:912;height:536;radius:18;color:loading.tokens["colors.surface"] || "#20303b"}
    Item {
        x:450;y:170;width:60;height:60
        Rectangle {anchors.fill:parent;radius:30;color:"transparent";border.width:4;border.color:loading.accent;opacity:0.2}
        Item {anchors.fill:parent
            Rectangle {x:26;y:0;width:8;height:8;radius:4;color:loading.accent}
            RotationAnimator on rotation {from:0;to:360;duration:1300;loops:Animation.Infinite;running:loading.animate}
        }
    }
    Text {x:48;y:265;width:864;horizontalAlignment:Text.AlignHCenter;text:loading.operation.busy ? "Attivazione di "+loading.operation.targetName : "Preparazione del tema…";color:loading.ink;font.pixelSize:34;elide:Text.ElideRight}
    Text {x:48;y:320;width:864;horizontalAlignment:Text.AlignHCenter;text:loading.operation.busy ? loading.operation.message : "Le schermate saranno visibili appena pronte.";color:loading.muted;font.pixelSize:24;elide:Text.ElideRight}
    Row {
        x:120;y:402;spacing:28
        Repeater {model:["Preparazione","Schermata","Salvataggio"]
            delegate:Text {
                required property string modelData
                required property int index
                readonly property int step:loading.phase==="saving" || loading.phase==="finishing" ? 2 : loading.phase==="presenting" ? 1 : 0
                width:220;horizontalAlignment:Text.AlignHCenter;text:modelData
                color:index<=step ? loading.accent : loading.muted;font.pixelSize:22;font.bold:index===step
            }
        }
    }
    Text {x:48;y:536;width:864;horizontalAlignment:Text.AlignHCenter;text:loading.phase==="saving" || loading.phase==="finishing" ? "Completamento del salvataggio…" : "7 Annulla";color:loading.muted;font.pixelSize:22}
    MouseArea {anchors.fill:parent}
}
