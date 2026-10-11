"""Dedicated iliadbox session and Qt WebSocket; events invalidate HTTP state.

Address reachability is never promoted to device presence. HTTP reconciliation
remains enabled. TLS verifies the API hostname while connecting to the LAN IP.
"""
import json
from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, QUrl, Signal, Slot
from PySide6.QtNetwork import QNetworkRequest, QSslCertificate, QSslConfiguration, QSslSocket, QTcpServer, QTcpSocket, QHostAddress, QNetworkProxy
from PySide6.QtWebSockets import QWebSocket
from iliadbox import IliadboxClient, CA_FILE


class Signals(QObject):
    done = Signal(object, object)


class LocalTunnel(QObject):
    """Loopback CONNECT tunnel routes one verified TLS hostname to the LAN IP.

    QWebSocket does not honor QNetworkRequest.peerVerifyName on Qt 6.8. Keep
    the URL/SNI hostname intact instead of suppressing certificate errors.
    """
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.pairs = []
        self.server = QTcpServer(self)
        if not self.server.listen(QHostAddress.SpecialAddress.LocalHost, 0):
            raise OSError('Tunnel locale non disponibile')
        self.server.newConnection.connect(self._accept)

    def _accept(self):
        local = self.server.nextPendingConnection()
        remote = QTcpSocket(self)
        local.setReadBufferSize(65536)
        remote.setReadBufferSize(65536)
        pair = {'local': local, 'remote': remote, 'header': bytearray(), 'ready': False}
        self.pairs.append(pair)
        def close():
            local.abort(); remote.abort()
            if pair in self.pairs:
                self.pairs.remove(pair)
                local.deleteLater(); remote.deleteLater()
        def incoming():
            data = bytes(local.readAll())
            if not pair['ready']:
                pair['header'].extend(data)
                if len(pair['header']) > 4096:
                    close(); return
                if b'\r\n\r\n' not in pair['header']:
                    return
                target = f"CONNECT {self.config['api_domain']}:443 HTTP/1.1".encode()
                if bytes(pair['header']).split(b'\r\n', 1)[0] != target:
                    close(); return
                pair['ready'] = True
                remote.connectToHost(self.config['router'], 443)
            elif remote.bytesToWrite() < 1_000_000:
                remote.write(data)
            else:
                close()
        local.readyRead.connect(incoming)
        remote.connected.connect(lambda: local.write(b'HTTP/1.1 200 Connection established\r\n\r\n'))
        remote.readyRead.connect(lambda: local.write(remote.readAll()) if local.bytesToWrite() < 1_000_000 else close())
        local.disconnected.connect(close)
        remote.disconnected.connect(close)
        remote.errorOccurred.connect(lambda *_: close())

    def close(self):
        self.server.close()
        for pair in list(self.pairs):
            pair['local'].abort(); pair['remote'].abort()


class Login(QRunnable):
    def __init__(self, config, cleanup=None):
        super().__init__()
        self.config, self.cleanup = config, cleanup
        self.signals = Signals()

    def run(self):
        client = None
        try:
            if self.cleanup:
                self.cleanup.close()
            else:
                client = IliadboxClient(self.config)
                client.open()
            result, error = client, None
        except Exception:
            if client:
                client.close()
            result, error = None, 'Sessione eventi iliadbox non disponibile'
        self.signals.done.emit(result, error)


