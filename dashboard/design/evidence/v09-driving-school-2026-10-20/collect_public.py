from pathlib import Path
import tarfile
P=Path('/var/lib/smartpc-dashboard/v09-school-proof');out=Path('/tmp/smartpc-school-public-proof.tar.gz')
files=['arm-final-school.txt','arm-frozen-retention.txt','arm-frozen-retention.json','native-source-checks.json','arm-tests.txt','base.txt','functional.txt','apple.txt','source-checks.json','original-preservation.json','final-summary.json','final-source-reproduction.json','before-install.json','installed.json','final-receipt.json']
for theme in ('base','functional','apple'):
 assert (P/theme/'report.json').is_file()
 files += [str(f.relative_to(P)) for f in (P/theme).glob('*.png')]+[theme+'/report.json']
with tarfile.open(out,'w:gz') as tar:
 for n in files:
  f=P/n;assert f.is_file(),n;tar.add(f,arcname=n,recursive=False)
print(str(out),out.stat().st_size)
