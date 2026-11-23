.pragma library
function rng(seed) {
    var state = seed >>> 0
    return function() { state = (Math.imul(1664525,state)+1013904223) >>> 0; return state / 4294967296 }
}
function clamp(x,a,b) { return Math.max(a,Math.min(b,x)) }
function point(curve,t) {
    var v=1-t, p=curve.p
    return {x:v*v*v*p[0].x+3*v*v*t*p[1].x+3*v*t*t*p[2].x+t*t*t*p[3].x,
            y:v*v*v*p[0].y+3*v*v*t*p[1].y+3*v*t*t*p[2].y+t*t*t*p[3].y}
}
function tangent(curve,t) {
    var v=1-t,p=curve.p
    return {x:3*v*v*(p[1].x-p[0].x)+6*v*t*(p[2].x-p[1].x)+3*t*t*(p[3].x-p[2].x),
            y:3*v*v*(p[1].y-p[0].y)+6*v*t*(p[2].y-p[1].y)+3*t*t*(p[3].y-p[2].y)}
}
function segment(start,direction,area,random) {
    var end={x:area.x+random()*area.width,y:area.y+random()*area.height}
    if (Math.abs(end.x-start.x)<area.width*.25) end.x=start.x<area.x+area.width*.5 ? area.x+area.width*.85 : area.x+area.width*.15
    var dist=Math.hypot(end.x-start.x,end.y-start.y), length=Math.hypot(direction.x,direction.y)||1
    var reach=Math.min(120,dist*.4)
    var p1={x:clamp(start.x+direction.x/length*reach,area.x,area.x+area.width),y:clamp(start.y+direction.y/length*reach,area.y,area.y+area.height)}
    var p2={x:clamp(end.x-(end.x-start.x)*.3,area.x,area.x+area.width),y:clamp(end.y-(end.y-start.y)*.2,area.y,area.y+area.height)}
    var c={p:[start,p1,p2,end],arc:[0],length:0}, last=start
    for(var i=1;i<=32;i++) { var pos=point(c,i/32); c.length+=Math.hypot(pos.x-last.x,pos.y-last.y);c.arc.push(c.length);last=pos }
    return c
}
function sample(curve,distance) {
    var s=clamp(distance,0,curve.length), a=curve.arc, i=1
    while(i<a.length-1 && a[i]<s) i++
    var u=(i-1+(a[i]>a[i-1] ? (s-a[i-1])/(a[i]-a[i-1]) : 0))/32
    var pos=point(curve,u), dir=tangent(curve,u)
    return {x:pos.x,y:pos.y,dx:dir.x,dy:dir.y}
}
