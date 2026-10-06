#!/usr/bin/env python3
"""Fetch only the two already-reviewed, hash-pinned development tank sources."""
from pathlib import Path
import hashlib,json,urllib.request
root=Path(__file__).resolve().parents[2];dest=root/'.tools/asset-sources';dest.mkdir(parents=True,exist_ok=True);rows=[]
for source in json.loads((root/'content/model-sources.json').read_text())['sources']:
 if source['filename'] not in ('Tank.blend','Tank3.blend'):continue
 path=dest/source['filename'];row={'filename':source['filename'],'expected_sha256':source['sha256'],'download_url':source['download_url']}
 try:
  if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==source['sha256']:row['status']='verified_cached'
  else:
   file_id=source['download_url'].split('id=')[-1]
   alternate='https://drive.usercontent.google.com/download?id='+file_id+'&export=download&confirm=t'
   row['requested_url']=alternate
   request=urllib.request.Request(alternate,headers={'User-Agent':'RED-HORIZON-offline-asset-tool/1'})
   with urllib.request.urlopen(request,timeout=20) as response:data=response.read(64*1024*1024+1)
   digest=hashlib.sha256(data).hexdigest();row['received_bytes']=len(data);row['received_sha256']=digest
   if digest!=source['sha256']:row['status']='rejected_hash_mismatch'
   else:
    temporary=path.with_suffix('.blend.download');temporary.write_bytes(data);temporary.replace(path);row['status']='verified_downloaded'
 except Exception as exc:row['status']='fetch_failed';row['diagnostic']=str(exc)
 rows.append(row)
result={'scope':'Development source preparation only; no runtime/baked asset change or new license acceptance','sources':rows};(root/'docs/evidence/ground-attachment-source-fetch-alternate.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
