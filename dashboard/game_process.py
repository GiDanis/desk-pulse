"""Qt-safe dedicated subprocesses and bounded local packet transport.

Use posix_spawn (close_fds=False, no preexec/cwd/pass_fds), never fork the Qt
process or reconstruct its __main__. All extra descriptors close after exec.
Filesystem Unix sockets are private and independent of logind's POSIX IPC
cleanup. Trusted local packets only; no network endpoint is exposed.
"""
from collections import deque
from pathlib import Path
import os,pickle,queue,select,socket,struct,subprocess,sys,tempfile,time

HEADER=struct.Struct('!I');MAX_PACKET=64*1024*1024


def pack(channel,value):
    payload=pickle.dumps((channel,value),protocol=5)
    if len(payload)>MAX_PACKET:raise ValueError('Local game packet too large')
    return HEADER.pack(len(payload))+payload


def extract(buffer):
    messages=[];offset=0
    while len(buffer)-offset>=HEADER.size:
        size=HEADER.unpack_from(buffer,offset)[0]
        if size>MAX_PACKET:raise ValueError('Invalid local game packet length')
        if len(buffer)-offset<HEADER.size+size:break
        start=offset+HEADER.size;messages.append(pickle.loads(buffer[start:start+size]));offset=start+size
    if offset:del buffer[:offset]
    return messages


class ProcessHandle:
    def __init__(self,process,spawn_ms):self.process=process;self.spawn_ms=spawn_ms
    @property
    def pid(self):return self.process.pid
    @property
    def exitcode(self):return self.process.poll()
    def is_alive(self):return self.process.poll() is None
    def terminate(self):self.process.terminate()
    def kill(self):self.process.kill()
    def join(self,timeout=None):
        try:self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:pass
    def close(self):
        if self.is_alive():raise ValueError('Close a stopped process only')
        self.process.wait()


class ParentLink:
    def __init__(self):
        self.private=tempfile.TemporaryDirectory(prefix='spc-')
        self.path=Path(self.private.name)/'s'
        if len(os.fsencode(self.path))>=104:
            self.private.cleanup();raise ValueError('Temporary path too long for private game socket')
        self.listener=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        self.listener.bind(str(self.path));self.listener.listen(1);self.listener.setblocking(False)
        self.socket=None;self.buffer=bytearray();self.events=deque();self.frames=deque(maxlen=2);self.outgoing=deque();self.closed=False;self.eof=False

    def pump(self):
        if self.closed:raise EOFError('Local game transport closed')
        if self.eof:
            if self.events or self.frames:return
            raise EOFError('Local game transport disconnected')
        if self.socket is None:
            try:self.socket,_=self.listener.accept();self.socket.setblocking(False)
            except BlockingIOError:return
        while self.outgoing:
            try:n=self.socket.send(self.outgoing[0])
            except BlockingIOError:break
            if not n:raise EOFError('Local game transport disconnected')
            if n<len(self.outgoing[0]):self.outgoing[0]=self.outgoing[0][n:];break
            self.outgoing.popleft()
        received=0
        while received<1024*1024:
            try:data=self.socket.recv(65536)
            except BlockingIOError:break
            if not data:
                self.eof=True
                if not self.events and not self.frames:raise EOFError('Local game transport disconnected')
                break
            self.buffer.extend(data);received+=len(data)
            for channel,value in extract(self.buffer):
                if channel=='frame':self.frames.append(value)
                elif channel=='event':self.events.append(value)
                else:raise ValueError('Invalid local game channel')

    def send(self,value):
        if len(self.outgoing)>=16:raise OSError('Local game command queue full')
        self.outgoing.append(pack('command',value));self.pump()
    def poll(self):self.pump();return bool(self.events)
    def recv(self):
        if not self.events:self.pump()
        if not self.events:raise queue.Empty
        return self.events.popleft()
    def close(self):
        if self.closed:return
        self.closed=True
        if self.socket:self.socket.close()
        self.listener.close();self.private.cleanup();self.outgoing.clear();self.frames.clear();self.events.clear()


class ParentFrames:
    def __init__(self,link):self.link=link
    def get_nowait(self):
        self.link.pump()
        if not self.link.frames:raise queue.Empty
        return self.link.frames.popleft()
    def cancel_join_thread(self):pass
    def close(self):pass


class ParentRequests:
    def __init__(self,link):self.link=link
    def put_nowait(self,value):self.link.send(value)
    def cancel_join_thread(self):pass
    def close(self):self.link.close()


class ParentResults:
    def __init__(self,link):self.link=link
    def get_nowait(self):
        if not self.link.poll():raise queue.Empty
        return self.link.recv()
    def cancel_join_thread(self):pass
    def close(self):self.link.close()


