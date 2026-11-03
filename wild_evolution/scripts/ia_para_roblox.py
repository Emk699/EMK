"""Pega o modelo gerado por IA (TripoSR/Meshy, .glb ou .obj), limpa e deixa pronto pro Roblox.

- importa, coloca em pe (Z para cima), centraliza e apoia no chao
- escala para a altura desejada
- reduz triangulos (Decimate) para caber no limite de MeshPart do Roblox (20k)
- usa as cores de vertice do modelo
- exporta FBX + renderiza previa no estilo do jogo

Uso: python3 ia_para_roblox.py entrada.glb nome [altura_m] [max_tris] [rot_z_graus] [rot_x_graus] [rot_y_graus]
"""
import bpy, math, os, sys
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from animais_refeitos import clear, stage, PREV, EXP

args = sys.argv[1:]
src, nome = args[0], args[1]
altura = float(args[2]) if len(args) > 2 else 2.0
max_tris = int(args[3]) if len(args) > 3 else 15000
rotz = float(args[4]) if len(args) > 4 else 0.0
rotx = float(args[5]) if len(args) > 5 else 0.0

clear()
if src.endswith(".obj"):
    bpy.ops.wm.obj_import(filepath=src)
else:
    bpy.ops.import_scene.gltf(filepath=src)
obs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
for o in bpy.context.scene.objects: o.select_set(o in obs)
bpy.context.view_layer.objects.active = obs[0]
if len(obs) > 1: bpy.ops.object.join()
ob = bpy.context.view_layer.objects.active
ob.name = nome
from mathutils import Matrix
roty = float(args[6]) if len(args) > 6 else 0.0
ob.matrix_world = (Matrix.Rotation(math.radians(rotz), 4, "Z") @ Matrix.Rotation(math.radians(roty), 4, "Y") @
                   Matrix.Rotation(math.radians(rotx), 4, "X") @ ob.matrix_world)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# reduz triangulos
tris = sum(len(p.vertices)-2 for p in ob.data.polygons)
if tris > max_tris:
    d = ob.modifiers.new("Reduzir", "DECIMATE"); d.ratio = max_tris/tris
    bpy.ops.object.modifier_apply(modifier=d.name)
bpy.ops.object.shade_smooth()

# escala, centraliza e apoia no chao
bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
mn = Vector([min(v[i] for v in bb) for i in range(3)]); mx = Vector([max(v[i] for v in bb) for i in range(3)])
s = altura/(mx.z-mn.z); ob.scale = (s, s, s)
ob.location = (-(mn.x+mx.x)/2*s, -(mn.y+mx.y)/2*s, -mn.z*s)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# material com a cor de vertice
attrs = ob.data.color_attributes
if attrs:
    m = bpy.data.materials.new(nome+"_cor"); m.use_nodes = True
    N = m.node_tree.nodes; b = N["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.6
    a = N.new("ShaderNodeVertexColor"); a.layer_name = attrs[0].name
    g = N.new("ShaderNodeGamma"); g.inputs["Gamma"].default_value = 2.2   # cor veio em sRGB
    m.node_tree.links.new(a.outputs["Color"], g.inputs["Color"]); m.node_tree.links.new(g.outputs["Color"], b.inputs["Base Color"])
    ob.data.materials.clear(); ob.data.materials.append(m)

tris = sum(len(p.vertices)-2 for p in ob.data.polygons)
print(f"{nome}: {tris} triangulos, altura {altura} m, cores={bool(attrs)}")
ob.select_set(True)
bpy.ops.export_scene.fbx(filepath=os.path.join(EXP, nome+".fbx"), use_selection=True,
                         apply_scale_options="FBX_SCALE_ALL", object_types={"MESH"}, colors_type="SRGB")

stage(640)
sc = bpy.context.scene
cam = bpy.data.cameras.new("cam"); cam.lens = 55
co = bpy.data.objects.new("cam", cam); sc.collection.objects.link(co)
ctr = Vector((0, 0, altura*0.45)); r = max(ob.dimensions)
co.location = ctr + Vector((-1.0, -0.75, 0.55)).normalized()*r*1.9
co.rotation_euler = (ctr - co.location).to_track_quat("-Z", "Y").to_euler()
sc.camera = co
sc.render.filepath = os.path.join(PREV, nome+".png")
bpy.ops.render.render(write_still=True)
