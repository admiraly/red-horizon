#!/usr/bin/env python3
"""Offline authored Blender geometry/action bake. Run with Blender, never runtime.

blender -b --python tools/bake_models.py -- --sources .tools/asset-sources \
    --output content/models/battle.rham --report content/models/bake-report.json
Optional --config accepts a JSON list of the role settings below. Sources and
licences are pinned separately by content/model-sources.json; no assets invented.
"""
import argparse
import array
import hashlib
import json
import math
import pathlib
import struct
import sys

DEFAULTS = [
    dict(file='Character_Soldier.blend', role=0, forward='-Y', size=1.8, height=True,
         objects=['Body','Head','ShoulderPad.L','ShoulderPad.R','AK'],
         clips=[['Idle',0],['Walk',1],['Run_Gun',2],['Idle_Shoot',3]], high=1000, low=96),
    dict(file='Tank.blend', role=1, forward='-X', size=6, clips=[['Forward',1]], high=1500, low=96),
    dict(file='Tank3.blend', role=2, forward='-X', size=7, clips=[['Tank_Forward',1]], high=1500, low=96),
    dict(file='craft_speederD.glb', role=3, forward='+Y', size=12, high=1500, low=96),
    dict(file='AK.blend', role=4, forward='-X', size=.8, high=1000, low=96),
    dict(file='BrickWall_1.blend', role=5, forward='-Y', size=6, high=1000, low=96),
    dict(file='Tree_1.blend', role=6, forward='-Y', size=7, height=True, high=1000, low=96),
    dict(file='Structure_1.blend', role=7, forward='-Y', size=8, high=1500, low=96),
]

def basis(forward):
    from mathutils import Matrix
    return {'-Y':Matrix(((1,0,0),(0,0,1),(0,-1,0))),
            '+Y':Matrix(((-1,0,0),(0,0,1),(0,1,0))),
            '-X':Matrix(((0,-1,0),(0,0,1),(-1,0,0))),
            '+X':Matrix(((0,1,0),(0,0,1),(1,0,0)))}[forward]


def colour(material):
    if material is None:return (0.5,0.5,0.5)
    value=material.diffuse_color
    if material.node_tree:
        for node in material.node_tree.nodes:
            if node.type=='BSDF_PRINCIPLED':
                value=node.inputs['Base Color'].default_value
                if node.inputs['Base Color'].is_linked:
                    raise ValueError('Texture material requires explicit palette sampling: '+material.name)
                break
    return tuple(max(0,min(1,float(v))) for v in value[:3])


def prepare(objects, budget):
    """Collapse/triangulate the original mesh BEFORE skinning, once per LOD.

    Applying at the front of the stack preserves vertex groups and bone parents.
    All later frames consequently use exactly the same triangulated topology.
    """
    import bpy
    total=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in objects)
    ratio=min(1,budget/max(1,total)*.92)
    for obj in objects:
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True);bpy.context.view_layer.objects.active=obj
        for mod in list(obj.modifiers):
            if mod.type not in ('ARMATURE',):obj.modifiers.remove(mod)
        mod=obj.modifiers.new('RHAM offline collapse','DECIMATE');mod.ratio=ratio
        while obj.modifiers[0]!=mod:bpy.ops.object.modifier_move_up(modifier=mod.name)
        bpy.ops.object.modifier_apply(modifier=mod.name)
        mod=obj.modifiers.new('RHAM fixed triangles','TRIANGULATE')
        while obj.modifiers[0]!=mod:bpy.ops.object.modifier_move_up(modifier=mod.name)
        bpy.ops.object.modifier_apply(modifier=mod.name)
    count=sum(len(o.data.polygons) for o in objects)
    if count>budget and budget<=100:
        # Tiny disconnected fittings have a collapse floor. Distant LOD drops
        # the smallest authored components rather than synthesizing geometry.
        import bmesh
        meshes=[];components=[]
        for obj in objects:
            bm=bmesh.new();bm.from_mesh(obj.data);meshes.append((obj,bm))
            unseen=set(bm.faces)
            while unseen:
                face=unseen.pop();group={face};pending=[face]
                while pending:
                    for vertex in pending.pop().verts:
                        for adjacent in vertex.link_faces:
                            if adjacent in unseen:
                                unseen.remove(adjacent);group.add(adjacent);pending.append(adjacent)
                components.append((sum(f.calc_area() for f in group),bm,group))
        for area,bm,group in sorted(components,key=lambda c:c[0]):
            if count<=budget:break
            if count-len(group)<64:continue
            bmesh.ops.delete(bm,geom=list(group),context='FACES');count-=len(group)
        for obj,bm in meshes:bm.to_mesh(obj.data);bm.free()
    if count>budget:raise ValueError(f'Decimation exceeded budget {count}>{budget}')
    return count


