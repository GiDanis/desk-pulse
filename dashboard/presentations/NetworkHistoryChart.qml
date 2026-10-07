import QtQuick
Item {
    id:root
    required property var chart
    required property var visualStyle
    readonly property var series:chart.series
    readonly property var drawing: {
        const result=[]
        for (let i=0;i<series.count;i++) {
            const s=series.get(i),points=[]
            for (let j=0;j<s.points.count;j++) { const p=s.points.get(j);points.push({time:p.time,value:p.value,broken:p.breakBefore}) }
            result.push({label:s.label,unit:s.unit,gaps:s.gaps,points:points})
        }
        return result
    }
    function formatted(value,unit) {
        if (unit==="bit/s") return value>=1e9 ? (value/1e9).toFixed(2)+" Gbit/s" : value>=1e6 ? (value/1e6).toFixed(2)+" Mbit/s" : (value/1000).toFixed(1)+" kbit/s"
        return value.toFixed(1)+" "+unit
    }
    onDrawingChanged: canvas.requestPaint()
    CasaLabel { visualStyle:root.visualStyle; width:parent.width;font.pixelSize:visualStyle.font20;text:root.chart.period+(root.chart.previous ? " · PRECEDENTE" : "") }
    Canvas {
        id:canvas;x:60;y:46;width:parent.width-80;height:parent.height-110
        onWidthChanged:requestPaint()
        onHeightChanged:requestPaint()
        onPaint: {
            const ctx=getContext("2d");ctx.reset()
            let maximum=0
            for (const s of root.drawing) for (const p of s.points) if (p.value!==null && p.value!==undefined) maximum=Math.max(maximum,p.value)
            maximum=maximum>0 ? maximum : 1
            ctx.strokeStyle=root.visualStyle.border;ctx.lineWidth=1
            for (let i=0;i<4;i++) { const y=height*i/3;ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(width,y);ctx.stroke() }
            for (let i=0;i<root.drawing.length;i++) {
                ctx.strokeStyle=i===0 ? root.visualStyle.accent : root.visualStyle.textSecondary;ctx.lineWidth=3;ctx.beginPath();let started=false
                for (const p of root.drawing[i].points) {
                    if (p.value===null || p.value===undefined) { started=false;continue }
                    const x=width*(p.time-root.chart.start)/Math.max(1,root.chart.end-root.chart.start),y=height*(1-p.value/maximum)
                    if (!started || p.broken) ctx.moveTo(x,y);else ctx.lineTo(x,y)
                    started=true
                }
                ctx.stroke()
            }
            ctx.fillStyle=root.visualStyle.textSecondary;ctx.font="16px sans-serif";ctx.fillText(root.formatted(maximum,root.chart.unit),2,18);ctx.fillText("0",2,height-4)
        }
    }
    CasaLabel { visualStyle:root.visualStyle;y:parent.height-55;width:parent.width;font.pixelSize:visualStyle.font18;text:root.drawing.map(s=>s.label+" · "+s.gaps+" buchi").join("  /  ") }
    CasaLabel { visualStyle:root.visualStyle;y:parent.height-28;width:parent.width;font.pixelSize:visualStyle.font18;color:visualStyle.textSecondary;text:root.chart.message+" · valori nella risoluzione RRD disponibile" }
}
