"""Local transport fragmentation/backpressure and Qt-safe process launch."""
from pathlib import Path
import json,os,queue,subprocess,sys,tempfile,threading,time,unittest
from unittest.mock import patch
from game_process import ParentLink,ChildLink,ChildFrames,ChildRequests,extract,pack,spawn_role
from game_store import GameStore


class ProcessChecks(unittest.TestCase):
    def test_partial_large_pause_is_completed_before_next_training_update(self):
        import socket
        parent=ParentLink();child=ChildLink(str(parent.path));parent.pump()
        parent.socket.setsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF,4096)
        message=dict(type='pause',previewReadout=b'x'*(2*1024*1024));parent.send(message)
        self.assertTrue(parent.outgoing);errors=[]
        def send_rest():
            try:
                deadline=time.monotonic()+4
                while parent.outgoing and time.monotonic()<deadline:parent.pump();time.sleep(.001)
            except Exception as e:errors.append(e)
        thread=threading.Thread(target=send_rest);thread.start()
        try:
            self.assertEqual(ChildRequests(child).get_nowait(),message)
            thread.join(2);self.assertFalse(thread.is_alive());self.assertFalse(errors)
            with self.assertRaises(queue.Empty):ChildRequests(child).get_nowait()
            parent.socket.send(b'\x00\x00\x10\x00partial')
            with self.assertRaises(TimeoutError):child.recv(timeout=.02)
        finally:
            thread.join(2);child.close();parent.close()

    @unittest.skipUnless(sys.platform.startswith('linux'),'Linux parent-death contract')
    def test_forced_parent_exit_cannot_leave_a_local_worker_running(self):
        with tempfile.TemporaryDirectory() as root:
            GameStore(root);destination=Path(root)/'child.json'
            code="from game_process import spawn_role;from pathlib import Path;import json,time,sys;p,l,f=spawn_role('metadata',sys.argv[1]);l.send((1,'','oval-1','impara'));end=time.monotonic()+15\nwhile not l.poll() and time.monotonic()<end:time.sleep(.005)\nassert l.recv()['ticket']==1\nPath(sys.argv[2]).write_text(json.dumps(dict(pid=p.pid)))\ntime.sleep(60)"
            parent=subprocess.Popen([sys.executable,'-c',code,root,str(destination)])
            try:
                deadline=time.monotonic()+20
                while not destination.exists() and parent.poll() is None and time.monotonic()<deadline:time.sleep(.01)
                self.assertTrue(destination.exists());pid=json.loads(destination.read_text())['pid']
                parent.kill();parent.wait(3);deadline=time.monotonic()+4
                def running():
                    try:return (Path('/proc')/str(pid)/'stat').read_text().split(') ',1)[1].split()[0]!='Z'
                    except FileNotFoundError:return False
                while running() and time.monotonic()<deadline:time.sleep(.01)
                self.assertFalse(running(),'Worker survived its killed parent')
            finally:
                if parent.poll() is None:parent.kill();parent.wait(3)

    def test_large_metadata_packet_fragmentation_and_bounded_frames(self):
        parent=ParentLink();child=ChildLink(str(parent.path));frame=ChildFrames(child)
        data={'text':'x'*600000};error=[]
        def send():
            try:
                for i in range(30):
                    try:frame.put_nowait(dict(sequence=i,payload='y'*40000))
                    except queue.Full:pass
                child.send(data)
            except Exception as e:error.append(e)
        thread=threading.Thread(target=send);thread.start();deadline=time.monotonic()+5
        try:
            while not parent.events and time.monotonic()<deadline:parent.pump();time.sleep(.001)
            thread.join(1)
            self.assertFalse(thread.is_alive());self.assertFalse(error)
            self.assertEqual(parent.recv(),data);self.assertLessEqual(len(parent.frames),2)
        finally:child.close();parent.close()
        encoded=pack('event',{'n':7});buffer=bytearray()
        for byte in encoded[:-1]:buffer.append(byte);self.assertEqual(extract(buffer),[])
        buffer.append(encoded[-1]);self.assertEqual(extract(buffer),[('event',{'n':7})])

    def test_dedicated_metadata_process_uses_posix_spawn(self):
        with tempfile.TemporaryDirectory() as root:
            GameStore(root)
            with patch('os.posix_spawn',wraps=os.posix_spawn) as spawn:
                process,link,_=spawn_role('metadata',root)
            try:
                self.assertEqual(spawn.call_count,1)
                link.send((1,'','oval-1','impara'));deadline=time.monotonic()+10
                while not link.poll() and time.monotonic()<deadline:time.sleep(.005)
                result=link.recv();self.assertEqual(len(result['drivers']),5);self.assertEqual(result['ticket'],1)
                link.send(None);process.join(3);self.assertFalse(process.is_alive())
            finally:
                if process.is_alive():process.kill();process.join(1)
                process.close();link.close()


if __name__=='__main__':unittest.main()
