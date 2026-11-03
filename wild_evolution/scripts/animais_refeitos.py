"""Wild Evolution - remodelo de 5 animais no estilo fofo (Blender 4.x/5.x, bpy).

Animais: unicornio, rinoceronte, triceratops, anquilossauro, ourico.
Referencias de anatomia usadas (fotos/ilustracoes reais):
  - Unicornio: corpo de cavalo, pescoco longo inclinado ~45 graus, focinho alongado,
    pernas finas com cascos, chifre espiral na testa, crina ao longo do pescoco.
  - Rinoceronte: corpo em barril, pernas curtas e grossas, cabeca baixa,
    chifre grande NA PONTA do nariz + chifre menor atras, dobras de pele no ombro.
  - Triceratops: cabeca enorme (~1/3 do corpo), gola ossea larga com bordas
    serrilhadas, 2 chifres longos sobre os olhos apontando para frente,
    chifre curto no nariz, bico, cauda grossa, patas dianteiras menores.
  - Anquilossauro: corpo baixo, largo e achatado, costas cobertas de placas
    (osteodermos) em fileiras, espinhos laterais, cabeca larga com chifrinhos
    nos cantos, cauda com clava ossea dupla na ponta.
  - Ourico: corpo redondo, centenas de espinhos cobrindo costas e topo da cabeca,
    rosto pontudo claro, barriga clara, patinhas curtas.

Uso:  python3 animais_refeitos.py [pasta_saida]
Gera: previews/<animal>.png, previews/folha_animais_refeitos.png, export/<animal>.fbx
"""
import bpy, math, os, sys
from mathutils import Vector

OUT = sys.argv[-1] if len(sys.argv) > 1 and os.path.isdir(sys.argv[-1]) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREV = os.path.join(OUT, "previews"); EXP = os.path.join(OUT, "export")
os.makedirs(PREV, exist_ok=True); os.makedirs(EXP, exist_ok=True)

# ---------------------------------------------------------------- utilidades
def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)

_mats = {}
def mat(name, rgb, rough=0.55, emit=0.0):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*rgb, 1)
        b.inputs["Emission Strength"].default_value = emit
    return m

def hexc(h):
    h = h.lstrip("#"); c = [int(h[i:i+2], 16)/255 for i in (0, 2, 4)]
    return tuple(x/12.92 if x <= 0.04045 else ((x+0.055)/1.055)**2.4 for x in c)

def quat_x_to(d):
    return Vector((1, 0, 0)).rotation_difference(d.normalized())

K = 1.35       # metaball com stiffness 2 aparece com ~57% do raio; 1.35 deixa o corpo cheinho sem inchar demais

class Blob:
    """Metaball: varias esferas/capsulas que se fundem num corpo liso."""
    def __init__(self, name, material, res=0.035):
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
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(self.ob.evaluated_get(dg))
        name = self.ob.name
        bpy.data.objects.remove(self.ob); bpy.data.metaballs.remove(self.mb)
        ob = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(ob)
        for p in me.polygons: p.use_smooth = True
        me.materials.append(self.material)
        return ob

def prim(kind, loc, scale=(1, 1, 1), rot=(0, 0, 0), material=None, **kw):
    f = {"sphere": bpy.ops.mesh.primitive_uv_sphere_add, "cone": bpy.ops.mesh.primitive_cone_add,
         "cyl": bpy.ops.mesh.primitive_cylinder_add, "torus": bpy.ops.mesh.primitive_torus_add}[kind]
    if kind == "sphere": kw.setdefault("segments", 24); kw.setdefault("ring_count", 12)
    if kind in ("cone", "cyl"): kw.setdefault("vertices", 16)
    f(location=loc, rotation=rot, **kw)
    ob = bpy.context.active_object; ob.scale = scale
    if kind != "torus":
        for p in ob.data.polygons: p.use_smooth = True
    if material: ob.data.materials.append(material)
    return ob

def cone_along(base, tip, r, material, verts=12):
    base, tip = Vector(base), Vector(tip); d = tip-base
    ob = prim("cone", (base+tip)/2, material=material, radius1=r, radius2=0, depth=d.length, vertices=verts)
    ob.rotation_mode = "QUATERNION"; ob.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized())
    return ob

