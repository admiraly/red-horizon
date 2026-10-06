#!/usr/bin/env python3
"""Collect exact terminal body-route jobs without replacing older evidence."""
from pathlib import Path
import hashlib,json,shutil,sys
root=Path(__file__).resolve().parents[2];out=root/'docs/evidence';summary=[]
for supplied in sys.argv[1:]:
 folder=Path(supplied) if Path(supplied).is_absolute() else root/'runs/jobs'/supplied
 data=json.loads((folder/'job.json').read_text());data.update(json.loads((folder/'result.json').read_text()));snap=folder/'source'
 files=[p for name in ('src','shaders','schemas','tools','tests') for p in sorted((snap/name).rglob('*')) if p.is_file() and '__pycache__' not in str(p)]
 files.extend(snap/name for name in ('content/terrain/roads.json','content/terrain/relief.json','content/asset-manifest.json'))
 hashes={str(p.relative_to(snap)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files};data['source_sha256']=hashes;data['authored_input_count']=len(hashes)
 data['current_source_mismatches']=[n for n,h in hashes.items() if not(root/n).exists() or hashlib.sha256((root/n).read_bytes()).hexdigest()!=h]
 log=(folder/'job.log').read_text();reports=[];decoder=json.JSONDecoder();pos=0
 while pos<len(log):
  i=log.find('{',pos)
  if i<0:break
  try:
   value,n=decoder.raw_decode(log[i:]);pos=i+n
   if isinstance(value,dict) and any(k in value for k in ('suite','runtime','coverage','ground_support_samples','ground_contact_samples','suspension_calls','ground_eye_cases')):reports.append(value)
  except ValueError:pos=i+1
 prefix='wreck-dense-routing-'+folder.name
 (out/(prefix+'-reports.json')).write_text(json.dumps(reports,indent=2)+'\n');data['reports']='docs/evidence/'+prefix+'-reports.json';data['report_count']=len(reports)
 if data['status']!='passed':
  dest=out/(prefix+'-'+data['status']+'.log');shutil.copy2(folder/'job.log',dest);data['terminal_log']=str(dest.relative_to(root))
 summary.append(data)
(out/'wreck-dense-routing-jobs.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps([{k:r.get(k) for k in ('job_id','status','seconds','report_count','current_source_mismatches')} for r in summary],indent=2))
