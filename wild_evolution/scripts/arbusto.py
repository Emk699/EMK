"""Wild Evolution - arbusto de frutinhas (substitui o arbusto "bolha" verde do jogo).

Monte baixo e largo coberto de ROSETAS de folhas pontudas em camadas, com cachos de
frutinhas vermelhas/magenta facetadas (low-poly) e algumas maiores tipo framboesa.
Pecas agrupadas por material (folhas, base, frutas...) -> poucas MeshParts no Roblox.

Uso: python3 arbusto.py    -> previews/arbusto.png  e  export/arbusto.fbx
"""
import bpy, bmesh, math, os, random, sys
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from animais_refeitos import clear, mat, prim, fib_points, stage, frame, PREV, EXP

random.seed(7)
A, B, H = 2.1, 1.5, 0.62          # semi-eixos do monte (largura, profundidade, altura)

def leaf_mesh():
    """Folha pontuda com nervura central dobrada (fica com cara de folha de verdade)."""
    me = bpy.data.meshes.new("folha"); bm = bmesh.new()
    pts = [(0, 0, 0), (0.07, 0.1, 0.015), (0.09, 0.2, 0.02), (0.06, 0.3, 0.012), (0, 0.4, 0),
           (-0.06, 0.3, 0.012), (-0.09, 0.2, 0.02), (-0.07, 0.1, 0.015),
           (0, 0.1, 0.04), (0, 0.2, 0.045), (0, 0.3, 0.03)]
    v = [bm.verts.new(p) for p in pts]
    for f in ((0, 1, 8), (1, 2, 9, 8), (2, 3, 10, 9), (3, 4, 10),
              (0, 8, 7), (8, 9, 6, 7), (9, 10, 5, 6), (10, 4, 5)):
        bm.faces.new([v[i] for i in f])
    bm.to_mesh(me); bm.free()
    return me

def place(objs_by_mat, me, matrix):
    objs_by_mat.setdefault(me.name, []).append((me, matrix))

def surface(u, v):
    """Ponto e normal no monte (elipsoide achatado) para direcao (u,v,w)."""
    d = Vector((u, v, 0)); w = math.sqrt(max(0.0, 1 - d.length_squared))
    p = Vector((u*A, v*B, w*H))
    n = Vector((u/A, v/B, w/H)).normalized()
    return p, n