_horn_id = [0]
def curved_horn(base, direction, up, length, r, material, bend=0.35, segs=12):
    """Chifre curvo e liso: cadeia de metaballs afinando ate a ponta."""
    base = Vector(base); d = Vector(direction).normalized(); u = Vector(up).normalized()
    _horn_id[0] += 1
    b = Blob(f"chifre{_horn_id[0]}", material, res=0.012)
    segs = max(segs, int(length/(r*0.08)))                   # bolas bem juntas = superficie lisa
    for i in range(segs+1):
        t = i/segs
        b.ball(base + d*length*t + u*length*bend*t*t, r*(1-0.8*t**0.9), stiff=3.0)
    return b.to_mesh()

def eyes(head_c, fwd_off, side, height, r, look=(0, -1, 0)):
    """Olhos grandes estilo fofo: esfera escura + brilho branco + palpebra leve."""
    black = mat("olho", hexc("#1b1414"), 0.15); white = mat("brilho", (1, 1, 1), 0.2, emit=1.0)
    hc = Vector(head_c)
    for s in (-1, 1):
        c = hc + Vector((s*side, fwd_off, height))
        prim("sphere", c, (r, r*0.75, r*1.1), material=black)
        prim("sphere", c + Vector((r*0.25, -r*0.6, r*0.4)), (r*0.28,)*3, material=white)
        prim("sphere", c + Vector((-r*0.2, -r*0.66, -r*0.35)), (r*0.12,)*3, material=white)

def cheeks(head_c, fwd_off, side, height, r):
    pink = mat("bochecha", hexc("#ff9fb0"), 0.8)
    for s in (-1, 1):
        prim("sphere", Vector(head_c) + Vector((s*side, fwd_off, height)), (r, r*0.4, r*0.6), material=pink)

def fib_points(n):
    ga = math.pi*(3-math.sqrt(5))
    for i in range(n):
        z = 1 - 2*(i+0.5)/n; rr = math.sqrt(1-z*z); t = ga*i
        yield Vector((math.cos(t)*rr, math.sin(t)*rr, z))

# ---------------------------------------------------------------- animais
def unicornio():
    skin = mat("uni_pelo", hexc("#f7f2fb")); hoof = mat("uni_casco", hexc("#c9a8e8"), 0.35)
    horn = mat("uni_chifre", hexc("#ffd36b"), 0.25); nose = mat("uni_focinho", hexc("#ffd6e4"))
    b = Blob("uni_corpo", skin)
    b.ell((0, 0, 0.95), 0.55, 0.62, 0.95, 0.62)              # tronco de cavalo (alongado)
    b.ball((0, 0.45, 1.0), 0.48)                              # anca
    b.cap((0, -0.55, 1.15), (0, -0.85, 1.75), 0.26)           # PESCOCO longo, inclinado ~45
    b.ell((0, -1.0, 2.0), 0.42, 0.85, 1.0, 0.85)              # cabeca
    b.cap((0, -1.15, 1.95), (0, -1.45, 1.75), 0.22)           # focinho alongado
    for x in (-0.28, 0.28):
        for y in (-0.42, 0.5):
            b.cap((x, y, 0.85), (x, y, 0.22), 0.13)           # pernas finas
    body = b.to_mesh()
    for x in (-0.28, 0.28):
        for y in (-0.42, 0.5):
            prim("cyl", (x, y, 0.1), (1, 1, 1), material=hoof, radius=0.15, depth=0.2)
    prim("sphere", (0, -1.52, 1.72), (0.2, 0.14, 0.15), material=nose)
    # chifre espiral: segmentos conicos sobrepostos (efeito de rosca)
    base = Vector((0, -1.2, 2.3)); tip = Vector((0, -1.45, 3.0)); n = 7
    for i in range(n):
        a0, a1 = base.lerp(tip, i/n), base.lerp(tip, (i+1.25)/n)
        cone_along(a0, a1, 0.12*(1-i/n)+0.02, horn, 16)
    # orelhas
    for s in (-1, 1):
        cone_along((s*0.2, -0.88, 2.3), (s*0.3, -0.82, 2.62), 0.09, skin)
    # crina arco-iris ao longo do pescoco e testa + cauda
    rainbow = ["#ff7b9c", "#ffb36b", "#ffe66b", "#8be08b", "#6bc5ff", "#b28bff"]
    pts = [Vector((0, -1.05, 2.42)), Vector((0, -0.85, 2.3)), Vector((0, -0.7, 2.0)),
           Vector((0, -0.55, 1.7)), Vector((0, -0.42, 1.45))]
    for i, p in enumerate(pts):
        c = rainbow[i % len(rainbow)]
        prim("sphere", p + Vector((0, 0.08, 0.05)), (0.15, 0.2, 0.17), material=mat("crina"+c, hexc(c), 0.6))
        prim("sphere", p + Vector((0.11, 0.12, -0.05)), (0.1, 0.17, 0.14), material=mat("crina"+c, hexc(c), 0.6))
        prim("sphere", p + Vector((-0.11, 0.12, -0.05)), (0.1, 0.17, 0.14), material=mat("crina"+c, hexc(c), 0.6))
    tail = [Vector((0, 0.95, 1.15)), Vector((0, 1.15, 1.0)), Vector((0, 1.25, 0.75)), Vector((0, 1.28, 0.5))]
    for i, p in enumerate(tail):
        c = rainbow[(i*2) % len(rainbow)]
        prim("sphere", p, (0.14, 0.17, 0.2), material=mat("crina"+c, hexc(c), 0.6))
    eyes((0, -1.0, 2.0), -0.22, 0.27, 0.05, 0.12)
    cheeks((0, -1.0, 2.0), -0.3, 0.3, -0.15, 0.08)