class NetworkEvents(QObject):
    invalidated = Signal()
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = None
        self.client = None
        self.job = None
        self.enabled = self.closed = False
        self.registered = False
        self.tunnel = None
        self.status = 'eventi non collegati'
        self.failures = 0
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(2)
        self.socket = QWebSocket()
        self.socket.setMaxAllowedIncomingMessageSize(65536)
        self.socket.connected.connect(self._opened)
        self.socket.textMessageReceived.connect(self._message)
        self.socket.disconnected.connect(self._disconnected)
        self.socket.errorOccurred.connect(self._failed)
        self.retry = QTimer(self)
        self.retry.setSingleShot(True)
        self.retry.timeout.connect(self._login)
        self.deadline = QTimer(self)
        self.deadline.setSingleShot(True)
        self.deadline.timeout.connect(self._failed)
        self.coalesce = QTimer(self)
        self.coalesce.setSingleShot(True)
        self.coalesce.timeout.connect(self.invalidated)
        self.ping = QTimer(self)
        self.ping.setInterval(60000)
        self.ping.timeout.connect(lambda: self.socket.ping(b'SmartPC'))

    def ensure(self, config, enabled):
        if self.closed:
            return
        if config != self.config or not enabled:
            self.enabled = False
            self.retry.stop()
            self.socket.abort()
            self._release()
        self.config = dict(config) if config else None
        self.enabled = bool(enabled and config)
        if self.enabled and not self.client and not self.job and not self.retry.isActive():
            self._login()

    def _login(self):
        if not self.enabled or self.job or self.closed:
            return
        self.job = Login(self.config)
        self.job.signals.done.connect(self._logged_in)
        self.pool.start(self.job)

    @Slot(object, object)
    def _logged_in(self, client, error):
        self.job = None
        if self.closed or not self.enabled or client and client.config != self.config:
            self._release(client)
            return
        if error:
            self._failed()
            return
        self.client = client
        if self.tunnel:
            self.tunnel.close(); self.tunnel.deleteLater()
        self.tunnel = LocalTunnel(self.config, self)
        self.socket.setProxy(QNetworkProxy(QNetworkProxy.ProxyType.HttpProxy, '127.0.0.1', self.tunnel.server.serverPort()))
        request = QNetworkRequest(QUrl(f"wss://{self.config['api_domain']}{client.base}/ws/event"))
        request.setRawHeader(b'X-Fbx-App-Auth', client.token.encode())
        ssl = QSslConfiguration.defaultConfiguration()
        ssl.setCaCertificates(QSslCertificate.fromPath(str(CA_FILE)))
        ssl.setPeerVerifyMode(QSslSocket.PeerVerifyMode.VerifyPeer)
        request.setSslConfiguration(ssl)
        self.socket.setSslConfiguration(ssl)
        self.socket.open(request)
        self.deadline.start(15000)

    def _opened(self):
        self.socket.sendTextMessage(json.dumps({'action': 'register', 'request_id': 1,
            'events': ['lan_host_l3addr_reachable', 'lan_host_l3addr_unreachable']}))

    def _message(self, text):
        try:
            for line in text.splitlines():
                value = json.loads(line)
                if value.get('action') == 'register' and value.get('success') is True:
                    self.registered = True
                    self.deadline.stop()
                    self.failures = 0
                    self.status = 'eventi collegati · riconciliazione 5 minuti'
                    self.ping.start()
                    self.changed.emit()
                    self.invalidated.emit()  # Silent reconciliation after reconnect.
                elif value.get('action') == 'notification' and self.registered and value.get('success') is True:
                    if str(value.get('source')) + '_' + str(value.get('event')) in ('lan_host_l3addr_reachable', 'lan_host_l3addr_unreachable'):
                        if not self.coalesce.isActive():
                            self.coalesce.start(2000)
                elif value.get('success') is False:
                    self._failed()
        except (ValueError, AttributeError):
            self._failed()

    def _release(self, client=None):
        client = client or self.client
        if client is self.client:
            self.client = None
        if client:
            self.pool.start(Login(client.config, cleanup=client))

    def _disconnected(self):
        self.deadline.stop()
        self.ping.stop()
        self.registered = False
        self._release()
        self.status = 'eventi scollegati · riconciliazione HTTP'
        self.changed.emit()
        if self.enabled and not self.closed and not self.retry.isActive():
            self.failures += 1
            self.retry.start(min(900, 30 * 2 ** min(self.failures, 4)) * 1000)

    def _failed(self, *_):
        self.socket.abort()
        self._disconnected()

    def close(self):
        self.closed = True
        self.enabled = False
        for timer in (self.retry, self.deadline, self.coalesce, self.ping):
            timer.stop()
        self.socket.abort()
        if self.tunnel:
            self.tunnel.close()
        self._release()
        self.pool.waitForDone(6500)
