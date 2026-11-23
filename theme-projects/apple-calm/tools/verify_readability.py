#!/usr/bin/env python3
"""Real Main + Apple Calm: reserved notification space and visible data oracles."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'dashboard'))
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--palette',choices=['day','night'],default='day');p.add_argument('--header-only',action='store_true');p.add_argument('--scenes-only',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    from theme_fixture_support import isolate_process,LegacyHarness,read_corpus
    private,base=isolate_process();h=None;records=[]
    try:
     from PySide6.QtCore import QObject,QDateTime,QPointF,QTime,qVersion
     from PySide6.QtQml import QQmlExpression,QQmlEngine
     from theme_bundle import BundleManager,validate_project
     from theme_test_support import as_value
     project=ROOT/'theme-projects/apple-calm/bundle';valid=validate_project(project)
     cached=json.loads((project.parent/'evidence/preflight-cache.json').read_text())
     assert cached['digest']==valid['digest'] and cached['result']['status']=='passed' and cached['result']['qt']==qVersion()
     BundleManager(base,app_root=ROOT/'dashboard').import_bundle(project,preflight=lambda *_:cached['result'],require_preflight=True)
     h=LegacyHarness(base,{'theme':'base','variant':a.palette,'motion':'off','game':True})
     assert h.service.selectDraft('studio.applecalm'),h.service.lastError
     h.wait_ready();_,cases,_=read_corpus()
     views=[] if a.header_only or a.scenes_only else ['home.now','home.clock','home.day','weather.now','weather.forecast','account.usage','sport.overview','racing.overview','casa.overview','network.overview']
     def eval_in(obj,code):
      context=QQmlEngine.contextForObject(obj);engine=context.engine();engine.globalObject().setProperty('__calmAuditItem',engine.newQObject(obj))
      ex=QQmlExpression(context,obj,code);value,undefined=ex.evaluate();assert not ex.hasError(),ex.error().toString();assert not undefined;return as_value(value)
     def host(sid):return h.root.findChild(QObject,{'home.now':'homeNow','home.clock':'homeClock','home.day':'homeDay','weather.now':'weatherNow','weather.forecast':'weatherForecast','account.usage':'accountPanel','sport.overview':'sportPanel','racing.overview':'racingPanel','casa.overview':'casaOverview','network.overview':'networkOverview'}[sid])
     for scale in [1,1.1]:
      assert h.service.setToken('typography.textScale',scale);h.wait_ready()
      for sid in views:
       case=next(c for c in cases if c['surfaceId']==sid);h.setup(case)
       if sid in ('home.now','home.clock'):
        item=as_value(host(sid).property('currentItem'))
        clock=item.findChild(QObject,'dominantClock')
        position=clock.mapToItem(item,QPointF())
        dimensions=(clock.width(),clock.height())
        h.events.set_demo_scenario('prossimo');h.pump(100)
        assert item.property('showNext')
        assert clock.mapToItem(item,QPointF())==position and (clock.width(),clock.height())==dimensions
        widths=[]
        start=QDateTime.fromSecsSinceEpoch(int(h.now))
        for hour,minute in [(8,8),(11,11),(23,59)]:
         stamp=QDateTime(start);stamp.setTime(QTime(hour,minute))
         h.root.setProperty('now',stamp);h.pump(40)
         assert clock.property('text')==f'{hour:02}:{minute:02}'
         widths.append(clock.property('contentWidth'))
        assert max(widths)-min(widths)<=1,(sid,scale,widths)
        h.root.setProperty('now',start)
        h.weather.value.update(status='offline');h.weather.changed.emit();h.pump(50)
        weather=item.findChild(QObject,'deskWeatherStatus' if sid=='home.now' else 'clockWeather')
        assert weather.property('visible') and 'Dati meteo precedenti' in weather.property('text')
        if sid=='home.now':
         h.weather.value['data']['description']='Temporale con grandine intensa'
         h.weather.changed.emit();h.pump(50)
         condition=item.findChild(QObject,'deskWeatherCondition')
         assert condition.property('text')=='Temporale con grandine intensa'
         assert not condition.property('truncated') and condition.property('contentHeight')<=condition.height()+1
        for status,expected in [('pending','Meteo in attesa'),('updating','Aggiornamento meteo…'),
                                ('offline','Meteo offline'),('error','Errore meteo')]:
         h.weather.value.update(status=status,data={});h.weather.changed.emit();h.pump(50)
         label=item.findChild(QObject,'deskWeatherCondition' if sid=='home.now' else 'clockWeather')
         assert label.property('text')==expected and not label.property('truncated'),(sid,scale,status)
        if sid=='home.now':
         assert item.findChild(QObject,'weatherSymbol').property('resolvedSymbol')=='unknown'
        h.setup(case)
       if sid=='weather.forecast':
        h.weather.value['data']['forecast'][0].update(code=99,description='Temporale con grandine intensa')
        # A missing value must remain distinguishable from a measured zero.
        last=h.weather.value['data']['forecast'][-1]
        last.update(rainProbabilityValue=None,rain='—')
        h.weather.changed.emit()
       for banner in ['banner','banner grande']:
        h.events.set_demo_scenario(banner);h.pump(250)
        assert h.value('bannerEvent').get('id'),(sid,banner,'missing banner')
        item=as_value(host(sid).property('currentItem'));assert item is not None
        rect=h.expression('pageGeometry('+json.dumps(sid)+')');area={k:getattr(rect,k)() for k in ['x','y','width','height']};notices=h.root.findChild(QObject,'eventLargeBanner' if banner=='banner grande' else 'eventBanner')
        assert area['y']+area['height']<=notices.property('y')-8,(sid,area,notices.property('y'))
        assert item.property('height')==area['height']
        if banner=='banner grande':
         banner_item=as_value(notices.property('currentItem'))
         body=banner_item.findChild(QObject,'notificationBody')
         assert body.y()+body.property('contentHeight')<=notices.height()-14
         assert notices.height()<220,(sid,scale,notices.height())
        # Check visible leaf allocation inside cards. Scrollable lists may expose
        # partially visible rows; do not misclassify those as fixed card overflow.
        geometry=eval_in(item,'''(function(){var problems=[];function visit(n,scrolling){if(!n.visible)return;var sc=scrolling || n.contentY!==undefined;if(n.width<0 || n.height<0)problems.push(n.objectName+': negative size');if(!sc && n.text!==undefined && String(n.text).length && n.parent && n.parent.radius!==undefined && n.y+n.height>n.parent.height+1)problems.push(String(n.text)+': below card');for(var i=0;i<n.children.length;i++)visit(n.children[i],sc);}visit(this,false);return problems;}).call(__calmAuditItem)''')
        assert not geometry,(sid,scale,banner,geometry)
        if sid in ('home.now','home.clock'):
         required=['dominantClock','homeDate','weatherTemperature' if sid=='home.now' else 'clockWeather']
         for name in required:
          label=item.findChild(QObject,name)
          assert label is not None and label.property('visible') and not label.property('truncated'),(sid,scale,banner,name)
          top=label.mapToItem(item,QPointF()).y()
          assert 0<=top and top+label.height()<=area['height'],(sid,scale,banner,name,top,label.height(),area)
          assert label.property('contentHeight')<=label.height()+1,(sid,scale,banner,name)
        if sid=='account.usage':
         values=eval_in(item,'''(function(){var out=[];function walk(n){if(n.objectName && String(n.objectName).indexOf("accountRemaining")===0)out.push({name:n.objectName,text:n.text===undefined ? "" : String(n.text),ratio:n.parent.width ? n.width/n.parent.width : 0});for(var i=0;i<n.children.length;i++)walk(n.children[i]);}walk(this);return out;}).call(__calmAuditItem)''')
         assert any(v['name']=='accountRemaining0' and v['text']=='100%' for v in values),values
         if area['height']>350:assert any(v['name']=='accountRemainingBar0' and abs(v['ratio']-1)<.001 for v in values),values
        if sid=='weather.forecast':
         labels=eval_in(item,'''(function(root) {
          const out=[];
          function walk(item) {
           if (item.visible && item.text !== undefined)
            out.push({name:item.objectName,text:String(item.text),truncated:item.truncated,
                      bottom:item.mapToItem(root,0,0).y+item.height});
           for (const child of item.children) walk(child);
          }
          walk(root);return out;
         })(__calmAuditItem)''')
         assert all(any(label['text']==header for label in labels) for header in ('Max','Min','Pioggia')),labels
         days=[label for label in labels if label['name']=='forecastDayLabel']
         conditions=[label for label in labels if label['name']=='forecastCondition']
         assert len(days)==len(conditions)==3 and all(not label['truncated'] for label in days+conditions)
         assert 'grandine intensa' in conditions[0]['text'].lower()
         for name,expected in [('forecastHigh',('0°','1°','2°')),('forecastLow',('0°','-1°','-2°')),('forecastRain',('0%','0%','—'))]:
          column=[label for label in labels if label['name']==name]
          assert [label['text'] for label in column]==list(expected),(name,column)
          assert all(not label['truncated'] and label['bottom']<=area['height'] for label in column)
        assert h.window.activeFocusItem().objectName()=='inputOwner'
        assert not h.messages,(sid,h.messages)
        name=sid+'-'+str(scale).replace('.','')+'-'+('large' if banner=='banner grande' else 'small')+'.png';assert h.window.grabWindow().save(str(a.output/name))
        records.append({'surface':sid,'scale':scale,'banner':banner,'safeArea':area,'focusPreserved':True,'status':'passed'})
     # Header recovery and quiet states coexist without suppressing the clock/count.
     h.setup(next(c for c in cases if c['surfaceId']=='home.now'))
     h.state._theme_recovery_error='Synthetic recovery';h.state._quiet_enabled=True;h.state._quiet_start=0;h.state._quiet_end=1439;h.state.settingsChanged.emit();h.events.set_quiet(True,0,1439);h.pump(100)
     header=as_value(h.root.findChild(QObject,'shellHost').property('currentItem'))
     assert header.findChild(QObject,'headerClock').property('text')==h.expression('timeText()')
     assert header.findChild(QObject,'headerAlerts').property('visible')
     status=header.findChild(QObject,'headerStatus');assert 'Quiete' in status.property('text') and 'Ripristino' in status.property('text')
     assert status.property('contentHeight')<=status.property('height')+1 and not status.property('truncated'),status.property('text')
     assert h.window.grabWindow().save(str(a.output/'header-recovery-quiet.png'))
     if a.scenes_only:
      for sid,name in [('game.track','gameTrack'),('aquarium.3d','aquarium3DPage')]:
       h.setup(next(c for c in cases if c['surfaceId']==sid));h.state._quiet_enabled=False;h.state.settingsChanged.emit();h.events.set_quiet(False,0,1)
       if sid=='game.track':
        teacher=next(d for d in h.game.snapshot['drivers'] if d['algorithm']=='race_master')
        assert h.game.selectDriver(teacher['id']),h.game.snapshot
        h.pump(100)
        assert h.game.setMode('qualifica'),h.game.snapshot
        deadline=__import__('time').monotonic()+10
        while h.game.snapshot.get('saveState')=='saving' and __import__('time').monotonic()<deadline:h.pump(20)
        assert h.game.start(),h.game.snapshot
        deadline=__import__('time').monotonic()+20
        while h.game.snapshot['runState']!='running' and __import__('time').monotonic()<deadline:h.pump(20)
        assert h.game.snapshot['runState']=='running',h.game.snapshot
       for banner in ['banner','banner grande']:
        h.events.set_demo_scenario(banner);h.pump(400)
        host_obj=h.root.findChild(QObject,name);item=as_value(host_obj.property('currentItem'));assert item and item.property('ready')
        notice=h.root.findChild(QObject,'eventLargeBanner' if banner=='banner grande' else 'eventBanner')
        if sid=='game.track':
         rect=h.expression('pageGeometry("game.track")');assert rect.bottom()<=notice.property('y')-8
         assert h.game.snapshot['runState']=='running',h.game.snapshot
        else:
         rect=h.expression('publicSurfacePayload("aquarium.3d").safeArea');assert rect.bottom()<=notice.property('y')-8
         assert item.property('assetsReady') and not item.property('assetFailed')
        assert not h.messages,h.messages
        assert h.window.grabWindow().save(str(a.output/(sid+('-large' if banner=='banner grande' else '-small')+'.png')))
        records.append({'surface':sid,'banner':banner,'status':'passed','scope':'Synthetic isolated scene; no model learning/race/physical qualification'})
       if sid=='game.track':h.game.stop();h.pump(100)
     assert not h.messages,h.messages
     report={'status':'passed','scope':'Synthetic offline Main/QML layout/data assertions, not physical readability or provider qualification','palette':a.palette,'qt':qVersion(),'bundleDigest':valid['digest'],'cases':records,'qmlWarnings':h.messages}
     (a.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':'passed','cases':len(records),'palette':a.palette}))
    except BaseException:
     (a.output/'failure.json').write_text(json.dumps({'status':'failed','cases':records,'qmlWarnings':h.messages if h else []},ensure_ascii=False,indent=2)+'\n');raise
    finally:
     if h:h.close()
     private.cleanup()

if __name__=='__main__':
    main()
