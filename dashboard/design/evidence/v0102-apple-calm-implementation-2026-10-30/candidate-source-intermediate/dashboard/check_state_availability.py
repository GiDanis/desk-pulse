"""Navigation availability must not rebuild unrelated provider trees."""
import unittest
import math
import json
from unittest.mock import patch

from theme_fixture_support import isolate_process
private,base=isolate_process()
from PySide6.QtCore import QObject,Signal
from PySide6.QtGui import QGuiApplication
from account import AccountService
from casa import CasaService
from casa_core import display_devices
from network import NetworkService
from network_core import display
from state import DashboardState
from weather import WeatherService

app=QGuiApplication.instance() or QGuiApplication([])


class System(QObject):changed=Signal()


class AvailabilityChecks(unittest.TestCase):
    def test_repeated_reads_are_constant_and_domain_signals_update_first(self):
        network=NetworkService(auto_refresh=False,demo=True)
        casa=CasaService(auto_refresh=False,demo=True)
        weather=WeatherService(auto_refresh=False)
        account=AccountService(path=base/'missing-account.json')
        state=None
        try:
            with patch('network.display',wraps=display) as net,patch('casa.display_devices',wraps=display_devices) as home:
                state=DashboardState(weather,System(),account,casa=casa,network=network)
                initial=(net.call_count,home.call_count)
                self.assertTrue(state.networkAvailable)
                self.assertTrue(state.casaAvailable)
                expected=state.visibleModules
                for _ in range(200):
                    self.assertEqual(state.visibleModules,expected)
                    self.assertTrue(state.networkAvailable)
                    self.assertTrue(state.casaAvailable)
                self.assertEqual((net.call_count,home.call_count),initial)
                seen=[]
                state.networkChanged.connect(lambda:seen.append(state.networkAvailable))
                network._snapshot=dict(network._snapshot,checkedAt=0)
                network.changed.emit()
                self.assertEqual(seen,[False])
                self.assertNotIn('network',state.visibleModules)
                self.assertEqual(net.call_count,initial[0]+1)
                favourites=casa._snapshot['favourites']
                casa._snapshot=dict(casa._snapshot,favourites=['not-in-inventory'])
                casa.changed.emit()
                self.assertFalse(state.casaAvailable)
                casa._snapshot=dict(casa._snapshot,favourites=favourites)
                casa.changed.emit()
                self.assertTrue(state.casaAvailable)
                casa._demo=False
                casa.changed.emit()
                self.assertFalse(state.casaAvailable)
                reads=(net.call_count,home.call_count)
                for _ in range(200):state.visibleModules
                self.assertEqual((net.call_count,home.call_count),reads)
        finally:
            if state and state.appearance:state.appearance.cancel()
            network.close();casa.close();weather.close();account.close()

    def test_json_wire_preserves_values_reuse_and_source_revision(self):
        class Sport(QObject):
            changed=Signal()
            def __init__(self):
                super().__init__()
                self.rows=[dict(canonicalMatchId='quote"\\unicode-é',homeScore=0,lineups=[{'name':'A'}]),
                           dict(canonicalMatchId='match-2',homeScore=None)]
                self.status='stale'
                self.stamp=100
            def view_state(self,selected):
                return dict(status=self.status,updatedAt=self.stamp,data=dict(fixtures=self.rows,
                    activeMatches=[],upcoming=self.rows,lastFinished=[],selectedMatchId=selected))
        weather=WeatherService(auto_refresh=False)
        account=AccountService(path=base/'missing-account.json')
        sport=Sport()
        state=DashboardState(weather,System(),account,sport=sport)
        try:
            first=state.sportViewState('match-2')
            self.assertEqual(json.loads(first['_sportLists']['fixtures']),sport.rows)
            self.assertEqual(first['data']['selectedMatchId'],'match-2')
            sport.status='updating';sport.stamp+=1;sport.changed.emit()
            second=state.sportViewState('match-2')
            self.assertIs(first['_sportLists']['fixtures'],second['_sportLists']['fixtures'])
            self.assertNotIn('fixtures',second['data'])
            self.assertEqual((second['status'],second['updatedAt']),('updating',101))
            sport.rows=list(reversed(sport.rows))
            changed=state.sportViewState('match-2')
            self.assertNotEqual(first['_sportLists']['fixtures'],changed['_sportLists']['fixtures'])
            self.assertEqual(json.loads(changed['_sportLists']['fixtures']),sport.rows)
            # Preserve QVariant semantics for non-JSON values rather than lose facts.
            sport.rows=[dict(value=math.nan)]
            nonfinite=state.sportViewState('')
            self.assertIs(nonfinite['data']['fixtures'],sport.rows)
            self.assertTrue(math.isnan(nonfinite['data']['fixtures'][0]['value']))
            self.assertLessEqual(len(state._sport_wire_arrays),4)
            self.assertNotIn('fixtures',nonfinite['_sportLists'])
        finally:
            if state.appearance:state.appearance.cancel()
            weather.close();account.close()


if __name__=='__main__':unittest.main()
