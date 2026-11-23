import QtQml
QtObject {
    id: receipt
    required property var ctx
    required property string action
    property string target: ""
    property var result: null
    property int attempts: 0
    property double retryAt: 0
    property bool blocked: false
    readonly property bool committed: !!result && result.accepted && result.status === "completed"
    readonly property string errorText: blocked ? "Aggiornamento non riuscito · riapri l’Acquario per riprovare" : ""
    onTargetChanged: { result=null; attempts=0; retryAt=0; blocked=false }
    function tick() {
        if (committed) return true
        if (blocked || !target || !ctx) return false
        if (result && result.status === "pending") return false
        const now=Date.now()
        if (result) {
            result=null
            if (attempts>=3) { blocked=true; return false }
            retryAt=now+Math.min(5000,1000*Math.pow(2,Math.max(0,attempts-1)))
        }
        if (now<retryAt) return false
        const next=ctx.requestAction(action,target,{})
        if (next.accepted) { attempts++; result=next }
        else retryAt=now+1000
        return committed
    }
}
