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
    readonly property real maximum: {
        let value=0
        for (const s of drawing) for (const p of s.points)
            if (p.value!==null && p.value!==undefined) value=Math.max(value,p.value)
        return value>0 ? value : 1
    }
    CasaLabel { visualStyle:root.visualStyle; width:parent.width;font.pixelSize:visualStyle.font20;text:root.chart.period+(root.chart.previous ? " · PRECEDENTE" : "") }
    Canvas {
        id:canvas;x:60;y:46;width:parent.width-80;height:parent.height-110
        onWidthChanged:requestPaint()
        onHeightChanged:requestPaint()
        onPaint: {
            const ctx=getContext("2d");ctx.reset()
            const maximum=root.maximum
            ctx.strokeStyle=root.visualStyle.border;ctx.lineWidth=1
            for (let i=0;i<4;i++) { const y=height*i/3;ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(width,y);ctx.stroke() }
            for (let i=0;i<root.drawing.length;i++) {
                ctx.strokeStyle=i===0 ? root.visualStyle.accent : root.visualStyle.textSecondary;ctx.lineWidth=3;ctx.setLineDash(i===0 ? [] : [8,6]);ctx.beginPath();let started=false
                for (const p of root.drawing[i].points) {
                    if (p.value===null || p.value===undefined) { started=false;continue }
                    const x=width*(p.time-root.chart.start)/Math.max(1,root.chart.end-root.chart.start),y=height*(1-p.value/maximum)
                    if (!started || p.broken) ctx.moveTo(x,y);else ctx.lineTo(x,y)
                    started=true
                }
                ctx.stroke()
            }
            ctx.setLineDash([])
        }
    }
    // QML resolves bundled/system font families on EGLFS consistently with
    // the rest of the view; Canvas CSS font parsing does not resolve Qt aliases.
    CasaLabel {
        objectName:"networkChartMaximum"
        visualStyle:root.visualStyle;x:canvas.x+2;y:canvas.y+2;width:canvas.width-4
        font.pixelSize:visualStyle.font22;color:visualStyle.textSecondary
        text:root.formatted(root.maximum,root.chart.unit)
    }
    CasaLabel {
        objectName:"networkChartZero"
        visualStyle:root.visualStyle;x:canvas.x+2;y:canvas.y+canvas.height-height-4;width:canvas.width-4
        font.pixelSize:visualStyle.font22;color:visualStyle.textSecondary;text:"0"
    }
    CasaLabel { visualStyle:root.visualStyle;y:parent.height-55;width:parent.width;font.pixelSize:visualStyle.font22;text:root.drawing.map(s=>(root.drawing.indexOf(s)===0 ? "━ " : "┄ ")+s.label+" · "+s.gaps+" buchi").join("  /  ") }
    CasaLabel { visualStyle:root.visualStyle;y:parent.height-28;width:parent.width;font.pixelSize:visualStyle.font22;color:visualStyle.textSecondary;text:root.chart.message+" · valori nella risoluzione RRD disponibile" }
}
