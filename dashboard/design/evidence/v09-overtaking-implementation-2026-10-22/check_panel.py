"""Focused real Main/Worker keypad walkthrough of new attack diagnostic text."""
from pathlib import Path
import sys,textwrap
def main():
    S=Path(__import__('game').__file__).parent
    source=(S/'check_game_menu_ui.py').read_text()
    source=source.replace("for name in ('Crono','Memoria','Linea','Tattico'):","for name in ('Crono',):")
    source=source.replace("modes=('impara','impara_infinito','impara_sorpasso') if args.all_modes and not reopened else ('impara',)","modes=('impara_sorpasso',)")
    source=source.replace("budget=(1200 if d['profile']['algorithm']=='residual_ppo' else 120) if reopened else 4000","budget=1200")
    source=source.replace("                capture(name.lower()+'-'+mode)",textwrap.indent(textwrap.dedent("""
                    from PySide6.QtCore import QObject
                    for _ in range(5):
                        if h.game.snapshot['camera']=='telemetria':break
                        h.expression('activateKey(8)');h.pump(80)
                    assert h.game.snapshot['camera']=='telemetria'
                    h.expression('activateKey(6)');h.pump(80);assert h.game.snapshot['camera']=='premi'
                    h.expression('activateKey(6)');h.pump(80);assert h.game.snapshot['camera']=='rete'
                    panel=next(x for x in h.window.findChildren(QObject,'gameLearningPanel') if x.property('visible'))
                    assert h.game.scene['meta']['residual']['collectionLabel']
                    assert h.game.scene['meta']['residual']['attack']
                    capture('attack-network-panel')
                    h.expression('activateKey(8)');h.pump(80);assert h.game.snapshot['camera']=='sensori'
                    h.expression('activateKey(8)');h.pump(80);assert h.game.snapshot['camera']=='circuito'
                    """),'                '))
    source=source.replace('if not reopened:\n            for name', 'if False:\n            for name')
    exec(compile(source,str(S/'check_game_menu_ui.py'),'exec'),{'__file__':str(S/'check_game_menu_ui.py'),'__name__':'__main__'})

if __name__=='__main__':main()
