"""Wait for the current revision and reacquire dynamic presentation references."""
import time
from PySide6.QtCore import QObject


def as_value(value):return value.toVariant() if hasattr(value,'toVariant') else value


def wait_ready(application,window,timeout=3):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        application.processEvents()
        hosts=[child for child in window.findChildren(QObject) if child.metaObject().indexOfProperty('readiness')>=0 and child.property('active')]
        errors=[host.property('lastError') for host in hosts if host.property('readiness')=='error']
        assert not errors,errors
        if hosts and all(host.property('readiness')=='ready' for host in hosts):return
        time.sleep(.003)
    raise AssertionError('ViewHost non pronto: '+str([(h.property('contentId'),h.property('readiness')) for h in hosts]))


def current_item(application,window,name):
    wait_ready(application,window)
    host=window.findChild(QObject,name)
    assert host is not None,name
    item=as_value(host.property('currentItem'))
    assert item is not None,name
    return item


def wait_save(application,service,timeout=3):
    deadline=time.monotonic()+timeout
    while service.status=='saving' and time.monotonic()<deadline:
        application.processEvents();time.sleep(.003)
    application.processEvents()
    assert service.status!='saving','timeout salvataggio'


def configure_appearance(state):
    """Optional isolated harness profile, never a production environment override."""
    import os
    from PySide6.QtCore import QCoreApplication
    if not os.environ.get('SMARTPC_TEST_THEME'):return
    service=state.appearance;service.beginEdit()
    assert service.selectDraft(os.environ['SMARTPC_TEST_THEME']),service.lastError
    assert service.setSection('paletteMode',os.environ.get('SMARTPC_TEST_VARIANT','day'))
    assert service.setSection('motionMode',os.environ.get('SMARTPC_TEST_MOTION','normal'))
    if os.environ.get('SMARTPC_TEST_WIDE')=='1':
        assert service.setTokens({'metrics.listRows':3,'metrics.compactRows':2,'metrics.overviewRows':2,'metrics.fantasyRows':4,'typography.textScale':1.1})
    assert service.apply();wait_save(QCoreApplication.instance(),service)


def assert_theme_keeps_selection(application,window,state,properties):
    """Theme changes inside open details must not select/refresh providers again."""
    from unittest.mock import patch
    from contextlib import ExitStack
    before={key:as_value(window.property(key)) for key in properties}
    service=state.appearance
    with ExitStack() as stack:
        spies=[stack.enter_context(patch.object(state,name,wraps=getattr(state,name))) for name in ('selectSportMatch','selectFantacalcio','selectRacing','selectRacingDriver','dismissEvent','markEventSeen') if hasattr(state,name)]
        service.beginEdit();assert service.selectDraft('functional' if service.activeThemeId=='base' else 'base'),service.lastError
        wait_ready(application,window)
        assert {key:as_value(window.property(key)) for key in properties}==before
        service.cancel();wait_ready(application,window)
        assert {key:as_value(window.property(key)) for key in properties}==before
        assert all(spy.call_count==0 for spy in spies),'theme/presentation caused provider selection or delivery changes'
