import QtQuick

Window {
    id: root
    width: 960
    height: 640
    visible: true
    title: "SmartPC graphics check"
    color: "#101820"
    property int frameCount: 0
    property real firstFrameMs: 0
    property real lastFrameMs: 0
    property var frameIntervals: []

    onFrameSwapped: {
        const now = Date.now()
        if (firstFrameMs === 0)
            firstFrameMs = now
        if (lastFrameMs !== 0)
            frameIntervals.push(now - lastFrameMs)
        lastFrameMs = now
        frameCount += 1
    }

    Rectangle {
        width: 56
        height: 56
        radius: 12
        color: "#31d4bd"
        anchors.centerIn: parent

        NumberAnimation on rotation {
            from: 0
            to: 360
            duration: 1800
            loops: Animation.Infinite
            running: true
        }
    }

    Timer {
        interval: 5000
        running: true
        onTriggered: {
            const sorted = root.frameIntervals.slice().sort((a, b) => a - b)
            const p95 = sorted[Math.floor(sorted.length * 0.95)] || 0
            const elapsed = (root.lastFrameMs - root.firstFrameMs) / 1000
            console.log("SMOKE_FRAMES", root.frameCount,
                        "FPS", (root.frameCount - 1) / elapsed,
                        "P95_MS", p95)
            Qt.quit()
        }
    }
}