def build():
    clear()
    leaf_cols = [mat("folha_escura", "#2f8a2e", 0.55), mat("folha_media", "#3fa33a", 0.5),
                 mat("folha_clara", "#5cbf4a", 0.45)]
    base = mat("arbusto_base", "#256f25", 0.8)
    berry = [mat("fruta_vermelha", "#c8102e", 0.3, coat=0.6), mat("fruta_carmim", "#a3123f", 0.3, coat=0.6),
             mat("fruta_magenta", "#8c1f70", 0.3, coat=0.6)]
    rasp = mat("framboesa", "#b5122f", 0.45, bump=0.35, bump_scale=45)
    stem = mat("cabinho", "#4a3a1e", 0.7)

    # base (preenche os buracos entre as folhas)
    b = prim("sphere", (0, 0, 0), (A*0.93, B*0.93, H*0.92), material=base, segments=32, ring_count=16)

    leaf = leaf_mesh()
    parts = {m.name: bmesh.new() for m in leaf_cols}
    tmp = bmesh.new(); tmp.from_mesh(leaf)

    def add_leaf(col, M):
        bm = parts[col.name]; t = tmp.copy(); bmesh.ops.transform(t, matrix=M, verts=t.verts)
        me = bpy.data.meshes.new("t"); t.to_mesh(me); bm.from_mesh(me); bpy.data.meshes.remove(me); t.free()

    # centros das rosetas: distribuicao uniforme no topo + anel na borda
    centers = []
    for d in fib_points(110):
        if d.z < 0: continue
        centers.append((d.x*0.95, d.y*0.95))
    for i in range(18):
        a = i/18*2*math.pi + 0.1
        centers.append((math.cos(a)*0.98, math.sin(a)*0.98))
    rosettes = []
    for (u, v) in centers:
        p, n = surface(u, v)
        if p.z < 0.02: p.z = 0.05; n = (n + Vector((0, 0, 0.6))).normalized()
        frame_z = n; frame_x = frame_z.cross(Vector((0, 0, 1)) if abs(n.z) < 0.99 else Vector((1, 0, 0))).normalized()
        if frame_x.length < 0.1: frame_x = Vector((1, 0, 0))
        frame_y = frame_z.cross(frame_x)
        R = Matrix((frame_x, frame_y, frame_z)).transposed().to_4x4()
        sc = random.uniform(0.85, 1.2)
        # 3 aneis: folhas grandes escuras embaixo, medias, pequenas claras no centro
        for ring, (cnt, scale, tilt, col) in enumerate(((9, 1.25, 12, 0), (7, 0.95, 28, 1), (5, 0.6, 45, 2))):
            off = random.uniform(0, 1)
            for k in range(cnt):
                ang = (k + off + 0.5*ring)/cnt*2*math.pi
                M = (Matrix.Translation(p + n*0.02*ring) @ R @ Matrix.Rotation(ang, 4, "Z") @
                     Matrix.Rotation(math.radians(tilt + random.uniform(-6, 6)), 4, "X") @
                     Matrix.Scale(scale*sc, 4))
                add_leaf(leaf_cols[col], M)
        rosettes.append((p, n, sc))
    tmp.free()
    for name, bm in parts.items():
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(ob)
        me.materials.append(bpy.data.materials[name])

    # cachos de frutinhas facetadas em parte das rosetas
    random.shuffle(rosettes)
    berry_bm = {m.name: bmesh.new() for m in berry + [rasp, stem]}
    def add(kind, loc, r, subdiv=1):
        bm = berry_bm[kind.name]
        g = bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=r)
        bmesh.ops.translate(bm, vec=loc, verts=g["verts"])
    for i, (p, n, sc) in enumerate(rosettes[:34]):
        c = p + n*0.08
        if i % 5 == 0:                                        # framboesa grande no centro
            add(rasp, c + n*0.05, 0.17, 3)
            add(stem, c + n*0.22, 0.025, 1)
        k = random.randint(3, 6)
        for j in range(k):
            a = j/k*2*math.pi + random.uniform(-0.3, 0.3)
            t = n.cross(Vector((0, 0, 1)) if abs(n.z) < 0.99 else Vector((1, 0, 0))).normalized()
            t2 = n.cross(t)
            dist = 0.0 if (k == 3 and j == 0) else random.uniform(0.12, 0.2)
            loc = c + (t*math.cos(a) + t2*math.sin(a))*dist + n*random.uniform(0.0, 0.06)
            r = random.uniform(0.09, 0.14)
            add(random.choice(berry), loc + n*0.04, r, 2)
            add(stem, loc + n*r*0.95, 0.018, 0)
    for name, bm in berry_bm.items():
        if not bm.verts: bm.free(); continue
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(ob)
        me.materials.append(bpy.data.materials[name])
        if name == "framboesa":
            for pl in me.polygons: pl.use_smooth = True

    objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    tris = sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in objs)
    print(f"arbusto: {len(objs)} pecas, {tris} triangulos")
    for o in objs: o.select_set(True)
    bpy.ops.export_scene.fbx(filepath=os.path.join(EXP, "arbusto.fbx"), use_selection=True,
                             apply_scale_options="FBX_SCALE_ALL", object_types={"MESH"})
    stage(800)
    # piso de grama em vez do quadriculado liso
    g = bpy.data.materials["chao"]; N = g.node_tree.nodes; L = g.node_tree.links
    br = [n for n in N if n.bl_idname == "ShaderNodeTexBrick"][0]
    br.inputs["Color1"].default_value = (*__import__("animais_refeitos").hexc("#4c9a2f"), 1)
    br.inputs["Color2"].default_value = (*__import__("animais_refeitos").hexc("#58a836"), 1)
    frame(objs)
    cam = bpy.context.scene.camera
    ctr = Vector((0, 0, 0.3)); cam.location = ctr + Vector((-0.55, -1.0, 0.75)).normalized()*8.6
    cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.render.resolution_x = 1000; bpy.context.scene.render.resolution_y = 780
    bpy.context.scene.render.filepath = os.path.join(PREV, "arbusto.png")
    bpy.ops.render.render(write_still=True)

build()
