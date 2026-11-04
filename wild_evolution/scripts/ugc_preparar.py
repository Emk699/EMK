"""Prepara um modelo (OBJ/FBX/GLB do Meshy etc.) para UGC do Roblox.

- 1 malha so, 1 textura (1024x1024 no maximo)
- reduz para no maximo MAX_TRIS triangulos (acessorio UGC: ~4000)
- escala: a maior medida vira TAMANHO studs (1 unidade do arquivo = 1 stud)
- centraliza na origem
Uso: python3 ugc_preparar.py entrada textura.png saida_sem_ext [tamanho_studs] [max_tris]
Importar no Studio: File > Import 3D, em File Dimensions escolher "Studs".
"""
import bpy, os, sys, math
from mathutils import Vector
src, tex, out = sys.argv[1], sys.argv[2], sys.argv[3]
TAM = float(sys.argv[4]) if len(sys.argv) > 4 else 4.0
MAX_TRIS = int(sys.argv[5]) if len(sys.argv) > 5 else 3900
bpy.ops.wm.read_factory_settings(use_empty=True)
ext = os.path.splitext(src)[1].lower()
{".obj": lambda: bpy.ops.wm.obj_import(filepath=src), ".fbx": lambda: bpy.ops.import_scene.fbx(filepath=src),
 ".glb": lambda: bpy.ops.import_scene.gltf(filepath=src), ".gltf": lambda: bpy.ops.import_scene.gltf(filepath=src)}[ext]()
obs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
for o in bpy.context.scene.objects: o.select_set(o in obs)
bpy.context.view_layer.objects.active = obs[0]
if len(obs) > 1: bpy.ops.object.join()
ob = bpy.context.view_layer.objects.active; ob.name = os.path.basename(out)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
tris = sum(len(p.vertices)-2 for p in ob.data.polygons)
if tris > MAX_TRIS:
    d = ob.modifiers.new("Reduzir", "DECIMATE"); d.ratio = (MAX_TRIS - 20)/tris; d.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=d.name)
bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.quads_convert_to_tris(); bpy.ops.object.mode_set(mode="OBJECT")
bb = [Vector(c) for c in ob.bound_box]
mn = Vector([min(v[i] for v in bb) for i in range(3)]); mx = Vector([max(v[i] for v in bb) for i in range(3)])
s = TAM/max(mx-mn); ob.location = -(mn+mx)/2*s; ob.scale = (s, s, s)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
# material com a textura reduzida
m = bpy.data.materials.new(ob.name+"_mat"); m.use_nodes = True
N = m.node_tree.nodes; b = N["Principled BSDF"]; t = N.new("ShaderNodeTexImage")
t.image = bpy.data.images.load(os.path.abspath(tex)); m.node_tree.links.new(t.outputs["Color"], b.inputs["Base Color"])
ob.data.materials.clear(); ob.data.materials.append(m)
tris = len(ob.data.polygons)
print(f"{ob.name}: {tris} triangulos, medidas {tuple(round(x,2) for x in ob.dimensions)} studs")
ob.select_set(True)
bpy.ops.export_scene.fbx(filepath=out+".fbx", use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, apply_scale_options="FBX_SCALE_NONE",
                         path_mode="COPY", embed_textures=True, axis_forward="-Z", axis_up="Y")
bpy.ops.wm.obj_export(filepath=out+".obj", export_selected_objects=True, path_mode="RELATIVE",
                      export_triangulated_mesh=True)
# previa
sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.samples = 48
sc.render.resolution_x, sc.render.resolution_y = 900, 600
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.75, 0.78, 0.82, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 1.2
sun = bpy.data.lights.new("s", "SUN"); sun.energy = 4; so = bpy.data.objects.new("s", sun)
so.rotation_euler = (math.radians(50), 0, math.radians(30)); sc.collection.objects.link(so)
cam = bpy.data.cameras.new("c"); cam.lens = 50; co = bpy.data.objects.new("c", cam); sc.collection.objects.link(co)
co.location = Vector((0.0, -1.0, 0.25)).normalized()*TAM*2.0
co.rotation_euler = (-co.location).to_track_quat("-Z", "Y").to_euler(); sc.camera = co
sc.render.filepath = out+"_previa.png"; bpy.ops.render.render(write_still=True)
