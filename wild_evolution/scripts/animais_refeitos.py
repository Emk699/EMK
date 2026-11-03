"""Wild Evolution - remodelo de 5 animais no estilo "Modelos Melhorados" (Blender 4.x/5.x, bpy).

Animais: unicornio, rinoceronte, triceratops, anquilossauro, ourico.
Segue a folha de referencia "Modelos Melhorados" enviada pelo usuario:
  - Unicornio: chibi, cabeca grande, pelo branco perolado, crina e cauda de arco-iris
    em MECHAS onduladas, chifre espiral dourado, focinho rosado, cascos lilas.
  - Rinoceronte: pele cinza com textura e manchas, corpo em barril, chifre grande
    curvo na ponta do nariz + chifre menor, orelhas em tubo, unhas claras.
  - Triceratops: verde com listras escuras nas costas, barriga clara, gola laranja
    grande e redonda com anel interno e ESPINHOS EM TODA a borda, 2 chifres longos
    curvos para frente + 1 no nariz, bico, cauda longa.
  - Anquilossauro: marrom, costas TODAS cobertas de osteodermos pontudos,
    espinhos laterais grandes, chifres na cabeca, clava na cauda.
  - Ourico: rosto creme, centenas de espinhos longos marrons com ponta clara,
    nariz preto, orelhinhas.

Uso:  python3 animais_refeitos.py          (SO=Ourico para gerar so um)
Gera: previews/<animal>.png, previews/folha_animais_refeitos.png, export/<animal>.fbx
"""
import bpy, math, os
from mathutils import Vector

OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREV = os.path.join(OUT, "previews"); EXP = os.path.join(OUT, "export")
os.makedirs(PREV, exist_ok=True); os.makedirs(EXP, exist_ok=True)

# ---------------------------------------------------------------- materiais
def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def hexc(h):
    h = h.lstrip("#"); c = [int(h[i:i+2], 16)/255 for i in (0, 2, 4)]
    return tuple(x/12.92 if x <= 0.04045 else ((x+0.055)/1.055)**2.4 for x in c)

def _set(sock_owner, name, val):
    if name in sock_owner.inputs: sock_owner.inputs[name].default_value = val