def rinoceronte():
    skin = mat("rino_pele", hexc("#9b98a3"), 0.75); horn = mat("rino_chifre", hexc("#e4d9c3"), 0.45)
    dark = mat("rino_escuro", hexc("#6f6b78"), 0.8)
    b = Blob("rino_corpo", skin)
    b.ell((0, 0.1, 0.95), 0.8, 0.9, 1.0, 0.82)                 # corpo em barril
    b.ball((0, -0.45, 1.05), 0.7)                              # ombro alto
    b.ell((0, -1.05, 0.85), 0.5, 0.8, 1.0, 0.75)               # cabeca grande e BAIXA
    b.cap((0, -1.2, 0.75), (0, -1.55, 0.6), 0.32)              # focinho largo
    for x in (-0.42, 0.42):
        for y in (-0.45, 0.6):
            b.cap((x, y, 0.7), (x, y, 0.2), 0.24)               # pernas curtas e grossas
    b.to_mesh()
    for x in (-0.42, 0.42):                                    # dedos/unhas
        for y in (-0.45, 0.6):
            for dx in (-0.1, 0, 0.1):
                prim("sphere", (x+dx, y-0.2, 0.08), (0.07, 0.06, 0.06), material=horn)
    # chifres: o grande NA PONTA do nariz, curvo para cima; o menor atras
    curved_horn((0, -1.58, 0.82), (0, -0.3, 1), (0, 1, 0.2), 0.62, 0.18, horn, bend=0.3, segs=9)
    curved_horn((0, -1.25, 1.05), (0, -0.1, 1), (0, 1, 0), 0.3, 0.13, horn, bend=0.2, segs=7)
    for s in (-1, 1):                                          # orelhas em tubo
        cone_along((s*0.3, -0.75, 1.05), (s*0.42, -0.68, 1.4), 0.11, skin)
        prim("sphere", (s*0.41, -0.7, 1.36), (0.07, 0.04, 0.07), material=dark)
        prim("sphere", (s*0.17, -1.72, 0.58), (0.05, 0.03, 0.04), material=dark)  # narinas
    cone_along((0, 0.95, 0.95), (0, 1.25, 0.6), 0.06, skin)
    prim("sphere", (0, 1.25, 0.6), (0.06, 0.06, 0.1), material=dark)                     # rabinho
    eyes((0, -1.05, 0.85), -0.25, 0.38, 0.12, 0.1)
    cheeks((0, -1.05, 0.85), -0.38, 0.38, -0.08, 0.08)

