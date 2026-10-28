"""Like-for-like static projection cost; not an FPS or training comparison."""
from copy import deepcopy
import json,statistics,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from game_catalog import configuration,visual_content
from theme_api import _plain
rows=[]
for identity in ('mallory-oval-1','varano-short-1'):
 config=configuration(identity);before={'configuration':config,'drawing':config['track']['drawing']}
 projected,drawing=visual_content(identity);after={'configuration':projected,'drawing':drawing}
 result={'track':identity}
 for label,payload in (('before',before),('after',after)):
  elapsed=[]
  for _ in range(100):
   start=time.perf_counter();_plain(deepcopy(payload));elapsed.append(time.perf_counter()-start)
  result[label+'MedianMs']=statistics.median(elapsed)*1000
  result[label+'MaxMs']=max(elapsed)*1000
 result['ratio']=result['beforeMedianMs']/result['afterMedianMs'];rows.append(result)
out={'scope':'PC static map copy and legacy normalization, same metric geometry, 100 samples; no optical/GPU/end-to-end FPS claim','tracks':rows}
Path(__file__).with_name('gui-projection-benchmark.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
