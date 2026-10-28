"""Export only release proof, never the production Game directory or backups."""
from pathlib import Path
import tarfile
P=Path('/var/lib/smartpc-dashboard/v09-direct-proof');out=Path('/tmp/smartpc-direct-public-proof.tar.gz')
files=['arm-tests.txt','base.txt','functional.txt','apple.txt','source-checks.json','original-preservation.json','final-summary.json','final-source-reproduction.json','before-install.json','installed.json','final-receipt.json']
for theme in ('base','functional','apple'):
 files += [theme+'/'+n for n in ('report.json','ready-oval-12m.png','crono-learning.png','crono-controls.png','crono-network.png','five-grid.png','five-racing.png','pilot-method.png','clean-roster-settings.png')]
 if theme=='apple':files.append(theme+'/actual-flying-qualifying.png')
with tarfile.open(out,'w:gz') as tar:
 for n in files:
  f=P/n;assert f.is_file(),n;tar.add(f,arcname=n,recursive=False)
print(str(out),out.stat().st_size)