def triceratops():
    skin = mat("tri_pele", hexc("#7fc46a"), 0.65); belly = mat("tri_barriga", hexc("#d9f0a8"))
    frill = mat("tri_gola", hexc("#ff9a5c"), 0.6); horn = mat("tri_chifre", hexc("#fff1d6"), 0.4)
    beak = mat("tri_bico", hexc("#5a6b3a"), 0.4); spot = mat("tri_mancha", hexc("#5fa04e"))
    b = Blob("tri_corpo", skin)
    b.ell((0, 0.2, 0.95), 0.8, 0.95, 1.1, 0.85)                # corpo robusto
    b.cap((0, 0.9, 1.0), (0, 1.9, 0.6), 0.32)                  # cauda grossa
    b.ball((0, 2.0, 0.55), 0.14)
    b.ell((0, -0.95, 1.05), 0.6, 0.95, 1.0, 0.9)               # CABECA ENORME
    b.cap((0, -1.2, 0.95), (0, -1.6, 0.75), 0.3)               # focinho
    for x in (-0.45, 0.45):
        b.cap((x, -0.35, 0.75), (x, -0.4, 0.2), 0.2)            # patas dianteiras (menores)
        b.cap((x, 0.65, 0.8), (x, 0.65, 0.2), 0.26)             # patas traseiras (maiores)
    b.to_mesh()
    prim("sphere", (0, 0.1, 0.55), (0.6, 0.75, 0.35), material=belly)
    cone_along((0, -1.62, 0.78), (0, -1.86, 0.62), 0.16, beak)                 # bico
    # GOLA: escudo largo atras da cabeca, inclinado para tras, com bordas serrilhadas
    fr = prim("cyl", (0, -0.42, 1.5), material=frill, radius=0.8, depth=0.1, vertices=40)
    fr.rotation_euler = (math.radians(68), 0, 0); fr.scale = (1.2, 1, 1)   # em pe, virada para frente
    bpy.context.view_layer.update()
    mw = fr.matrix_world.copy()
    for i in range(15):                                        # epoccipitais (bordinhas)
        a = math.radians(-10 + i*200/14)
        loc = mw @ Vector((math.cos(a)*0.8, math.sin(a)*0.8, 0))
        if loc.z < 1.3: continue
        out = (mw.to_3x3() @ Vector((math.cos(a), math.sin(a), 0))).normalized()
        cone_along(loc - out*0.05, loc + out*0.22, 0.1, horn, 10)
    for s in (-1, 1):
        prim("sphere", mw @ Vector((s*0.45, 0.35, 0.07)), (0.17, 0.17, 0.05), material=spot)
    # 2 chifres LONGOS sobre os olhos, para frente e para cima; 1 curto no nariz
    for s in (-1, 1):
        curved_horn((s*0.26, -1.2, 1.3), (s*0.1, -0.8, 0.6), (0, -0.3, 0.6), 0.8, 0.12, horn, bend=0.15, segs=8)
    curved_horn((0, -1.5, 1.05), (0, -0.3, 1), (0, -1, 0), 0.25, 0.09, horn, bend=0.1)
    for x in (-0.45, 0.45):
        for y, z in ((-0.4, 0.08), (0.65, 0.08)):
            for dx in (-0.1, 0, 0.1):
                prim("sphere", (x+dx, y-0.19, z), (0.06, 0.06, 0.06), material=horn)
    for p in ((0.5, 0.0, 1.45), (-0.5, 0.3, 1.5), (0.3, 0.6, 1.65), (-0.2, -0.1, 1.75)):
        prim("sphere", p, (0.14, 0.14, 0.05), material=spot).rotation_euler = (0.3, 0.3*p[0], 0)
    eyes((0, -0.95, 1.05), -0.35, 0.38, 0.12, 0.12)
    cheeks((0, -0.95, 1.05), -0.5, 0.38, -0.12, 0.08)