class ChildLink:
    def __init__(self,path):
        self.socket=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);self.socket.connect(path)
        self.buffer=bytearray();self.commands=deque();self.pending_frame=b''
    def flush_frame(self,blocking=False):
        while self.pending_frame:
            try:n=self.socket.send(self.pending_frame,0 if blocking else socket.MSG_DONTWAIT)
            except BlockingIOError:return False
            if not n:raise EOFError('GUI disconnected')
            self.pending_frame=self.pending_frame[n:]
        return True
    def poll(self,timeout=0.):
        self.flush_frame()
        if not self.commands and timeout:select.select([self.socket],[],[],timeout)
        while select.select([self.socket],[],[],0)[0]:
            data=self.socket.recv(65536,socket.MSG_DONTWAIT)
            if not data:raise EOFError('GUI disconnected')
            self.buffer.extend(data)
            for channel,value in extract(self.buffer):
                if channel!='command':raise ValueError('Invalid GUI command channel')
                self.commands.append(value)
        return bool(self.commands)
    def recv(self,timeout=None):
        deadline=None if timeout is None else time.monotonic()+timeout
        while not self.commands:
            self.poll()
            if not self.commands:
                remaining=.1 if deadline is None else deadline-time.monotonic()
                if remaining<=0:raise TimeoutError('Incomplete local game command')
                select.select([self.socket],[],[],min(.1,remaining))
        return self.commands.popleft()
    def send(self,value):
        self.flush_frame(blocking=True);self.socket.sendall(pack('event',value))
    def close(self):self.socket.close()


class ChildFrames:
    def __init__(self,link):self.link=link
    def put_nowait(self,value):
        if not self.link.flush_frame():raise queue.Full
        self.link.pending_frame=pack('frame',value);self.link.flush_frame()
    def get_nowait(self):raise queue.Empty


class ChildRequests:
    def __init__(self,link):self.link=link
    def get(self):return self.link.recv()
    def get_nowait(self):
        if self.link.poll():return self.link.recv()
        # A large snapshot may fill the socket before the rest of its frame
        # arrives. Starting another full training update at every fragment
        # can postpone Pause by several rollouts. Complete an already-started
        # command here; an idle connection remains nonblocking, and a stalled
        # partial sender has a bounded transport deadline.
        if self.link.buffer:return self.link.recv(timeout=5.)
        raise queue.Empty


class ChildResults:
    def __init__(self,link):self.link=link
    def put(self,value):self.link.send(value)


def spawn_role(role,root,request=None,interpreter=None):
    if role not in ('learner','metadata','reference','reference-training'):raise ValueError('Unknown game process role')
    link=ParentLink();started=time.monotonic()
    try:
        process=subprocess.Popen([interpreter or sys.executable,str(Path(__file__).resolve()),'--child',role,'--parent-pid',str(os.getpid()),'--socket',str(link.path),'--root',str(root)],
            stdin=subprocess.DEVNULL,close_fds=False)
        handle=ProcessHandle(process,(time.monotonic()-started)*1000)
        if request is not None:link.send(request)
        return handle,link,ParentFrames(link)
    except Exception:
        link.close();raise


def child_main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--child',choices=('learner','metadata','reference','reference-training'),required=True)
    p.add_argument('--parent-pid',type=int,required=True)
    p.add_argument('--socket',required=True);p.add_argument('--root',required=True);a=p.parse_args()
    # Bind every level of the relay/preview/learner chain to its real parent.
    # A forced GUI shutdown must not leave grandchildren consuming CPU or
    # trying to save into a private store whose owner has already exited.
    import ctypes,signal
    if sys.platform.startswith('linux'):
        if ctypes.CDLL(None,use_errno=True).prctl(1,signal.SIGTERM)!=0:
            raise OSError(ctypes.get_errno(),'Cannot bind game process lifecycle')
    if os.getppid()!=a.parent_pid:return
    # Close inherited driver/Qt descriptors after exec, without atfork hooks.
    for file in Path('/proc/self/fd').iterdir():
        fd=int(file.name)
        if fd>2:
            try:os.close(fd)
            except OSError:pass
    os.environ.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    link=ChildLink(a.socket)
    if a.child=='metadata':
        from game_metadata import _read_loop
        try:_read_loop(a.root,ChildRequests(link),ChildResults(link))
        except EOFError:pass
        finally:link.close()
    elif a.child=='reference-training':
        from game_lab.runtime_worker import training_main
        try:training_main(link,a.root,link.recv())
        finally:link.close()
    elif a.child=='reference':
        # Only this interpreter imports Torch/Gym/SB3. Metadata and Qt retain
        # the caller's runtime and never load the learning libraries.
        from game_lab.runtime_worker import worker_main
        try:worker_main(link,ChildFrames(link),a.root,link.recv())
        finally:link.close()
    else:
        from game_session import session_main
        session_main(link,ChildFrames(link),a.root,link.recv())


if __name__=='__main__':child_main()