def mat(name, color, rough=0.55, metal=0.0, emit=0.0, bump=0.0, bump_scale=9.0,
        spots=None, stripes=None, coat=0.0, film=0.0):
    """spots=(cor2, escala, quantidade 0-1)   stripes=(cor2, escala)"""
    m = bpy.data.materials.get(name)
    if m: return m
    rgb = hexc(color) if isinstance(color, str) else color
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    b = N["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*rgb, 1); b.inputs["Emission Strength"].default_value = emit
    if coat: _set(b, "Coat Weight", coat); _set(b, "Coat Roughness", 0.15)
    if film: _set(b, "Thin Film Thickness", film); _set(b, "Thin Film IOR", 1.4)
    tc = N.new("ShaderNodeTexCoord")
    pattern = spots or stripes
    if pattern:
        if spots:
            t = N.new("ShaderNodeTexNoise"); t.inputs["Scale"].default_value = spots[1]
            t.inputs["Detail"].default_value = 3
            lo = 0.62 - 0.12*spots[2]
        else:
            t = N.new("ShaderNodeTexWave"); t.wave_type = "BANDS"; t.bands_direction = "Y"
            t.inputs["Scale"].default_value = stripes[1]; t.inputs["Distortion"].default_value = 4
            lo = 0.55
        L.new(tc.outputs["Object"], t.inputs["Vector"])
        mr = N.new("ShaderNodeMapRange"); mr.inputs[1].default_value = lo; mr.inputs[2].default_value = lo+0.06
        L.new(t.outputs["Fac"], mr.inputs[0])
        mix = N.new("ShaderNodeMix"); mix.data_type = "RGBA"
        mix.inputs[6].default_value = (*rgb, 1)
        c2 = hexc(pattern[0]); mix.inputs[7].default_value = (*c2, 1)
        L.new(mr.outputs[0], mix.inputs[0]); L.new(mix.outputs[2], b.inputs["Base Color"])
    if bump:
        nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = bump_scale
        nz.inputs["Detail"].default_value = 8
        L.new(tc.outputs["Object"], nz.inputs["Vector"])
        bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump
        bp.inputs["Distance"].default_value = 0.03
        L.new(nz.outputs["Fac"], bp.inputs["Height"]); L.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m

# ---------------------------------------------------------------- geometria
def quat_x_to(d):
    return Vector((1, 0, 0)).rotation_difference(d.normalized())

K = 1.35   # metaball com stiffness 2 aparece com ~57% do raio; 1.35 deixa o corpo cheinho

class Blob:
    """Metaball: varias esferas/capsulas que se fundem num corpo liso."""
    def __init__(self, name, material, res=0.03):
        self.mb = bpy.data.metaballs.new(name)
        self.mb.resolution = res; self.mb.render_resolution = res
        self.ob = bpy.data.objects.new(name, self.mb)
        bpy.context.collection.objects.link(self.ob)
        self.material = material
    def ball(self, co, r, stiff=2.0):
        e = self.mb.elements.new(type="BALL"); e.co = co; e.radius = r*K; e.stiffness = stiff; return e
    def ell(self, co, r, sx, sy, sz, stiff=2.0):
        e = self.mb.elements.new(type="ELLIPSOID"); e.co = co; e.radius = r*K
        e.size_x, e.size_y, e.size_z = sx, sy, sz; e.stiffness = stiff; return e
    def cap(self, a, b, r, stiff=2.0):
        a, b = Vector(a), Vector(b)
        e = self.mb.elements.new(type="CAPSULE"); e.co = (a+b)/2; e.radius = r*K
        e.size_x = (b-a).length/2; e.rotation = quat_x_to(b-a); e.stiffness = stiff; return e
    def to_mesh(self):
        return bake(self.ob, self.material, data=self.mb)

def bake(ob, material, data=None):
    """Converte metaball/curva em malha (para exportar FBX)."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    name = ob.name; bpy.data.objects.remove(ob)
    if data is not None:
        (bpy.data.metaballs if isinstance(data, bpy.types.MetaBall) else bpy.data.curves).remove(data)
    new = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(new)
    for p in me.polygons: p.use_smooth = True
    me.materials.append(material)
    return new

def prim(kind, loc, scale=(1, 1, 1), rot=(0, 0, 0), material=None, **kw):
    f = {"sphere": bpy.ops.mesh.primitive_uv_sphere_add, "cone": bpy.ops.mesh.primitive_cone_add,
         "cyl": bpy.ops.mesh.primitive_cylinder_add, "torus": bpy.ops.mesh.primitive_torus_add,
         "plane": bpy.ops.mesh.primitive_plane_add}[kind]
    if kind == "sphere": kw.setdefault("segments", 24); kw.setdefault("ring_count", 12)
    if kind in ("cone", "cyl"): kw.setdefault("vertices", 16)
    f(location=loc, rotation=rot, **kw)
    ob = bpy.context.active_object; ob.scale = scale
    if kind not in ("plane",):
        for p in ob.data.polygons: p.use_smooth = True
    if material: ob.data.materials.append(material)
    return ob

def cone_along(base, tip, r, material, verts=12):
    base, tip = Vector(base), Vector(tip); d = tip-base
    ob = prim("cone", (base+tip)/2, material=material, radius1=r, radius2=0, depth=d.length, vertices=verts)
    ob.rotation_mode = "QUATERNION"; ob.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized())
    return ob

_uid = [0]
def uid(p):
    _uid[0] += 1; return f"{p}{_uid[0]}"

def curved_horn(base, direction, up, length, r, material, bend=0.35, tipr=0.12):
    """Chifre curvo e liso: cadeia de metaballs afinando ate a ponta."""
    base = Vector(base); d = Vector(direction).normalized(); u = Vector(up).normalized()
    b = Blob(uid("chifre"), material, res=0.012)
    segs = max(12, int(length/(r*0.08)))
    for i in range(segs+1):
        t = i/segs
        b.ball(base + d*length*t + u*length*bend*t*t, r*(1-(1-tipr)*t**0.9), stiff=3.0)
    return b.to_mesh()

def strand(pts, r, material, profile=(0.7, 1.0, 1.0, 0.85, 0.55, 0.15)):
    """Mecha de cabelo: curva NURBS com espessura variavel (crina/cauda)."""
    cu = bpy.data.curves.new(uid("mecha"), "CURVE"); cu.dimensions = "3D"
    cu.bevel_depth = r; cu.bevel_resolution = 4; cu.resolution_u = 10; cu.use_fill_caps = True
    sp = cu.splines.new("NURBS"); sp.points.add(len(pts)-1)
    for i, p in enumerate(pts):
        sp.points[i].co = (*p, 1)
        t = i/(len(pts)-1); k = t*(len(profile)-1); j = min(int(k), len(profile)-2)
        sp.points[i].radius = profile[j] + (profile[j+1]-profile[j])*(k-j)
    sp.use_endpoint_u = True; sp.order_u = 3
    ob = bpy.data.objects.new(cu.name, cu); bpy.context.collection.objects.link(ob)
    return bake(ob, material, data=cu)

def eyes(head_c, fwd_off, side, height, r, lids=None):
    """Olho escuro brilhante + 1 brilho grande + 1 pequeno (igual a referencia)."""
    black = mat("olho", "#120d0b", 0.08, coat=1.0); white = mat("brilho", (1, 1, 1), 0.2, emit=2.0)
    hc = Vector(head_c)
    for s in (-1, 1):
        c = hc + Vector((s*side, fwd_off, height))
        prim("sphere", c, (r, r*0.8, r*1.05), material=black)
        prim("sphere", c + Vector((r*0.3, -r*0.68, r*0.38)), (r*0.24,)*3, material=white)
        prim("sphere", c + Vector((-r*0.2, -r*0.74, -r*0.32)), (r*0.1,)*3, material=white)
        if lids:  # palpebra da cor da pele (deixa o olhar mais natural)
            lid = prim("sphere", c + Vector((0, 0.02*r, r*0.35)), (r*1.12, r*0.9, r*0.7), material=lids)

def fib_points(n):
    ga = math.pi*(3-math.sqrt(5))
    for i in range(n):
        z = 1 - 2*(i+0.5)/n; rr = math.sqrt(1-z*z); t = ga*i
        yield Vector((math.cos(t)*rr, math.sin(t)*rr, z))

# ---------------------------------------------------------------- animais
RAINBOW = ["#ff6f91", "#ffa15c", "#ffe066", "#7ed67e", "#5cc8ff", "#a98bff"]

def unicornio():
    coat = mat("uni_pelo", "#fbf8ff", 0.35, coat=0.6, film=380)
    muzzle = mat("uni_focinho", "#ffe3ec", 0.45, coat=0.3)
    inner = mat("uni_orelha", "#ffb6cc", 0.6)
    hoof = mat("uni_casco", "#b9a2e8", 0.25, metal=0.2, coat=0.6)
    horn = mat("uni_chifre", "#f2c14e", 0.28, metal=0.85)
    b = Blob("uni_corpo", coat)
    b.ell((0, 0.05, 0.78), 0.5, 0.62, 0.95, 0.62)           # tronco curtinho e redondo (chibi)
    b.ball((0, 0.38, 0.8), 0.36)                             # anca
    b.cap((0, -0.3, 0.9), (0, -0.55, 1.35), 0.24)            # pescoco grosso
    b.ell((0, -0.68, 1.62), 0.5, 0.9, 1.0, 0.92)             # CABECAO
    for x in (-0.2, 0.2):
        for y in (-0.3, 0.4):
            b.cap((x, y, 0.62), (x, y, 0.16), 0.11)           # pernas
    b.to_mesh()
    prim("sphere", (0, -1.0, 1.5), (0.24, 0.24, 0.2), material=muzzle)          # focinho rosado
    nos = mat("uni_narina", "#d9879c", 0.5)
    for s in (-1, 1):
        prim("sphere", (s*0.09, -1.21, 1.53), (0.035, 0.02, 0.025), material=nos)
    for x in (-0.2, 0.2):
        for y in (-0.3, 0.4):
            prim("cyl", (x, y, 0.09), material=hoof, radius=0.13, depth=0.18)
    # orelhas com miolo rosa
    for s in (-1, 1):
        cone_along((s*0.2, -0.55, 1.88), (s*0.3, -0.5, 2.18), 0.085, coat)
        cone_along((s*0.205, -0.6, 1.9), (s*0.29, -0.565, 2.12), 0.05, inner)
    # chifre espiral dourado (segmentos sobrepostos = rosca)
    base = Vector((0, -0.86, 1.95)); tip = Vector((0, -1.0, 2.6)); n = 12
    for i in range(n):
        cone_along(base.lerp(tip, i/n), base.lerp(tip, (i+1.6)/n), 0.095*(1-i/n)+0.02, horn, 20)
    # CRINA: mechas onduladas de arco-iris caindo pelos dois lados do pescoco
    r0, r1 = Vector((0, -0.62, 1.98)), Vector((0, -0.18, 1.12)); nroots = 9
    for i in range(nroots):
        t = i/(nroots-1); root = r0.lerp(r1, t)
        col = mat("crina"+RAINBOW[min(int(t*6), 5)], RAINBOW[min(int(t*6), 5)], 0.35, coat=0.4)
        for s in (-1, 0, 1):
            L = 0.38 + 0.08*(1-t)
            pts = [root,
                   root + Vector((s*0.10, 0.10, 0.06)),
                   root + Vector((s*0.22, 0.16, -L*0.35)),
                   root + Vector((s*0.26, 0.12, -L*0.7)),
                   root + Vector((s*0.18, 0.2, -L))]
            if s == 0: pts = [p + Vector((0, 0.04, 0.02)) for p in pts[:3]] + [root + Vector((0.05, 0.3, -0.12))]
            strand(pts, 0.075, col)
    # topete caindo de lado na testa
    for s, c in ((-1, RAINBOW[0]), (1, RAINBOW[5])):
        strand([Vector((0, -0.66, 2.03)), Vector((s*0.08, -0.8, 2.02)), Vector((s*0.2, -0.9, 1.9)),
                Vector((s*0.24, -0.92, 1.76))], 0.065, mat("crina"+c, c, 0.35, coat=0.4))
    # CAUDA: mechas grossas em arco
    for k, c in enumerate(RAINBOW):
        s = (k-2.5)/2.5
        strand([Vector((s*0.05, 0.55, 0.95)), Vector((s*0.08, 0.72, 1.08)), Vector((s*0.14, 0.92, 0.95)),
                Vector((s*0.16, 0.98, 0.65)), Vector((s*0.1, 0.9, 0.42)), Vector((s*0.05, 0.78, 0.38))],
               0.085, mat("crina"+c, c, 0.35, coat=0.4))
    eyes((0, -0.68, 1.62), -0.27, 0.25, 0.04, 0.12)

def rinoceronte():
    skin = mat("rino_pele", "#8f8c92", 0.8, bump=0.12, bump_scale=10, spots=("#7a767d", 9, 0.3))
    horn = mat("rino_chifre", "#e8dcc0", 0.5, bump=0.15, bump_scale=30)
    dark = mat("rino_escuro", "#58535a", 0.8)
    nail = mat("rino_unha", "#efe6d4", 0.4)
    b = Blob("rino_corpo", skin)
    b.ell((0, 0.15, 0.95), 0.8, 0.9, 1.05, 0.8)                # corpo em barril
    b.ball((0, -0.45, 1.08), 0.68)                             # cupim do ombro
    b.ell((0, -1.0, 0.86), 0.48, 0.78, 1.0, 0.72)              # cabeca baixa
    b.cap((0, -1.15, 0.78), (0, -1.5, 0.62), 0.3)              # focinho largo
    for x in (-0.42, 0.42):
        for y in (-0.45, 0.65):
            b.cap((x, y, 0.75), (x, y, 0.2), 0.24)              # pernas grossas
    b.to_mesh()
    for x in (-0.42, 0.42):
        for y in (-0.45, 0.65):
            for dx in (-0.11, 0, 0.11):
                prim("sphere", (x+dx, y-0.24, 0.08), (0.075, 0.07, 0.065), material=nail)
    curved_horn((0, -1.55, 0.82), (0, -0.35, 1), (0, 1, 0.15), 0.7, 0.2, horn, bend=0.35)
    curved_horn((0, -1.22, 1.05), (0, -0.15, 1), (0, 1, 0), 0.32, 0.14, horn, bend=0.2)
    for s in (-1, 1):                                          # orelhas em tubo
        e = Blob(uid("orelha"), skin, res=0.015)
        e.cap((s*0.3, -0.72, 1.12), (s*0.42, -0.62, 1.45), 0.08); e.ball((s*0.43, -0.62, 1.47), 0.09)
        e.to_mesh()
        prim("sphere", (s*0.45, -0.68, 1.46), (0.05, 0.03, 0.06), material=dark)
        prim("sphere", (s*0.15, -1.74, 0.6), (0.045, 0.03, 0.04), material=dark)   # narinas
    strand([Vector((0, 1.0, 1.05)), Vector((0, 1.15, 0.9)), Vector((0, 1.2, 0.65))], 0.05, skin)
    eyes((0, -1.0, 0.86), -0.22, 0.4, 0.12, 0.075)

def triceratops():
    skin = mat("tri_pele", "#74b552", 0.6, bump=0.12, bump_scale=18, stripes=("#5f9c45", 1.6))
    belly = mat("tri_barriga", "#e3efb0", 0.7, bump=0.15, bump_scale=18)
    frill = mat("tri_gola", "#f39a35", 0.55, bump=0.2, bump_scale=10, spots=("#e5792a", 5, 0.35))
    ring = mat("tri_anel", "#d9661c", 0.5)
    spike = mat("tri_espinho", "#ffd166", 0.45)
    horn = mat("tri_chifre", "#efe2c4", 0.4, bump=0.1, bump_scale=30)
    beak = mat("tri_bico", "#6e6a5f", 0.4)
    b = Blob("tri_corpo", skin)
    b.ell((0, 0.25, 0.92), 0.78, 0.95, 1.12, 0.82)             # corpo robusto
    b.cap((0, 0.95, 0.95), (0, 1.75, 0.6), 0.3)                # cauda longa
    b.cap((0, 1.75, 0.6), (0, 2.3, 0.4), 0.16)
    b.ell((0, -0.9, 1.0), 0.58, 0.95, 1.05, 0.88)              # cabeca grande
    b.cap((0, -1.1, 0.92), (0, -1.5, 0.75), 0.28)              # focinho
    for x in (-0.45, 0.45):
        b.cap((x, -0.3, 0.72), (x, -0.35, 0.18), 0.2)           # patas dianteiras
        b.cap((x, 0.7, 0.78), (x, 0.7, 0.18), 0.26)             # patas traseiras
    b.to_mesh()
    prim("sphere", (0, 0.15, 0.55), (0.6, 0.8, 0.33), material=belly)
    curved_horn((0, -1.52, 0.86), (0, -1, -0.4), (0, 0, -1), 0.28, 0.13, beak, bend=0.4, tipr=0.25)  # bico
    # GOLA grande e redonda, em pe atras da cabeca
    fr = prim("cyl", (0, -0.45, 1.55), material=frill, radius=0.85, depth=0.1, vertices=48)
    fr.rotation_euler = (math.radians(66), 0, 0); fr.scale = (1.18, 1, 1)
    bpy.context.view_layer.update(); mw = fr.matrix_world.copy(); R3 = mw.to_3x3()
    tor = prim("torus", mw @ Vector((0, 0, -0.06)), material=ring, major_radius=0.58, minor_radius=0.05)
    tor.rotation_euler = fr.rotation_euler; tor.scale = (1.18, 1, 0.6)
    for i in range(22):                                        # espinhos em TODA a borda
        a = math.radians(-35 + i*250/21)
        loc = mw @ Vector((math.cos(a)*0.85, math.sin(a)*0.85, 0))
        out = (R3 @ Vector((math.cos(a), math.sin(a), 0))).normalized()
        cone_along(loc - out*0.06, loc + out*0.24, 0.085, spike, 10)
    # 2 chifres longos curvando para frente + 1 curto no nariz
    for s in (-1, 1):
        curved_horn((s*0.27, -1.12, 1.32), (s*0.18, -0.75, 0.55), (0, -0.4, 0.6), 0.85, 0.11, horn, bend=0.2)
    curved_horn((0, -1.45, 1.0), (0, -0.35, 1), (0, -1, 0), 0.24, 0.085, horn, bend=0.15)
    for x in (-0.45, 0.45):
        for y in (-0.35, 0.7):
            for dx in (-0.1, 0, 0.1):
                prim("sphere", (x+dx, y-0.2, 0.08), (0.06, 0.06, 0.055), material=horn)
    eyes((0, -0.9, 1.0), -0.36, 0.37, 0.12, 0.1)

def anquilossauro():
    skin = mat("anq_pele", "#b07c48", 0.7, bump=0.15, bump_scale=16)
    belly = mat("anq_barriga", "#ecd3a0", 0.7)
    plate = mat("anq_placa", "#8a5634", 0.5, bump=0.3, bump_scale=25)
    spike = mat("anq_espinho", "#f3e2be", 0.4)
    b = Blob("anq_corpo", skin)
    b.ell((0, 0.15, 0.68), 0.85, 1.25, 1.2, 0.6)               # corpo baixo, largo e achatado
    b.cap((0, 1.0, 0.62), (0, 2.1, 0.45), 0.2)                 # cauda
    b.ell((0, -1.05, 0.62), 0.45, 1.2, 0.9, 0.75)              # cabeca larga
    b.cap((0, -1.2, 0.58), (0, -1.5, 0.48), 0.24)
    for x in (-0.62, 0.62):
        for y in (-0.45, 0.75):
            b.cap((x, y, 0.5), (x*1.05, y, 0.14), 0.19)
    b.to_mesh()
    prim("sphere", (0, 0.15, 0.38), (0.85, 1.0, 0.3), material=belly)
    for s in (-1, 1):                                          # clava da cauda
        prim("sphere", (s*0.2, 2.2, 0.45), (0.24, 0.26, 0.19), material=plate)
    prim("sphere", (0, 2.32, 0.45), (0.18, 0.2, 0.16), material=plate)
    # OSTEODERMOS cobrindo TODAS as costas (distribuicao uniforme na casca)
    c = Vector((0, 0.15, 0.68)); R = Vector((0.82, 0.8, 0.42)); n = 0
    for d in fib_points(520):
        if d.z < 0.28: continue
        p = c + Vector((d.x*R.x, d.y*R.y, d.z*R.z))
        nrm = Vector((d.x/R.x, d.y/R.y, d.z/R.z)).normalized()
        big = 1.0 + 0.35*(abs(d.x) > 0.6)
        cone_along(p - nrm*0.02, p + nrm*0.12*big, 0.055*big, plate, 8)
        n += 1
    for i, y in enumerate((1.15, 1.42, 1.7, 1.95)):            # placas da cauda
        for s in (-1, 1):
            cone_along((s*0.12, y, 0.62 - i*0.05), (s*0.25, y, 0.74 - i*0.05), 0.065, plate, 8)
    for y in (-0.5, -0.18, 0.15, 0.48, 0.8):                    # espinhos laterais grandes
        for s in (-1, 1):
            cone_along((s*0.88, y, 0.66), (s*1.3, y + 0.08, 0.62), 0.1, spike, 12)
    for s in (-1, 1):                                          # chifres da cabeca
        cone_along((s*0.42, -0.85, 0.82), (s*0.66, -0.62, 0.95), 0.1, spike, 8)
        cone_along((s*0.42, -1.05, 0.7), (s*0.62, -1.0, 0.62), 0.07, spike, 8)
    for x, y in ((-0.18, -1.0), (0.18, -1.0), (0, -0.85), (-0.25, -0.82), (0.25, -0.82)):
        prim("sphere", (x, y, 0.94), (0.1, 0.1, 0.04), material=plate)
    eyes((0, -1.05, 0.62), -0.3, 0.36, 0.16, 0.085)
    print("osteodermos:", n)

def ourico():
    face = mat("our_rosto", "#e9cfa4", 0.75, bump=0.15, bump_scale=40)
    quill = mat("our_espinho", "#5e4030", 0.55); tip = mat("our_ponta", "#f2e6d0", 0.5)
    inner = mat("our_base", "#7a5640", 0.85, bump=0.3, bump_scale=40)
    dark = mat("our_nariz", "#1a1210", 0.2, coat=1.0); ear = mat("our_orelha", "#d9a98a", 0.7)
    b = Blob("our_corpo", face)
    b.ell((0, 0.05, 0.6), 0.6, 1.0, 1.15, 0.92)
    b.ell((0, -0.55, 0.55), 0.38, 1.0, 1.0, 0.95)
    b.cap((0, -0.75, 0.5), (0, -1.05, 0.42), 0.15)
    for x in (-0.28, 0.28):
        for y in (-0.3, 0.4):
            b.cap((x, y, 0.3), (x, y - 0.05, 0.06), 0.09)
    b.to_mesh()
    prim("sphere", (0, -1.11, 0.43), (0.075, 0.065, 0.065), material=dark)
    prim("sphere", (0, 0.15, 0.7), (0.66, 0.72, 0.58), material=inner)
    c = Vector((0, 0.15, 0.7)); R = Vector((0.66, 0.72, 0.58)); n = 0
    for d in fib_points(1500):                                  # ~650 espinhos longos
        if d.z < -0.12: continue
        if d.y < -0.5 and d.z < 0.6: continue
        if d.y < -0.82: continue
        p = c + Vector((d.x*R.x, d.y*R.y, d.z*R.z))
        nrm = Vector((d.x/R.x, d.y/R.y, d.z/R.z)).normalized()
        dirv = (nrm + Vector((0, 0.9, 0.05))).normalized()
        L = 0.36 + 0.12*((n*7919) % 7)/6
        cone_along(p - dirv*0.04, p + dirv*L*0.68, 0.03, quill, 5)
        cone_along(p + dirv*L*0.66, p + dirv*L, 0.017, tip, 5)
        n += 1
    for s in (-1, 1):
        prim("sphere", (s*0.3, -0.45, 0.88), (0.1, 0.05, 0.1), material=ear)
    eyes((0, -0.55, 0.55), -0.27, 0.21, 0.1, 0.09)
    print("espinhos do ourico:", n)

ANIMAIS = [("Unicornio", unicornio), ("Rinoceronte", rinoceronte), ("Triceratops", triceratops),
           ("Anquilossauro", anquilossauro), ("Ourico", ourico)]

# ---------------------------------------------------------------- render/export
def stage(size=640):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"; sc.cycles.samples = 64; sc.cycles.use_denoising = True
    sc.cycles.device = "CPU"
    sc.render.resolution_x = sc.render.resolution_y = size
    sc.view_settings.view_transform = "Standard"
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (*hexc("#cfe8ff"), 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.45
    # piso verde quadriculado (estilo baseplate)
    g = bpy.data.materials.new("chao"); g.use_nodes = True; N = g.node_tree.nodes; L = g.node_tree.links
    br = N.new("ShaderNodeTexBrick"); br.offset = 0; br.squash = 1
    br.inputs["Color1"].default_value = (*hexc("#4fa83a"), 1); br.inputs["Color2"].default_value = (*hexc("#55b03f"), 1)
    br.inputs["Mortar"].default_value = (*hexc("#2f7a26"), 1)
    br.inputs["Scale"].default_value = 1; br.inputs["Mortar Size"].default_value = 0.015
    br.inputs["Brick Width"].default_value = 1.0; br.inputs["Row Height"].default_value = 1.0
    tc = N.new("ShaderNodeTexCoord"); L.new(tc.outputs["Object"], br.inputs["Vector"])
    bs = N["Principled BSDF"]; bs.inputs["Roughness"].default_value = 0.7
    L.new(br.outputs["Color"], bs.inputs["Base Color"])
    prim("plane", (0, 0, 0), material=g, size=60).rotation_euler = (0, 0, math.radians(20))
    sun = bpy.data.lights.new("sol", "SUN"); sun.energy = 2.2; sun.angle = math.radians(8)
    so = bpy.data.objects.new("sol", sun); so.rotation_euler = (math.radians(45), math.radians(-15), math.radians(-50))
    sc.collection.objects.link(so)
    fill = bpy.data.lights.new("preenchimento", "AREA"); fill.energy = 120; fill.size = 6
    fo = bpy.data.objects.new("preenchimento", fill); fo.location = (-4, -3, 3)
    fo.rotation_euler = (Vector((0, 0, 1)) - fo.location).to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(fo)

def frame(objs):
    mn = Vector((1e9,)*3); mx = Vector((-1e9,)*3)
    for o in objs:
        for v in o.bound_box:
            w = o.matrix_world @ Vector(v)
            mn = Vector(map(min, mn, w)); mx = Vector(map(max, mx, w))
    ctr = (mn+mx)/2; size = (mx-mn).length
    cam = bpy.data.cameras.new("cam"); cam.lens = 55
    co = bpy.data.objects.new("cam", cam); bpy.context.scene.collection.objects.link(co)
    co.location = ctr + Vector((-1.0, -0.6, 0.58)).normalized()*size*1.45
    co.rotation_euler = (ctr - co.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = co

def main():
    from PIL import Image, ImageDraw, ImageFont
    tiles = []; only = os.environ.get("SO")
    for nome, fn in ANIMAIS:
        if only and only.lower() not in nome.lower(): continue
        clear(); fn()
        objs = [o for o in bpy.context.scene.objects if o.type == "MESH" and not o.hide_render]
        for o in [o for o in bpy.context.scene.objects if o.hide_render]: bpy.data.objects.remove(o)
        tris = sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in objs)
        print(f"{nome}: {len(objs)} pecas, {tris} triangulos")
        for o in objs: o.select_set(True)
        bpy.ops.export_scene.fbx(filepath=os.path.join(EXP, nome.lower()+".fbx"), use_selection=True,
                                 apply_scale_options="FBX_SCALE_ALL", object_types={"MESH"})
        stage(); frame(objs)
        path = os.path.join(PREV, nome.lower()+".png")
        bpy.context.scene.render.filepath = path; bpy.ops.render.render(write_still=True)
        tiles.append((nome, path))
    if only: return
    W = 640; sheet = Image.new("RGB", (W*3, W*2 + 60), (160, 214, 128)); dr = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 34)
    except Exception:
        font = ImageFont.load_default()
    dr.text((20, 12), "Wild Evolution - Modelos Melhorados", fill=(20, 40, 20), font=font)
    for i, (nome, p) in enumerate(tiles):
        im = Image.open(p); x, y = (i % 3)*W, 60 + (i//3)*W
        sheet.paste(im, (x, y)); dr.text((x+20, y+W-50), nome, fill=(15, 30, 15), font=font)
    sheet.save(os.path.join(PREV, "folha_animais_refeitos.png"))

if __name__ == "__main__":
    main()