def anquilossauro():
    skin = mat("anq_pele", hexc("#c79a5b"), 0.7); belly = mat("anq_barriga", hexc("#f0d9a8"))
    plate = mat("anq_placa", hexc("#8a5a3a"), 0.5); spike = mat("anq_espinho", hexc("#fff0d2"), 0.4)
    b = Blob("anq_corpo", skin)
    b.ell((0, 0.15, 0.7), 0.85, 1.25, 1.2, 0.6)                # corpo BAIXO, LARGO e achatado
    b.cap((0, 1.0, 0.65), (0, 2.1, 0.5), 0.22)                 # cauda
    b.ell((0, -1.05, 0.65), 0.45, 1.2, 0.9, 0.75)              # cabeca larga e baixa
    b.cap((0, -1.2, 0.6), (0, -1.5, 0.5), 0.25)
    for x in (-0.65, 0.65):
        for y in (-0.45, 0.75):
            b.cap((x, y, 0.5), (x*1.05, y, 0.15), 0.19)         # patas curtinhas
    b.to_mesh()
    prim("sphere", (0, 0.15, 0.4), (0.85, 1.0, 0.3), material=belly)
    # CLAVA da cauda: duas bolas laterais grandes + uma central
    for s in (-1, 1):
        prim("sphere", (s*0.2, 2.2, 0.5), (0.24, 0.26, 0.19), material=plate)
    prim("sphere", (0, 2.32, 0.5), (0.18, 0.2, 0.16), material=plate)
    # OSTEODERMOS: fileiras de placas nas costas (seguem a curva do corpo)
    rows = [(-0.55, 0.25), (-0.25, 0.37), (0.05, 0.42), (0.35, 0.4), (0.65, 0.32), (0.92, 0.18)]
    for y, h in rows:
        cols = (-0.66, -0.33, 0.0, 0.33, 0.66)
        for x in cols:
            z = 0.7 + h*(1 - (x/0.95)**2)**0.5 + 0.08
            cone_along((x, y, z-0.06), (x, y, z+0.1), 0.11, plate, 10)
    for i, y in enumerate((1.25, 1.55, 1.85)):                 # placas na cauda
        for s in (-1, 1):
            cone_along((s*0.12, y, 0.68 - i*0.04), (s*0.22, y, 0.8 - i*0.04), 0.07, plate, 8)
    # ESPINHOS LATERAIS apontando para fora
    for y in (-0.5, -0.15, 0.2, 0.55, 0.9):
        for s in (-1, 1):
            cone_along((s*0.95, y, 0.72), (s*1.3, y + 0.05, 0.68), 0.09, spike, 10)
    # chifrinhos nos cantos de tras da cabeca (piramidais)
    for s in (-1, 1):
        cone_along((s*0.42, -0.85, 0.85), (s*0.65, -0.65, 0.95), 0.1, spike, 6)
        cone_along((s*0.42, -1.05, 0.72), (s*0.6, -1.0, 0.65), 0.07, spike, 6)
    eyes((0, -1.05, 0.65), -0.3, 0.36, 0.18, 0.11)
    cheeks((0, -1.05, 0.65), -0.42, 0.38, -0.05, 0.08)

def ourico():
    face = mat("our_rosto", hexc("#f1d3ab"), 0.75); quill = mat("our_espinho", hexc("#6b4a33"), 0.6)
    tip = mat("our_ponta", hexc("#f3e6d2"), 0.6); dark = mat("our_escuro", hexc("#3a2a22"), 0.4)
    inner = mat("our_base", hexc("#8a6446"), 0.8)
    b = Blob("our_corpo", face)
    b.ell((0, 0.05, 0.62), 0.6, 1.0, 1.15, 0.95)               # corpo redondo
    b.ell((0, -0.55, 0.55), 0.38, 1.0, 1.0, 0.95)              # cabeca
    b.cap((0, -0.75, 0.5), (0, -1.05, 0.42), 0.15)              # focinho pontudo
    for x in (-0.3, 0.3):
        for y in (-0.3, 0.4):
            b.cap((x, y, 0.3), (x, y - 0.05, 0.06), 0.09)
    b.to_mesh()
    prim("sphere", (0, -1.1, 0.43), (0.08, 0.07, 0.07), material=dark)          # nariz
    # manto marrom por baixo dos espinhos
    prim("sphere", (0, 0.15, 0.72), (0.66, 0.72, 0.6), material=inner)
    # MUITOS espinhos: ~420 em distribuicao uniforme (fibonacci) sobre o manto,
    # inclinados para tras como num ourico de verdade, pontas claras.
    c = Vector((0, 0.15, 0.72)); R = Vector((0.66, 0.72, 0.6)); n = 0
    for d in fib_points(900):
        if d.z < -0.05: continue                               # nao na barriga
        if d.y < -0.55 and d.z < 0.55: continue                # deixa o rosto livre
        if d.y < -0.8: continue
        p = c + Vector((d.x*R.x, d.y*R.y, d.z*R.z))
        nrm = Vector((d.x/R.x, d.y/R.y, d.z/R.z)).normalized()
        dirv = (nrm + Vector((0, 0.85, 0.1))).normalized()     # para tras
        L = 0.3 + 0.08*((n*7919) % 5)/4
        cone_along(p - dirv*0.04, p + dirv*L*0.72, 0.035, quill, 6)
        cone_along(p + dirv*L*0.7, p + dirv*L, 0.019, tip, 6)
        n += 1
    for s in (-1, 1):                                          # orelhinhas
        prim("sphere", (s*0.3, -0.48, 0.92), (0.1, 0.05, 0.1), material=face)
    eyes((0, -0.55, 0.55), -0.28, 0.2, 0.1, 0.085)
    cheeks((0, -0.55, 0.55), -0.33, 0.25, -0.07, 0.06)
    print("espinhos do ourico:", n*2)

