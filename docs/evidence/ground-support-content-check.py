#!/usr/bin/env python3
"""Reproducible development-only canonical compatibility negatives."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,tempfile
root=Path(__file__).resolve().parents[2]
results=[]; world_results=[]
with tempfile.TemporaryDirectory(prefix='rh-terrain-content-') as td:
    copy=Path(td)
    for folder in ('tools','schemas','content/terrain','src/net'):
        shutil.copytree(root/folder,copy/folder,ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copy2(root/'content/asset-manifest.json',copy/'content/asset-manifest.json')
    cases=(('relief_height','content/terrain/relief.json','64','65'),
           ('tank_grade','schemas/terrain_grade.inc','0.49029059656570206','0.48029059656570206'),
           ('tank_skin','schemas/terrain_body.inc','3.551','3.552'),
           ('render_spacing','tools/terrain_world.py',"'spacing':5","'spacing':10"),
           ('support_width','schemas/ground_support.inc','1.75','1.76'),
           ('support_offset','schemas/ground_support.inc','-0.45','-0.46'))
    for label,name,old,new in cases:
        p=copy/name;before=p.read_text();assert old in before,(label,old)
        p.write_text(before.replace(old,new,1))
        result=subprocess.run([sys.executable,str(copy/'tools/ground_content.py'),'--check'],cwd=copy,capture_output=True,text=True)
        assert result.returncode and 'compatibility mismatch' in result.stderr,(label,result.stdout,result.stderr)
        results.append({'mutation':label,'rejected':True,'exit_code':result.returncode,'diagnostic':result.stderr.splitlines()[-1]})
        p.write_text(before)
    result=subprocess.run([sys.executable,str(copy/'tools/ground_content.py'),'--check'],cwd=copy,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    restored=json.loads(result.stdout)
    field_path=copy/'content/terrain/relief.json';canonical=json.loads(field_path.read_text())
    for label,axis,index,value,diagnostic in (
        ('tile_support','x',3,6000,'fit inside refined tile'),
        ('unaligned_cusp','x',1,5481,'align with refined mesh'),
        ('height_budget','height',None,100,'triangle error budget')):
        mutated=json.loads(json.dumps(canonical))
        if index is None:mutated['fields'][0][axis]=value
        else:mutated['fields'][0][axis][index]=value
        field_path.write_text(json.dumps(mutated))
        result=subprocess.run([sys.executable,str(copy/'tools/terrain_world.py'),'--check'],cwd=copy,capture_output=True,text=True)
        assert result.returncode and diagnostic in result.stderr,(label,result.stdout,result.stderr)
        world_results.append({'mutation':label,'rejected':True,'exit_code':result.returncode,'diagnostic':result.stderr.strip()})
    field_path.write_text(json.dumps(canonical))
    files=('tools/ground_content.py','tools/terrain_world.py','schemas/terrain_grade.inc','schemas/terrain_body.inc','content/terrain/relief.json','src/net/protocol.inc','schemas/ground_support.inc')
    print(json.dumps({'scope':'Isolated stale-fingerprint negatives; no runtime changes','source_sha256':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files},'mutations':results,'world_guard_mutations':world_results,'restored_check':restored},indent=2))
