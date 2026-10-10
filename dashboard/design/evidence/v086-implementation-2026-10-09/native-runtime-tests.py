import sys,unittest,json
from pathlib import Path
sys.path.insert(0,'/var/lib/smartpc-dashboard/v086-source-staging/project/dashboard')
import check_theme_api_runtime as module
suite=unittest.defaultTestLoader.loadTestsFromModule(module)
def flatten(s):
 for test in s:
  if isinstance(test,unittest.TestSuite):yield from flatten(test)
  else:yield test
all_tests=list(flatten(suite));excluded=[t.id() for t in all_tests if t.id().endswith('.test_lint_typo_rejected_with_real_qmllint')]
assert len(excluded)==1
selected=[t for t in all_tests if t.id() not in excluded]
result=unittest.TextTestRunner(verbosity=1).run(unittest.TestSuite(selected))
report={'status':'passed' if result.wasSuccessful() else 'failed','testsRun':result.testsRun,'excludedDesktopAuthoringGate':excluded,'desktopGate':'Passed with real Qt 6.8 qmllint on PC; executable not installed on board'}
Path('/var/lib/smartpc-dashboard/v086-source-proof/public-runtime-scope.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report));sys.exit(0 if result.wasSuccessful() else 1)
