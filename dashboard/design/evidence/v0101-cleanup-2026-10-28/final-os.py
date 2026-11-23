import hashlib,json,pathlib,shutil,subprocess
b=json.loads(pathlib.Path('/tmp/smartpc-cleanup-v0101/os-after-packages.json').read_text())
packages={};states={}
for line in subprocess.check_output(['dpkg-query','-W','-f=${Package}\t${Version}\t${db:Status-Abbrev}\n'],text=True).splitlines():
 name,version,status=line.split('\t')
 packages[name]=version;states[name]=status
assert packages==b['packages'] and states==b['states'],'DPKG package versions or states changed'
held=subprocess.check_output(['apt-mark','showhold'],text=True).splitlines()
assert sorted(held)==sorted(b['held']),'Package holds changed'
for name,digest in b['hardwareHashes'].items():
 path=pathlib.Path(name)
 current=hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
 assert current==digest,'Protected OS file changed: '+name
boot=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot==b['bootId'],'Unexpected OS reboot'
print(json.dumps({'status':'passed','installedPackages':sum(s[1]=='i' for s in states.values()),'dpkgRecordsVerified':len(packages),'packageSetPreservedSinceAuthorizedRemoval':True,'hardwareFilesVerified':len(b['hardwareHashes']),'holdsPreserved':True,'sameBoot':True,'disk':shutil.disk_usage('/')._asdict()}))
