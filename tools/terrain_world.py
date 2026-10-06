#!/usr/bin/env python3
"""Development-only checks connecting canonical relief to the fixed render tile."""
import argparse, importlib.util, json, pathlib, re
ROOT=pathlib.Path(__file__).resolve().parents[1]
PATCH={'x':[5375,5875],'z':[4750,5625],'spacing':5,'max_height_error':0.027,'route_margin':6,'node_limit':27}
def check(document):
    spec=importlib.util.spec_from_file_location('relief_validation',ROOT/'tools/terrain_relief.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    row=module.validate(document)[0];x=row[:4];z=row[4:8];height=row[8]
    for axis,limits in ((x,PATCH['x']),(z,PATCH['z'])):
        assert limits[0]<axis[0] and axis[-1]<limits[-1], 'Relief support must fit inside refined tile'
        assert all((v-limits[0])%PATCH['spacing']==0 for v in axis), 'Relief cusp must align with refined mesh'
    mixed=height/(min(x[1]-x[0],x[3]-x[2])*min(z[1]-z[0],z[3]-z[2]))
    interior=mixed*PATCH['spacing']**2/4+1.5e-6*PATCH['spacing']**2/4
    seam=1e-6*62.5**2/4
    assert interior+seam+0.0001<=PATCH['max_height_error'], 'Relief exceeds actual triangle error budget'
    assert PATCH['route_margin']>4.491 and PATCH['node_limit']*8+24<=256
    return {'interior_height_bound':interior,'seam_correction_bound':seam,'roundoff_allowance':0.0001}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');a=p.parse_args()
    try:
        proof=check(json.loads((ROOT/'content/terrain/relief.json').read_text()))
        # Build guards preserve the exact worker-verified fixed tile contract.
        shader=(ROOT/'shaders/battle.vert').read_text();client=(ROOT/'src/platform/linux/client.asm').read_text()
        for text in ('vec2(5375.,4750.)','cell%100,cell/100','off)*5.','grid.x>=86 && grid.x<94 && grid.y>=76 && grid.y<90'):
            assert text in shader, 'Refined shader tile changed; regenerate its policy and verify actual GL'
        assert 'mov edx,105000' in client, 'Refined draw count differs from verified tile'
        nav=(ROOT/'src/nav/squads.asm').read_text()
        assert re.search(r'^route_margin: dd 6\.0$',nav,re.M) and '%define NODES 27' in nav
    except (AssertionError,ValueError,OSError) as e:p.exit(2,f'terrain world: {e}\n')
    print(json.dumps({'terrain_world_checked':True,'patch':PATCH,**proof}))
if __name__=='__main__':main()
