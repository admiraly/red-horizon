#!/usr/bin/env python3
"""Development-only exact dependency gates, before nested fast/job checks."""
import pathlib
root=pathlib.Path(__file__).resolve().parents[2]
source=(root/'tests/test_tools.py').read_text().split("    fast=dev('test','--suite','fast')")[0]
source=source.replace("ROOT=pathlib.Path(__file__).resolve().parents[1]", "ROOT=pathlib.Path("+repr(str(root))+")")
source+="    print(json.dumps({'suite':'supply-route-exact-build-dependencies','passed':True,'exact_player_consumers':len(player_dependencies),'direct_and_nested_exact_sets':True,'single_module_and_shader_isolation':True,'source_preservation':True,'client_exact_set':True,'limits':'Focused dependency prefix; nested fast and remaining tools checks are separate.'}))\n"
exec(compile(source,str(root/'tests/test_tools.py'),'exec'))