def capture(objects, rotation):
    import bpy
    deps=bpy.context.evaluated_depsgraph_get()
    vertices=[];topology=[]
    for obj in objects:
        evaluated=obj.evaluated_get(deps);mesh=evaluated.to_mesh()
        matrix=evaluated.matrix_world
        normal_matrix=matrix.to_3x3().inverted().transposed()
        colours=[colour(m) for m in mesh.materials]
        for polygon in mesh.polygons:
            if len(polygon.vertices)!=3:raise ValueError('Nontriangle evaluated topology')
            topology.append((obj.name,tuple(polygon.vertices),polygon.material_index))
            for vi in polygon.vertices:
                v=mesh.vertices[vi]
                position=rotation@(matrix@v.co)
                # Authored flat material faces survive collapse with hard normals.
                normal=rotation@(normal_matrix@polygon.normal);normal.normalize()
                rgb=colours[polygon.material_index] if colours else (.5,.5,.5)
                vertices.append((tuple(position),tuple(normal),rgb))
        evaluated.to_mesh_clear()
    return vertices,topology


def bake_one(source, spec, lod):
    import bpy
    if source.suffix=='.blend':bpy.ops.wm.open_mainfile(filepath=str(source))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(source))
    if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
    objects=sorted([o for o in bpy.data.objects if o.type=='MESH' and
                    ('objects' not in spec or o.name in spec['objects'])],key=lambda o:o.name)
    if not objects:raise ValueError('No selected source meshes')
    triangles=prepare(objects,spec['high' if lod==0 else 'low'])
    rotation=basis(spec['forward'])
    arms=[o for o in bpy.data.objects if o.type=='ARMATURE']
    actions=spec.get('clips',[])
    if actions:
        for arm in arms:
            arm.animation_data_create();arm.animation_data.action=bpy.data.actions[actions[0][0]]
    bpy.context.scene.frame_set(0 if actions else 1)
    reference,topology=capture(objects,rotation)
    roots=[(arm,next((b.name for b in arm.pose.bones if b.parent is None),None)) for arm in arms]
    def root_position():
        from mathutils import Vector
        if not roots:return Vector((0,0,0))
        arm,name=roots[0]
        return rotation@(arm.matrix_world@arm.pose.bones[name].matrix.translation)
    reference_root=root_position();removed_motion=0.
    lo=[min(p[0][i] for p in reference) for i in range(3)]
    hi=[max(p[0][i] for p in reference) for i in range(3)]
    centre=((lo[0]+hi[0])/2,lo[1],(lo[2]+hi[2])/2)
    dimension=hi[1]-lo[1] if spec.get('height') else max(hi[0]-lo[0],hi[2]-lo[2])
    scale=spec['size']/dimension
    clips=[];frames=[];authored=[]
    if not actions:actions=[[None,0]]
    for name,semantic in actions:
        if name:
            action=bpy.data.actions.get(name)
            if action is None:raise ValueError('Missing authored action '+name)
            for arm in arms:arm.animation_data.action=action
            first,last=map(float,action.frame_range)
            fps=bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
            samples=[first+i*fps/12 for i in range(max(1,math.ceil((last-first)/fps*12)))]
        else:samples=[1]
        if len(frames)+len(samples)>64:raise ValueError('More than64 baked frames')
        clips.append((len(frames),len(samples),12.,semantic))
        hashes=[]
        for frame in samples:
            bpy.context.scene.frame_set(math.floor(frame),subframe=frame%1)
            vertices,actual_topology=capture(objects,rotation)
            if actual_topology!=topology:raise ValueError('Animation changes triangle topology')
            root_delta=root_position()-reference_root
            removed_motion=max(removed_motion,root_delta.length*scale)
            packed=array.array('f')
            for position,normal,rgb in vertices:
                pos=tuple((position[i]-root_delta[i]-centre[i])*scale for i in range(3))
                if not all(math.isfinite(v) and abs(v)<10000 for v in pos):raise ValueError('Invalid source position')
                if not .999<math.sqrt(sum(v*v for v in normal))<1.001:raise ValueError('Invalid source normal')
                packed.extend((*pos,1.,*normal,0.,*rgb,1.))
            if sys.byteorder!='little':packed.byteswap()
            raw=packed.tobytes();hashes.append(hashlib.sha256(raw).hexdigest())
            frames.append(raw)
        authored.append(dict(action=name,semantic=semantic,frames=len(samples),distinct_frames=len(set(hashes))))
    # One common ground offset across all clips preserves authored body bobbing;
    # no per-frame deformation-bound recentering or source root motion is added.
    ground=min(struct.unpack_from('<f',raw,i+4)[0] for raw in frames for i in range(0,len(raw),48))
    if ground:
        grounded=[]
        for raw in frames:
            data=array.array('f');data.frombytes(raw)
            if sys.byteorder!='little':data.byteswap()
            for i in range(1,len(data),12):data[i]-=ground
            if sys.byteorder!='little':data.byteswap()
            grounded.append(data.tobytes())
        frames=grounded
    all_positions=[]
    for raw in frames:
        data=array.array('f');data.frombytes(raw)
        if sys.byteorder!='little':data.byteswap()
        all_positions.extend(tuple(data[i:i+3]) for i in range(0,len(data),12))
    mins=[min(p[i] for p in all_positions) for i in range(3)]
    maxs=[max(p[i] for p in all_positions) for i in range(3)]
    dims=[maxs[i]-mins[i] for i in range(3)]
    radius=max(math.sqrt(sum(v*v for v in p)) for p in all_positions)
    report=dict(role=spec['role'],lod=lod,file=source.name,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                forward=spec['forward'],root_bones=[name for _,name in roots],root_motion_removed_max_metres=removed_motion,ground_offset_metres=-ground,triangles=triangles,vertex_count=triangles*3,frame_count=len(frames),
                bounds_min=mins,bounds_max=maxs,dimensions=dims,radius=radius,clips=authored)
    return frames,clips,report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources',type=pathlib.Path,required=True)
    parser.add_argument('--output',type=pathlib.Path,required=True)
    parser.add_argument('--report',type=pathlib.Path)
    parser.add_argument('--config',type=pathlib.Path)
    parser.add_argument('--allow-missing',action='store_true',help='Development slice only; report skipped sources')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    specs=json.loads(args.config.read_text()) if args.config else DEFAULTS
    mesh_records=[];clip_records=[];payload=[];reports=[];missing=[];vec4_count=0
    for spec in specs:
        source=args.sources/spec['file']
        if not source.is_file():
            if not args.allow_missing:raise FileNotFoundError(source)
            missing.append(spec['file']);continue
        for lod in (0,1):
            frames,clips,report=bake_one(source,spec,lod)
            base=vec4_count;clip_first=len(clip_records)
            clip_records.extend(struct.pack('<IIfI',*c) for c in clips)
            for raw in frames:payload.append(raw);vec4_count+=len(raw)//16
            fields=(spec['role'],lod,report['vertex_count'],report['frame_count'],base,clip_first,len(clips),
                    int(any(c['distinct_frames']>1 for c in report['clips'])),1.,report['radius'],*report['dimensions'],0,0,0)
            mesh_records.append(struct.pack('<8I5f3I',*fields));reports.append(report)
            print('BAKED',json.dumps(report),flush=True)
    mesh_offset=48;clip_offset=mesh_offset+len(mesh_records)*64
    data_offset=clip_offset+len(clip_records)*16;total=data_offset+vec4_count*16
    if total>=64*1024*1024:raise ValueError('RHAM exceeds64MiB')
    header=struct.pack('<4s11I',b'RHAM',1,total,len(mesh_records),len(clip_records),vec4_count,mesh_offset,clip_offset,data_offset,0,0,0)
    blob=b''.join([header,*mesh_records,*clip_records,*payload])
    assert len(blob)==total
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(blob)
    report=dict(format='RHAM',version=1,total_bytes=total,sha256=hashlib.sha256(blob).hexdigest(),
                sample_fps=12,frame_limit_per_mesh=64,low_lod_triangle_budget=96,
                low_lod_policy='collapse original skinned triangles, then drop smallest disconnected fittings if necessary',
                grounding='single common offset across clips; specific rootbone translation removed',
                limitations=['Tank3 is a second authored tank used for artillery visual role, not a howitzer model',
                             'Kenney craft_speederD is a static spaceship fallback, not an animated military jet',
                             'BrickWall_1 is a fortification wall used for bunker role, not an enclosed bunker',
                             'Solid source material colors baked; textured materials rejected'],
                blender_version=__import__('bpy').app.version_string,mesh_count=len(reports),vec4_count=vec4_count,
                missing_sources=missing,meshes=reports)
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,indent=2)+'\n')
    print('RHAM COMPLETE',json.dumps({k:v for k,v in report.items() if k!='meshes'}),flush=True)

if __name__=='__main__':main()
