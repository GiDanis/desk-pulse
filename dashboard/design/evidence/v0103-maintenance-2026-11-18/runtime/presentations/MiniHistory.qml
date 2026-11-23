import QtQuick
Canvas {
    id:root
    required property var chart
    required property var visualStyle
    readonly property var drawing: {
        const lines=[]
        if (!chart) return lines
        for (let i=0;i<chart.series.count;i++) {
            const series=chart.series.get(i),points=[]
            for (let j=0;j<series.points.count;j++) {const p=series.points.get(j);points.push({time:p.time,value:p.value,broken:p.breakBefore})}
            lines.push(points)
        }
        return lines
    }
    onDrawingChanged:requestPaint()
    onWidthChanged:requestPaint()
    onHeightChanged:requestPaint()
    onPaint: {
        const c=getContext("2d");c.reset();if (!chart) return;let maximum=0
        for (var a=0;a<root.drawing.length;a++) for (var b=0;b<root.drawing[a].length;b++) {var v=root.drawing[a][b].value;if (v!==null && v!==undefined && isFinite(v)) maximum=Math.max(maximum,v)}
        maximum=Math.max(maximum,1)
        c.strokeStyle=visualStyle.border;c.lineWidth=1
        for (let i=0;i<3;i++) {c.beginPath();c.moveTo(0,height*i/2);c.lineTo(width,height*i/2);c.stroke()}
        for (var k=0;k<root.drawing.length;k++) {
            c.strokeStyle=k===0 ? String(visualStyle.accent) : String(visualStyle.textSecondary);c.lineWidth=3;c.setLineDash(k===0 ? [] : [7,5]);c.beginPath();let started=false
            for (var j=0;j<root.drawing[k].length;j++) {
                var p=root.drawing[k][j]
                if (p.value===null || p.value===undefined || !isFinite(p.value)) {started=false;continue}
                const x=width*(p.time-chart.start)/Math.max(1,chart.end-chart.start),y=height*(1-p.value/maximum)
                if (!started || p.broken) c.moveTo(x,y);else c.lineTo(x,y)
                started=true
            }
            c.stroke()
        }
        c.setLineDash([])
    }
}