ANIMAIS = [("Unicornio", unicornio), ("Rinoceronte", rinoceronte), ("Triceratops", triceratops),
           ("Anquilossauro", anquilossauro), ("Ourico", ourico)]

# ---------------------------------------------------------------- render/export
def stage(size=640):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"; sc.cycles.samples = 48; sc.cycles.use_denoising = True
    sc.cycles.device = "CPU"
    sc.render.resolution_x = sc.render.resolution_y = size
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "Standard"
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (*hexc("#a8dc86"), 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
    gm = mat("chao", hexc("#9fd67c"), 0.9)
    prim("cyl", (0, 0, -0.01), material=gm, radius=30, depth=0.02, vertices=48)
    sun = bpy.data.lights.new("sol", "SUN"); sun.energy = 3.2; sun.angle = math.radians(12)
    so = bpy.data.objects.new("sol", sun); so.rotation_euler = (math.radians(40), math.radians(-20), math.radians(-35))
    sc.collection.objects.link(so)

def frame(objs):
    mn = Vector((1e9,)*3); mx = Vector((-1e9,)*3)
    for o in objs:
        for v in o.bound_box:
            w = o.matrix_world @ Vector(v)
            mn = Vector(map(min, mn, w)); mx = Vector(map(max, mx, w))
    ctr = (mn+mx)/2; size = (mx-mn).length
    cam = bpy.data.cameras.new("cam"); cam.lens = 50
    co = bpy.data.objects.new("cam", cam); bpy.context.scene.collection.objects.link(co)
    d = size*1.55
    co.location = ctr + Vector((-1.0, -0.75, 0.6)).normalized()*d
    co.rotation_euler = (ctr - co.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = co

def main():
    from PIL import Image, ImageDraw, ImageFont
    tiles = []
    only = os.environ.get("SO")
    for nome, fn in ANIMAIS:
        if only and only.lower() not in nome.lower(): continue
        clear(); fn()
        objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
        tris = sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in objs)
        print(f"{nome}: {len(objs)} pecas, {tris} triangulos")
        # export (antes do cenario) - FBX para importar no Roblox Studio
        for o in objs: o.select_set(True)
        bpy.ops.export_scene.fbx(filepath=os.path.join(EXP, nome.lower()+".fbx"), use_selection=True,
                                 apply_scale_options="FBX_SCALE_ALL", object_types={"MESH"})
        stage(); frame(objs)
        path = os.path.join(PREV, nome.lower()+".png")
        bpy.context.scene.render.filepath = path; bpy.ops.render.render(write_still=True)
        tiles.append((nome, path))
    if only: return
    W = 640; sheet = Image.new("RGB", (W*3, W*2 + 60), (168, 220, 134)); dr = ImageDraw.Draw(sheet)
    try: font = ImageFont.truetype("DejaVuSans-Bold.ttf", 34)
    except Exception: font = ImageFont.load_default()
    dr.text((20, 12), "Wild Evolution - animais refeitos com referencia (previa)", fill=(30, 50, 30), font=font)
    for i, (nome, p) in enumerate(tiles):
        im = Image.open(p); x, y = (i % 3)*W, 60 + (i//3)*W
        sheet.paste(im, (x, y)); dr.text((x+20, y+W-50), nome, fill=(25, 40, 25), font=font)
    sheet.save(os.path.join(PREV, "folha_animais_refeitos.png"))

main()
