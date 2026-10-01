// Research probe: bounded, unauthenticated subscription, no dashboard code.
// Uses Node's built-in WebSocket. A snapshot does not prove live updates.
import fs from 'node:fs';

const output = process.argv[2] || 'dashboard/design/evidence/v06-signalrcore-check-pc.json';
const result = {
    started_at: new Date().toISOString(),
    scope: 'bounded unauthenticated SignalR Core handshake and snapshot; no active-session latency measurement',
    endpoint: 'wss://livetiming.formula1.com/signalrcore',
    opened: false, handshake: false, topics: {}, message_types: [], errors: []
};
const topics = ['Heartbeat', 'SessionInfo', 'SessionStatus', 'TrackStatus',
    'DriverList', 'TimingData', 'LapCount', 'RaceControlMessages'];
let subscribed = false;
let done = false;
const socket = new WebSocket(result.endpoint);

function finish(reason) {
    if (done) return;
    done = true;
    result.reason = reason;
    result.completed_at = new Date().toISOString();
    fs.writeFileSync(output, JSON.stringify(result, null, 2) + '\n');
    try { socket.close(); } catch {}
    console.log(JSON.stringify({ reason, topics: Object.keys(result.topics), errors: result.errors }));
    setTimeout(() => process.exit(0), 150);
}

const timer = setTimeout(() => finish('bounded_timeout'), 15000);
socket.onopen = () => {
    result.opened = true;
    socket.send(JSON.stringify({ protocol: 'json', version: 1 }) + '\x1e');
};
socket.onmessage = event => {
    for (const part of String(event.data).split('\x1e').filter(Boolean)) {
        let message;
        try { message = JSON.parse(part); }
        catch { result.errors.push('non-json message'); continue; }
        if (message.type !== undefined) result.message_types.push(message.type);
        if (Object.keys(message).length === 0 && !subscribed) {
            result.handshake = true;
            subscribed = true;
            socket.send(JSON.stringify({ type: 1, invocationId: '1', target: 'Subscribe', arguments: [topics] }) + '\x1e');
        }
        if (message.error) result.errors.push(String(message.error).slice(0, 200));
        if (message.type === 3 && message.result) {
            for (const [key, value] of Object.entries(message.result)) {
                result.topics[key] = {
                    type: Array.isArray(value) ? 'array' : typeof value,
                    nonempty: !!value && Object.keys(value).length > 0
                };
                if (key === 'SessionInfo') result.session = {
                    name: value.Name, start: value.StartDate,
                    end: value.EndDate, gmt_offset: value.GmtOffset, meeting: value.Meeting?.Name
                };
            }
            clearTimeout(timer);
            finish('subscription_snapshot');
        }
        if (message.type === 1) {
            const args = message.arguments;
            if (Array.isArray(args) && typeof args[0] === 'string') result.topics[args[0]] = { seen: true };
        }
    }
};
socket.onerror = () => result.errors.push('websocket_error');
socket.onclose = event => {
    clearTimeout(timer);
    result.close_code = event.code;
    finish('connection_closed');
};
