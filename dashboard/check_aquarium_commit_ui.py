"""Real Main/ThemeApi routing: an accepted aquarium write is pending until commit."""
import json
import os
import sqlite3
import time
from theme_fixture_support import isolate_process,LegacyHarness


def main():
    os.environ['SMARTPC_AQUARIUM_RENDERER']='2d'
    private,base=isolate_process();h=None
    try:
        h=LegacyHarness(base,{'theme':'base','variant':'day','motion':'off'})
        h.service.cancel();h.wait_ready()
        h.expression('familyId="aquarium";overlay=""');h.pump(100)
        p=h.aquarium.population;p.load()
        def wait(test):
            end=time.monotonic()+8
            while not test() and time.monotonic()<end:h.pump(5)
            assert test(),(p.error,h.messages)
        wait(lambda:bool(p.state) and not p.busy)
        wait(lambda:h.aquarium._exposed)
        original=p.state['active'][0]
        assert p.act('replace',original['id'],{'species':'angel'})
        wait(lambda:not p.busy)
        target=p.state['pending'][0]['operationId'];history=p.state['historyCount']
        factory=h.service.apiFactory;context=factory.create('aquarium.3d')
        payload=h.expression('publicSurfacePayload("aquarium.3d")')
        payload.update(active=True,interactive=True,viewportWidth=960,viewportHeight=640)
        assert factory.updateLegacy(context,payload)
        real=p.store.prepared;failures=[]
        def fail_once(operation):
            if not failures:failures.append(True);raise sqlite3.OperationalError('controlled database is locked')
            return real(operation)
        p.store.prepared=fail_once
        result=context.requestAction('aquarium.prepared',target,{})
        assert result.accepted and result.status=='pending',(result.status,result.errorCode,h.aquarium._selected,h.aquarium._exposed,h.aquarium._theme,h.value('overlay'))
        wait(lambda:result.status!='pending')
        assert result.status=='failed' and p.state['pending']
        assert p.state['historyCount']==history
        retry=context.requestAction('aquarium.prepared',target,{})
        assert retry.status=='pending'
        wait(lambda:retry.status!='pending')
        assert retry.status=='completed' and not p.state['pending']
        assert p.state['historyCount']==history+1
        replay=context.requestAction('aquarium.prepared',target,{})
        wait(lambda:replay.status!='pending')
        assert replay.status=='completed' and p.state['historyCount']==history+1
        assert not h.value('pendingPublicActions')
        factory.release(context)
        assert not h.messages,h.messages
        print(json.dumps({'status':'passed','checks':['accepted remains pending','late DB failure reported',
            'retry commits once','replayed operation does not duplicate visit','pending request released'],'warnings':h.messages}))
    finally:
        if h:h.close()
        private.cleanup()


if __name__=='__main__':main()
