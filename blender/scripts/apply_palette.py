"""Apply one of the four dark lobby palettes to Photobooth_Cinema.blend and render every view.

Layout and furniture stay as designed; only colours change (walls, ceiling, woodwork, sofa,
curtain, accents, the three backdrop blinds). The booth interior stays light cream.
Render fixes from fix_scene.py are reused: hidden lights switched back on, floor-plan
annotations hidden, EEVEE + AgX, globe pendants toned down, ceiling made visible to cameras.
Downlights are raised ~1/3 because dark walls reflect far less light.

Result: <name>_<palette>.blend next to the original (never overwritten) and one JPEG per camera.

Run: blender -b -P blender/scripts/apply_palette.py -- --blend <file.blend> --out <dir> [--palette dem_than]
"""
import argparse
import json
import math
import os
import sys

import bpy
import bmesh  # after bpy: the standalone bpy module registers bmesh on import
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fix_scene as fx  # noqa: E402

# Removed at the client's request: every prop on the accessory rack.
CLIENT_REMOVED = ["B_Book", "B_GoldBall", "B_Hat", "B_Pile", "B_PotPlant", "B_Vase"]

PALETTES = {
    "mocha": {
        "walls": "#6B5445", "ceiling": "#EDE5DA", "woodwork": "#F2EDE6", "sofa": "#E4D8C6",
        "curtain": "#4A382D", "accent": "#2A2725", "accent_metal": False,
        "blinds": ["#EFE6D8", "#8C6E5A", "#2A2725"],
    },
    "xanh_reu": {
        "walls": "#3E4A3F", "ceiling": "#EDE7DC", "woodwork": "#EFEAE2", "sofa": "#A8744A",
        "curtain": "#A8744A", "accent": "#B08D57", "accent_metal": True,
        "blinds": ["#EFE6D8", "#4A5A4B", "#7A5A43"],
    },
    "navy": {
        "walls": "#22303F", "ceiling": "#EFEAE2", "woodwork": "#F2EFEA", "sofa": "#D9CBB5",
        "curtain": "#2A3A4F", "accent": "#B08D57", "accent_metal": True,
        "blinds": ["#F2F0EC", "#D8CAB3", "#2A3A4F"],
    },
    "dem_than": {
        "walls": "#3B3936", "ceiling": "#45423E", "woodwork": "#262524", "sofa": "#E3DACB",
        "curtain": "#E3DACB", "accent": "#B08D57", "accent_metal": True,
        "blinds": ["#F2F0EC", "#D8CAB3", "#2A2928"],
    },
    # Budget concept: one oxblood colour drenched over walls, ceiling, skirting and the drywall booth
    # (paint is the cheapest high-impact finish), cream furniture, black/cream checker floor, brass,
    # no reception counter (self-service).
    "cherry": {
        "walls": "#5A1E26", "ceiling": "#5A1E26", "woodwork": "#EDE4D8", "sofa": "#EDE4D8",
        "curtain": "#E9DFD0", "accent": "#B08D57", "accent_metal": True,
        "blinds": ["#F2F0EC", "#E6C3BE", "#2A2928"],
        "skirting": "#5A1E26", "booth_shell": "#5A1E26", "floor_checker": True,
        "brass_objects": ["D_Mirror_Frame"], "hide_prefixes": ["C_", *CLIENT_REMOVED],
        "checker_tile": 0.5, "review_fixes": True, "sofa_model": "kidney", "bench": False,
    },
    # Light version for a small room with no daylight: pale blush walls (Munsell value ~8.5) and a warm
    # white ceiling reflect most of the light; the booth stays deep cherry as the one bold element, and
    # cherry skirting carries that colour round the room. Black/cream checker grounds the pale walls.
    "cherry_light": {
        "walls": "#EFDDD4", "ceiling": "#F6F0E8", "woodwork": "#F3ECE3", "sofa": "#EDE4D8",
        "curtain": "#EFE6D8", "accent": "#B08D57", "accent_metal": True,
        "blinds": ["#F2F0EC", "#E6C3BE", "#2A2928"],
        "skirting": "#7A1F2B", "booth_shell": "#7A1F2B", "floor_checker": True, "checker_tile": 0.5,
        "brass_objects": ["D_Mirror_Frame"], "hide_prefixes": ["C_", *CLIENT_REMOVED],
        "review_fixes": True, "sofa_model": "kidney", "bench": False,
        "exposure": 0.0, "downlight_boost": 1.0,  # pale walls need no compensation for dark paint
    },
    # Soft minimal (client inspiration: white clinic lounges): warm white walls and ceiling, light oak
    # floor, oat linen curtain on a greige booth, cream boucle, plaster and light oak, black lettering.
    # One statement pendant over a plaster table, cove light round the ceiling, an olive tree for colour.
    "soft_minimal": {
        "walls": "#F3F0EA", "ceiling": "#F7F5F1", "woodwork": "#F2EEE7", "sofa": "#EDE6DA",
        "curtain": "#D9CCBA", "accent": "#1E1C1A", "accent_metal": False,
        "blinds": ["#F2F0EC", "#E6D8CC", "#B9ADA0"],
        "skirting": "#F3F0EA", "booth_shell": "#E4DCD1", "floor_oak": True,
        "brass_objects": ["D_Mirror_Frame"],
        "hide_prefixes": ["C_", *CLIENT_REMOVED, "A_Floor_Tube", "Room_Pendant"],
        "review_fixes": True, "sofa_model": "kidney", "bench": False, "pay_point": False,
        "neon_heart": False, "minimal_decor": True,
        "light_color": (1.0, 0.8, 0.6),  # ~3000K: 2700K turns warm white walls peach
        "exposure": 0.0, "downlight_boost": 1.0,
    },
}
# Design review of the cherry concept (see apply_review_fixes).
PENDANT_MIN_CLEARANCE = 2.1  # m above the floor for anything hanging over a walkway
WARM_LIGHT = (1.0, 0.71, 0.42)  # ~2700K
WARM_LIGHT_SKIP = ("Booth_Flash_Light",)  # the booth keeps neutral light for skin tones
HEART_SCALE = 1.6  # the tallest heart that fits between the curtain head and the booth top
DEFAULT_PALETTE = "soft_minimal"

# Materials in the file, grouped by palette role.
MATERIALS = {
    "walls": ["Paint_Wall"],
    "ceiling": ["Ceiling"],
    "woodwork": ["Melamine_Plain", "Rack_Paint", "Rack_Back", "Marble_White", "Paint_Skirting"],
    "sofa": ["Sofa_Boucle"],
    "curtain": ["Velvet_Door"],
    "accent": ["Butter_Text", "Frame_Black"],
}
CORNICE = "Room_Crown_Moulding"
# Backdrop blinds, in the order of the palette's "blinds" list and of cameras 01a / 01b / 01c.
BLINDS = [("Rem_Ivory", "BlindBar_Ivory", "Cam_01a_cabin_rem01_trang"),
          ("Rem_Sky", "BlindBar_Sky", "Cam_01b_cabin_rem02_be"),
          ("Rem_DeepBlue", "BlindBar_DeepBlue", "Cam_01c_cabin_rem03_xam")]
PLAN_PREFIXES = ("Plan_", "PL_")
PLAN_CAMERAS = ("Cam_05_mat_bang", "Cam_07_mat_bang_den")
DOWNLIGHT_BOOST = 1.33  # ~1,800 lm -> ~2,400 lm fittings
BOOTH_FLASH_BOOST = 6.0  # the booth interior rendered grey; a photo booth is lit bright
EXPOSURE = 0.5  # AgX renders mid-tones darker than Standard
# Hollywood mirror: globe bulbs on brass sockets, mounted on the mirror frame.
MIRROR_BULB_DIAMETER = 0.05  # G16.5-style globe
SOCKET_LENGTH = 0.02
SOCKET_RADIUS = 0.011
FULL_RES = True  # 100% of the file resolution (1600x1000); False renders quick 50% previews


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--palette", default=DEFAULT_PALETTE, choices=sorted(PALETTES))
    parser.add_argument("--no-render", action="store_true")
    return parser.parse_args(argv)


def principled(mat):
    if not mat or not mat.use_nodes:
        return None
    return next((n for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)


def darker(hex_color, factor):
    h = hex_color.lstrip("#")
    return "#" + "".join(f"{int(int(h[i:i + 2], 16) * factor):02X}" for i in (0, 2, 4))


def recolor(name, hex_color, metal=False):
    mat = bpy.data.materials.get(name)
    bsdf = principled(mat)
    if bsdf is None:
        fx.log(f"material {name} not found")
        return
    sock = bsdf.inputs["Base Color"]
    if sock.is_linked and sock.links[0].from_node.bl_idname == "ShaderNodeValToRGB":
        # Keep the fabric/stone variation: remap the ramp from a darker shade to the target.
        ramp = sock.links[0].from_node.color_ramp
        ramp.elements[0].color = fx.hex_rgba(darker(hex_color, 0.8))
        ramp.elements[-1].color = fx.hex_rgba(hex_color)
    else:
        if sock.is_linked:
            mat.node_tree.links.remove(sock.links[0])
        sock.default_value = fx.hex_rgba(hex_color)
    if metal:
        bsdf.inputs["Metallic"].default_value = 1.0
        bsdf.inputs["Roughness"].default_value = 0.3
    fx.log(f"{name} -> {hex_color}{' brass' if metal else ''}")


def fix_visibility(scene):
    for o in scene.objects:
        if o.name.startswith(PLAN_PREFIXES):
            o.hide_render = True
        elif o.type == "LIGHT" and o.hide_render:
            o.hide_render = False
            fx.log(f"light on: {o.name}")
        elif o.type == "MESH" and hasattr(o, "visible_camera") and not o.visible_camera and not o.hide_render:
            o.visible_camera = True
            fx.log(f"made visible to camera: {o.name}")
    for name in ("Ceiling",):
        mat = bpy.data.materials.get(name)
        if mat and getattr(mat, "use_backface_culling", False):
            mat.use_backface_culling = False
            fx.log(f"{name}: backface culling off")


def ensure_visible(scene, name):
    """Log every reason an object could be missing from camera renders, and undo it."""
    o = scene.objects.get(name)
    if o is None:
        fx.log(f"{name}: not in scene")
        return
    lo, hi = fx.bbox_world([o])
    fx.log(f"{name}: z {lo.z:.2f}..{hi.z:.2f}, hide_render={o.hide_render}, "
           f"visible_camera={getattr(o, 'visible_camera', None)}, holdout={getattr(o, 'is_holdout', None)}, "
           f"collections={[c.name for c in o.users_collection]}")
    o.hide_render = False
    if hasattr(o, "visible_camera"):
        o.visible_camera = True
    if getattr(o, "is_holdout", False):
        o.is_holdout = False

    def walk(lc):
        yield lc
        for child in lc.children:
            yield from walk(child)

    names = {c.name for c in o.users_collection}
    for lc in walk(bpy.context.view_layer.layer_collection):
        if lc.name in names:
            fx.log(f"  collection {lc.name}: exclude={lc.exclude}, holdout={lc.holdout}, "
                   f"indirect_only={lc.indirect_only}, hide_render={lc.collection.hide_render}")
            lc.exclude = False
            lc.holdout = False
            lc.indirect_only = False
            lc.collection.hide_render = False
    for slot in o.material_slots:
        mat = slot.material
        if mat:
            fx.log(f"  material {mat.name}: backface_culling={getattr(mat, 'use_backface_culling', None)}, "
                   f"camera_culling={getattr(mat, 'use_backface_culling_shadow', None)}")
            if hasattr(mat, "use_backface_culling"):
                mat.use_backface_culling = False


def boost_booth_flash(scene):
    light = scene.objects.get("Booth_Flash_Light")
    if light:
        light.data.energy *= BOOTH_FLASH_BOOST
        fx.log(f"Booth_Flash_Light x{BOOTH_FLASH_BOOST} -> {light.data.energy:.0f}W")


def tone_down_globes():
    bsdf = principled(bpy.data.materials.get("Globe"))
    if bsdf:
        bsdf.inputs["Emission Strength"].default_value *= 0.35
        fx.set_input(bsdf, ["Emission Color", "Emission"], (*fx.WARM_2700K, 1.0))
        bsdf.inputs["Base Color"].default_value = fx.hex_rgba("#F4EEE6")
        fx.log("Globe: emission x0.35, 2700K opal")


def boost_downlights(scene, factor=DOWNLIGHT_BOOST):
    for o in scene.objects:
        if o.type == "LIGHT" and o.name.startswith("Room_Downlight"):
            o.data.energy *= factor
    fx.log(f"downlights x{factor}")


def mat_frosted_bulb():
    mat, bsdf = fx.new_material("PB_Bulb_Frosted")
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf.inputs["Base Color"].default_value = fx.hex_rgba("#FFF4E6")
    bsdf.inputs["Roughness"].default_value = 0.35
    fx.set_input(bsdf, ["Emission Color", "Emission"], (1.0, 0.72, 0.45, 1.0))
    # Brighter where the globe faces the viewer, dimmer at the rim, so it reads as a sphere.
    weight = nodes.new("ShaderNodeLayerWeight")
    weight.inputs["Blend"].default_value = 0.5
    ramp = nodes.new("ShaderNodeMapRange")
    ramp.inputs["To Min"].default_value = 8.0
    ramp.inputs["To Max"].default_value = 2.0
    links.new(weight.outputs["Facing"], ramp.inputs["Value"])
    links.new(ramp.outputs["Result"], bsdf.inputs["Emission Strength"])
    return mat


def smooth_mesh(name, build):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    build(bm)
    bm.to_mesh(me)
    bm.free()
    for poly in me.polygons:
        poly.use_smooth = True
    return me


def mount_mirror_bulbs(scene, room_center):
    """Replace the bulbs floating on the wall with globe bulbs on sockets fixed to the mirror frame."""
    frame = scene.objects.get("D_Mirror_Frame")
    glass = scene.objects.get("D_Mirror_Glass")
    old = sorted((o for o in scene.objects if o.name.startswith("D_Bulb")), key=lambda o: o.name)
    if not frame or not glass or not old:
        fx.log("mirror bulbs: frame, glass or bulbs not found, skipped")
        return
    count, parent, coll = len(old), old[0].parent, old[0].users_collection[0]

    lo, hi = fx.bbox_world([frame])
    center, dims = (lo + hi) / 2, hi - lo
    axis = min(range(3), key=lambda i: dims[i])  # frame thickness = mirror normal
    normal = Vector((0.0, 0.0, 0.0))
    normal[axis] = 1.0 if room_center[axis] > center[axis] else -1.0
    u_i, v_i = [i for i in range(3) if i != axis]
    u, v = Vector((0.0, 0.0, 0.0)), Vector((0.0, 0.0, 0.0))
    u[u_i], v[v_i] = 1.0, 1.0
    glo, ghi = fx.bbox_world([glass])
    outer = min(dims[u_i], dims[v_i]) / 2
    inner = min(ghi[u_i] - glo[u_i], ghi[v_i] - glo[v_i]) / 2
    ring = (outer + inner) / 2  # middle of the frame band, between glass edge and frame edge
    face = center + normal * (dims[axis] / 2)
    table = scene.objects.get("D_Table_Top")
    table_top = fx.bbox_world([table])[1].z if table else -1e9

    for o in old:
        bpy.data.objects.remove(o, do_unlink=True)

    radius = MIRROR_BULB_DIAMETER / 2
    bulb_me = smooth_mesh("PB_MirrorBulb", lambda bm: bmesh.ops.create_uvsphere(
        bm, u_segments=32, v_segments=16, radius=radius))
    bulb_me.materials.append(mat_frosted_bulb())

    def socket(bm):
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=24,
                              radius1=SOCKET_RADIUS, radius2=SOCKET_RADIUS, depth=SOCKET_LENGTH)
        bmesh.ops.translate(bm, verts=bm.verts, vec=(0.0, 0.0, SOCKET_LENGTH / 2))
    socket_me = smooth_mesh("PB_MirrorSocket", socket)
    socket_me.materials.append(fx.mat_brass())

    rot = normal.to_track_quat("Z", "Y").to_matrix().to_4x4()
    placed = skipped = 0
    for i in range(count):
        t = math.pi / 2 + 2 * math.pi * i / count  # start at the top, go round evenly
        base = face + (u * math.cos(t) + v * math.sin(t)) * ring
        bulb_center = base + normal * (SOCKET_LENGTH + radius * 0.85)
        if bulb_center.z - radius < table_top + 0.01:
            skipped += 1  # would sit inside the vanity top
            continue
        sock = bpy.data.objects.new(f"D_BulbSocket{i:02d}", socket_me)
        sock.matrix_world = Matrix.Translation(base) @ rot
        bulb = bpy.data.objects.new(f"D_Bulb{i:02d}", bulb_me)
        bulb.matrix_world = Matrix.Translation(bulb_center)
        for o in (sock, bulb):
            coll.objects.link(o)
            if parent:
                o.parent = parent
                o.matrix_parent_inverse = parent.matrix_world.inverted()
        placed += 1
    fx.log(f"mirror bulbs: {placed} globe bulbs on brass sockets, ring r={ring:.3f} m on the frame "
           f"(frame r={outer:.3f}, glass r={inner:.3f}), {skipped} skipped at the vanity top")


def apply_extras(scene, pal):
    """Optional palette keys for concepts that change more than colours."""
    if "skirting" in pal:
        recolor("Paint_Skirting", pal["skirting"])
    if "booth_shell" in pal:
        mat, bsdf = fx.new_material("PB_Booth_Paint")
        bsdf.inputs["Base Color"].default_value = fx.hex_rgba(pal["booth_shell"])
        bsdf.inputs["Roughness"].default_value = 0.8
        shell = [scene.objects[n] for n in ("Booth_Shell_MDF", "Booth_Roof") if n in scene.objects]
        fx.assign(shell, mat, "booth shell")
    if pal.get("floor_oak") and "Room_Floor" in scene.objects:
        fx.assign([scene.objects["Room_Floor"]], mat_oak(), "floor")
    if pal.get("floor_checker") and "Room_Floor" in scene.objects:
        fx.assign([scene.objects["Room_Floor"]], fx.mat_checker(pal.get("checker_tile", 0.4)), "floor")
    brass = [scene.objects[n] for n in pal.get("brass_objects", []) if n in scene.objects]
    if brass:
        fx.assign(brass, fx.mat_brass(), "brass")
    prefixes = tuple(pal.get("hide_prefixes", []))
    if prefixes:
        hidden = [o.name for o in scene.objects if o.name.startswith(prefixes)]
        for name in hidden:
            scene.objects[name].hide_render = True
        fx.log(f"hidden: {hidden}")
    if pal.get("review_fixes"):
        apply_review_fixes(scene, pal)
    if pal.get("sofa_model") == "kidney":
        build_kidney_sofa(scene)
    if pal.get("minimal_decor"):
        add_minimal_decor(scene, pal.get("light_color", WARM_LIGHT))


def scale_mesh_verts(obj, fn):
    """Apply fn(world_co) -> world_co to every vertex of a mesh whose geometry is baked in world space."""
    mw, inv = obj.matrix_world, obj.matrix_world.inverted()
    for v in obj.data.vertices:
        v.co = inv @ fn(mw @ v.co)
    obj.data.update()


def raise_pendant(scene, prefix):
    globes = [o for o in scene.objects if o.name.startswith(prefix + "_Globe")]
    if not globes:
        return
    bottom = fx.bbox_world(globes)[0].z
    lift = PENDANT_MIN_CLEARANCE - bottom
    if lift <= 0:
        return
    for g in globes:
        scale_mesh_verts(g, lambda co: co + Vector((0.0, 0.0, lift)))
    for wire in (o for o in scene.objects if o.name.startswith(prefix + "_Wire")):
        lo, hi = fx.bbox_world([wire])
        top, length = hi.z, hi.z - lo.z
        k = max(length - lift, 0.05) / length  # shorten from the bottom, keep the ceiling end
        scale_mesh_verts(wire, lambda co: Vector((co.x, co.y, top - (top - co.z) * k)))
    light = scene.objects.get(prefix + "_Light")
    if light:
        light.location.z += lift
    fx.log(f"{prefix}: raised {lift:.2f} m, globes now clear the floor by {PENDANT_MIN_CLEARANCE} m")


def box(name, lo, hi, mat, coll):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    size = Vector(hi) - Vector(lo)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    bmesh.ops.translate(bm, vec=(Vector(lo) + Vector(hi)) / 2, verts=bm.verts)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def flat_material(name, hex_color, roughness=0.6):
    mat, bsdf = fx.new_material(name)
    bsdf.inputs["Base Color"].default_value = fx.hex_rgba(hex_color)
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def add_entrance_wall(scene, pal):
    """A slim waiting bench and a QR pay point on the empty entrance wall (customer-strip gallery on request)."""
    coll = bpy.data.collections.get("PB_Entrance") or bpy.data.collections.new("PB_Entrance")
    if coll.name not in scene.collection.children:
        scene.collection.children.link(coll)
    wall = scene.objects.get("Room_Wall_Entrance")
    face_y = fx.bbox_world([wall])[1].y if wall else -3.0  # inner face of the entrance wall
    brass = fx.mat_brass()
    cream = bpy.data.materials.get("Sofa_Boucle") or flat_material("PB_Cream", "#EDE4D8")
    black = flat_material("PB_Black_Satin", "#1C1A19", 0.45)
    paper = flat_material("PB_Strip_Paper", "#F4EEE6", 0.4)
    tones = [flat_material(f"PB_Strip_Photo{i}", c, 0.35)
             for i, c in enumerate(("#8A6F63", "#3B3230", "#B89A86", "#6E5A55"))]

    # Everything is centred on the brand name above it.
    brand = scene.objects.get("A_Brand_Text")
    if brand:
        blo, bhi = fx.bbox_world([brand])
        cx = (blo.x + bhi.x) / 2
    else:
        cx = 2.1
    # Bench: 2.0 m long, 0.35 m deep, seat at 0.47 m; walkway to the booth keeps > 1.6 m.
    x0, x1, d = cx - 1.0, cx + 1.0, 0.35
    if pal.get("bench", True):
        base = flat_material("PB_Bench_Paint", pal["bench_base"], 0.5) if "bench_base" in pal else black
        box("PB_Bench_Base", (x0, face_y, 0.0), (x1, face_y + d, 0.38), base, coll)
        box("PB_Bench_Cushion", (x0 + 0.02, face_y + 0.01, 0.38), (x1 - 0.02, face_y + d, 0.47), cream, coll)

    count = 0
    if pal.get("strip_gallery"):
        # Gallery: one row of 2x6-inch strips in thin brass frames, below the brand name.
        # Above the heads of seated guests (~1.2 m) and below the brand name (~1.7 m).
        fw, fh, gap, z0 = 0.09, 0.22, 0.07, 1.32
        count = 13
        start = cx - (count * (fw + gap) - gap) / 2
        for i in range(count):
            x = start + i * (fw + gap)
            box(f"PB_Gallery_Frame{i:02d}", (x, face_y, z0), (x + fw, face_y + 0.015, z0 + fh), brass, coll)
            box(f"PB_Gallery_Paper{i:02d}", (x + 0.008, face_y + 0.015, z0 + 0.008),
                (x + fw - 0.008, face_y + 0.018, z0 + fh - 0.008), paper, coll)
            cell = (fh - 0.03) / 4
            for j in range(4):
                cz = z0 + fh - 0.012 - (j + 1) * cell
                box(f"PB_Gallery_Photo{i:02d}_{j}", (x + 0.014, face_y + 0.018, cz + 0.004),
                    (x + fw - 0.014, face_y + 0.02, cz + cell - 0.002), tones[(i + j) % len(tones)], coll)

    if pal.get("pay_point", True):
        # QR pay point next to the booth: brass shelf and a black QR board.
        box("PB_Pay_Shelf", (4.15, face_y, 1.0), (4.6, face_y + 0.22, 1.03), brass, coll)
        box("PB_Pay_Board", (4.25, face_y + 0.02, 1.03), (4.5, face_y + 0.05, 1.33), black, coll)
        box("PB_Pay_QR", (4.3, face_y + 0.05, 1.12), (4.45, face_y + 0.052, 1.27), paper, coll)
    fx.log(f"entrance wall: bench={pal.get('bench', True)}, pay point={pal.get('pay_point', True)}, "
           f"{count} gallery strips")

    cam_data = bpy.data.cameras.new("Cam_09_tuong_loi_vao")
    cam_data.lens = 16
    cam = bpy.data.objects.new("Cam_09_tuong_loi_vao", cam_data)
    cam.location = (cx, -0.6, 1.5)  # centred on the bench and brand name
    cam.rotation_euler = (math.radians(88), 0.0, math.radians(180))
    coll.objects.link(cam)


def mat_oak():
    """Light oak vinyl plank: 1.2 m x 0.19 m boards in a staggered pattern with a soft grain."""
    mat, bsdf = fx.new_material("PB_Oak_Plank")
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    geo = nodes.new("ShaderNodeNewGeometry")
    brick = nodes.new("ShaderNodeTexBrick")
    brick.offset, brick.offset_frequency = 0.37, 1
    brick.inputs["Color1"].default_value = fx.hex_rgba("#D9C6AB")
    brick.inputs["Color2"].default_value = fx.hex_rgba("#CDB797")
    brick.inputs["Mortar"].default_value = fx.hex_rgba("#B39B7E")
    brick.inputs["Scale"].default_value = 1.0
    brick.inputs["Mortar Size"].default_value = 0.0025
    brick.inputs["Brick Width"].default_value = 1.2
    brick.inputs["Row Height"].default_value = 0.19
    links.new(geo.outputs["Position"], brick.inputs["Vector"])
    grain = nodes.new("ShaderNodeTexWave")
    grain.wave_type, grain.bands_direction = "BANDS", "Y"
    grain.inputs["Scale"].default_value = 18.0
    grain.inputs["Distortion"].default_value = 6.0
    grain.inputs["Detail"].default_value = 3.0
    links.new(geo.outputs["Position"], grain.inputs["Vector"])
    mix = nodes.new("ShaderNodeMix")
    mix.data_type, mix.blend_type = "RGBA", "MULTIPLY"
    mix.inputs[0].default_value = 0.12
    links.new(brick.outputs["Color"], mix.inputs[6])
    links.new(grain.outputs["Color"], mix.inputs[7])
    links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.42
    add_bump = fx.add_bump
    add_bump(mat, bsdf, brick, 0.15, 0.002)
    return mat


def mat_plaster(name, hex_color, bump=0.25, scale=6.0):
    mat, bsdf = fx.new_material(name)
    bsdf.inputs["Base Color"].default_value = fx.hex_rgba(hex_color)
    bsdf.inputs["Roughness"].default_value = 0.9
    noise = mat.node_tree.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = 6.0
    fx.add_bump(mat, bsdf, noise, bump, 0.004)
    return mat


def cylinder(name, center, r0, r1, z0, z1, mat, coll, caps=True, segments=48):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=segments,
                          radius1=r0, radius2=r1, depth=z1 - z0)
    bmesh.ops.translate(bm, vec=(center[0], center[1], (z0 + z1) / 2), verts=bm.verts)
    bm.to_mesh(me)
    bm.free()
    for poly in me.polygons:
        poly.use_smooth = True
    me.materials.append(mat)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def add_olive_tree(center, coll):
    """Artificial olive tree in a ribbed stone-look pot (~1.8 m)."""
    import random
    rnd = random.Random(7)
    pot = mat_plaster("PB_Pot_Stone", "#D8CDBE", 0.35, 18.0)
    bark = flat_material("PB_Olive_Bark", "#4E4136", 0.8)
    leaf, bsdf = fx.new_material("PB_Olive_Leaf")
    bsdf.inputs["Base Color"].default_value = fx.hex_rgba("#65714F")
    bsdf.inputs["Roughness"].default_value = 0.6
    fx.set_input(bsdf, ["Subsurface Weight", "Subsurface"], 0.15)
    x, y = center
    cylinder("PB_Olive_Pot", (x, y), 0.17, 0.21, 0.0, 0.48, pot, coll)
    cylinder("PB_Olive_Soil", (x, y), 0.19, 0.19, 0.44, 0.46, bark, coll)
    tips = []
    for i, (dx, dy, top) in enumerate(((0.0, 0.0, 1.35), (0.14, 0.05, 1.6), (-0.12, -0.04, 1.55))):
        base = Vector((x + dx * 0.2, y + dy * 0.2, 0.45))
        tip = Vector((x + dx, y + dy, top))
        me = bpy.data.meshes.new(f"PB_Olive_Trunk{i}")
        bm = bmesh.new()
        length = (tip - base).length
        bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.028 - i * 0.006, radius2=0.012,
                              depth=length)
        bm.to_mesh(me)
        bm.free()
        me.materials.append(bark)
        trunk = bpy.data.objects.new(f"PB_Olive_Trunk{i}", me)
        trunk.location = (base + tip) / 2
        trunk.rotation_euler = (tip - base).to_track_quat("Z", "Y").to_euler()
        coll.objects.link(trunk)
        tips.append(tip)
    me = bpy.data.meshes.new("PB_Olive_Leaves")
    bm = bmesh.new()
    for tip in tips:
        for _ in range(320):
            c = tip + Vector((rnd.gauss(0, 0.12), rnd.gauss(0, 0.12), rnd.gauss(0.04, 0.1)))
            ret = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=rnd.uniform(0.022, 0.034))
            vs = ret["verts"]
            bmesh.ops.scale(bm, vec=(1.0, 0.35, 0.18), verts=vs)  # long, narrow olive leaves
            rot = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))).to_track_quat("X", "Z")
            bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=rot.to_matrix(), verts=vs)
            bmesh.ops.translate(bm, vec=c, verts=vs)
    bm.to_mesh(me)
    bm.free()
    for poly in me.polygons:
        poly.use_smooth = True
    me.materials.append(leaf)
    coll.objects.link(bpy.data.objects.new("PB_Olive_Leaves", me))


def add_minimal_decor(scene, light_color):
    """Soft-minimal styling: rug, plaster table, tiered fabric pendant, cove light, olive tree, plaster art."""
    coll = bpy.data.collections.get("PB_Minimal") or bpy.data.collections.new("PB_Minimal")
    if coll.name not in scene.collection.children:
        scene.collection.children.link(coll)
    sofa = [scene.objects[n] for n in ("PB_Kidney_Seat", "PB_Kidney_Back") if n in scene.objects]
    slo, shi = fx.bbox_world(sofa) if sofa else (Vector((0.1, -0.8, 0)), Vector((1.7, 0.0, 0)))
    sx = (slo.x + shi.x) / 2
    front = slo.y

    # Cream rug under the front of the sofa, clear of the entrance walkway (y > -1.7).
    rug = mat_plaster("PB_Rug_Wool", "#ECE5D9", 0.5, 60.0)
    box("PB_Rug", (sx - 0.85, front - 0.95, 0.0), (sx + 0.85, front + 0.25, 0.012), rug, coll)

    # Round plaster pedestal table in front of the sofa (~40% of the sofa length).
    plaster = mat_plaster("PB_Plaster_Table", "#EDE7DE")
    tc = (sx, front - 0.45)
    cylinder("PB_Table_Base", tc, 0.2, 0.16, 0.012, 0.40, plaster, coll)
    cylinder("PB_Table_Top", tc, 0.33, 0.33, 0.40, 0.44, plaster, coll)

    # Tiered fabric pendant over the table: the room's one decorative light.
    fabric, bsdf = fx.new_material("PB_Fabric_Shade")
    bsdf.inputs["Base Color"].default_value = fx.hex_rgba("#F4EFE7")
    bsdf.inputs["Roughness"].default_value = 0.9
    fx.set_input(bsdf, ["Emission Color", "Emission"], (1.0, 0.8, 0.6, 1.0))
    fx.set_input(bsdf, ["Emission Strength"], 0.3)
    for i, (r, z0, z1) in enumerate(((0.32, 2.02, 2.15), (0.25, 2.12, 2.24), (0.18, 2.21, 2.31))):
        cylinder(f"PB_Pendant_Tier{i}", tc, r, r, z0, z1, fabric, coll, caps=False)
    cord = flat_material("PB_Cord", "#2A2522", 0.5)
    cylinder("PB_Pendant_Cord", tc, 0.004, 0.004, 2.31, 3.0, cord, coll, segments=8)
    cylinder("PB_Pendant_Canopy", tc, 0.06, 0.06, 2.97, 3.0, plaster, coll)
    fx.add_light("PB_Pendant_Glow", "POINT", (tc[0], tc[1], 2.16), 45, color=light_color, shadow_soft_size=0.15)

    # Cove light round the ceiling perimeter, as in a lit tray ceiling.
    walls = [scene.objects[n] for n in fx.ROLES["walls"] if n in scene.objects]
    ceiling = scene.objects.get("Room_Ceiling")
    if walls and ceiling:
        wlo, whi = fx.bbox_world(walls)
        fx.add_cove_lights(fx.bbox_world([ceiling])[0].z, wlo, whi)
        for o in scene.objects:
            if o.name.startswith("PB_Cove_"):
                o.data.color = light_color
                o.data.energy *= 0.35

    # Olive tree beside the sofa against the left wall, as in the inspiration. The entrance wall is
    # where most cameras stand, and the doorway starts at y = -1.73.
    add_olive_tree((0.25, -1.35), coll)

    # Wall art above the sofa becomes cream plaster relief in light oak frames.
    oak = flat_material("PB_Oak_Frame", "#C9B08E", 0.5)
    relief, rb = fx.new_material("PB_Plaster_Relief")
    rb.inputs["Base Color"].default_value = fx.hex_rgba("#EFEAE2")
    rb.inputs["Roughness"].default_value = 0.9
    loops = relief.node_tree.nodes.new("ShaderNodeTexWave")  # looping raised lines, as in the inspiration
    loops.wave_type, loops.wave_profile = "RINGS", "SIN"
    loops.inputs["Scale"].default_value = 6.0
    loops.inputs["Distortion"].default_value = 9.0
    loops.inputs["Detail"].default_value = 1.0
    fx.add_bump(relief, rb, loops, 1.0, 0.01)
    for i in (1, 2, 3):
        border, photo = scene.objects.get(f"A_Frame{i}_Border"), scene.objects.get(f"A_Frame{i}_Photo")
        if border:
            fx.assign([border], oak, f"frame {i}")
        if photo:
            fx.assign([photo], relief, f"art {i}")
    fx.log("minimal decor: rug, plaster table, tiered pendant, cove light, olive tree, plaster art")


# Kidney bouclé sofa (client reference photo): bean-shaped seat, a curved back that wraps the seat and
# steps down towards the right end, a rolled bolster arm on the left. No loose cushions.
KIDNEY = {
    "arc_radius": 1.0,      # seat centreline radius; the centre of curvature sits in front of the sofa
    "half_angle": 30.0,     # degrees either side of the middle -> ~1.64 m wide with the round ends
    "seat": (0.64, 0.40),   # seat depth x height (m)
    "back": (0.26, 0.60),   # backrest thickness; its bottom is buried in the seat
    "back_top": 0.76,       # backrest top above the floor
    "arm_radius": 0.16,     # rolled arm bolster
}


def stadium_outline(center, half_w, cap_segments=12):
    """Closed 2D outline of a band of half-width half_w around a centreline, with round ends."""
    def normal(i):
        p0 = center[max(i - 1, 0)]
        p1 = center[min(i + 1, len(center) - 1)]
        tx, ty = p1[0] - p0[0], p1[1] - p0[1]
        ln = math.hypot(tx, ty)
        return -ty / ln, tx / ln

    left, right = [], []
    for i, (x, y) in enumerate(center):
        nx, ny = normal(i)
        left.append((x + nx * half_w, y + ny * half_w))
        right.append((x - nx * half_w, y - ny * half_w))

    def cap(i, start_angle):
        x, y = center[i]
        return [(x + half_w * math.cos(start_angle - math.pi * j / cap_segments),
                 y + half_w * math.sin(start_angle - math.pi * j / cap_segments))
                for j in range(1, cap_segments)]

    nx, ny = normal(len(center) - 1)
    end_cap = cap(len(center) - 1, math.atan2(ny, nx))
    nx, ny = normal(0)
    start_cap = cap(0, math.atan2(-ny, -nx))
    return left + end_cap + right[::-1] + start_cap


def soft_block(name, outline, z0, z1, bevel, coll, top_fn=None):
    """Extrude an outline into an upholstered block: rounded top and bottom edges, optional top shaping."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    verts = [bm.verts.new((x, y, z0)) for x, y in outline]
    face = bm.faces.new(verts)
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    top = [e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0.0, 0.0, z1 - z0), verts=top)
    bm.normal_update()
    caps = [f for f in bm.faces if len(f.verts) > 4]
    edges = list({e for f in caps for e in f.edges})
    bmesh.ops.bevel(bm, geom=edges, offset=bevel, segments=8, profile=0.5, affect="EDGES", clamp_overlap=True)
    if top_fn:
        for v in bm.verts:
            v.co.z = top_fn(v.co)
    ngons = [f for f in bm.faces if len(f.verts) > 4]
    bmesh.ops.triangulate(bm, faces=ngons, quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.to_mesh(me)
    bm.free()
    for poly in me.polygons:
        poly.use_smooth = True
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def build_kidney_sofa(scene):
    old = scene.objects.get("A_Sofa_Cloud")
    if old is None:
        fx.log("kidney sofa: A_Sofa_Cloud not found, skipped")
        return
    lo, hi = fx.bbox_world([old])
    mat = old.material_slots[0].material if old.material_slots else flat_material("PB_Boucle", "#EDE4D8")
    for o in [old] + list(old.children_recursive):
        o.hide_render = o.hide_viewport = True
    coll = bpy.data.collections.get("PB_Sofa_Kidney") or bpy.data.collections.new("PB_Sofa_Kidney")
    if coll.name not in scene.collection.children:
        scene.collection.children.link(coll)

    k = KIDNEY
    seat_d, seat_h = k["seat"]
    back_t, back_h = k["back"]
    r_seat = k["arc_radius"]
    r_back = r_seat + seat_d / 2 - back_t / 2 + 0.02
    cx = (lo.x + hi.x) / 2
    cy = hi.y - 0.02 - (r_back + back_t / 2)  # centre of curvature, in front of the sofa
    ha = math.radians(k["half_angle"])

    def arc(r, a0, a1, n=40):
        return [(cx + r * math.sin(a0 + (a1 - a0) * i / (n - 1)), cy + r * math.cos(a0 + (a1 - a0) * i / (n - 1)))
                for i in range(n)]

    seat = soft_block("PB_Kidney_Seat", stadium_outline(arc(r_seat, -ha, ha), seat_d / 2),
                      0.0, seat_h, 0.14, coll)

    # Back wraps the seat from the left arm and steps down over the right third.
    b0, b1 = -ha, ha * 0.92
    top = k["back_top"]

    def back_top(co):
        if co.z <= seat_h:
            return co.z
        a = math.atan2(co.x - cx, co.y - cy)
        t = min(max((a - b0) / (b1 - b0), 0.0), 1.0)
        taper = 1.0 if t < 0.55 else 1.0 - 0.6 * ((t - 0.55) / 0.45) ** 1.6
        return seat_h + (co.z - seat_h) * taper

    back = soft_block("PB_Kidney_Back", stadium_outline(arc(r_back, b0, b1), back_t / 2),
                      seat_h - 0.2, top, back_t / 2 - 0.01, coll, back_top)

    # Rolled arm: a bolster from the back to the front of the seat at the left end.
    ar = k["arm_radius"]
    a_arm = -ha
    ux, uy = math.sin(a_arm), math.cos(a_arm)
    r0, r1 = r_back, r_seat - seat_d / 2 + ar
    arm_line = [(cx + ux * (r0 + (r1 - r0) * i / 7), cy + uy * (r0 + (r1 - r0) * i / 7)) for i in range(8)]
    arm = soft_block("PB_Kidney_Arm", stadium_outline(arm_line, ar), seat_h - 0.2, top - 0.08, ar - 0.01, coll)

    for o in (seat, back, arm):
        o.data.materials.append(mat)
    slo, shi = fx.bbox_world([seat, back, arm])
    fx.log(f"kidney sofa: {shi.x - slo.x:.2f} m wide, {shi.y - slo.y:.2f} m deep, back {top} m, "
           f"seat {seat_h} m; replaces A_Sofa_Cloud")


def apply_review_fixes(scene, pal):
    # 1. Pendant cluster 1 hung at 1.77 m over the new walkway once the counter was removed.
    raise_pendant(scene, "Room_Pendant1")

    # 2. One metal: aluminium and stainless frames go brass; white trims and canopies take the ceiling paint.
    for name in ("Aluminium", "Inox"):
        recolor(name, "#B08D57", metal=True)
    ceiling = bpy.data.materials.get("Ceiling")
    trims = [o for o in scene.objects
             if o.name.startswith(("Room_Downlight", "Room_Pendant")) and o.name.endswith(("_Trim", "_Canopy"))]
    if ceiling and trims:
        fx.assign(trims, ceiling, "downlight trims and pendant canopies")

    # 3. Every lobby light at 2700K.
    warm = [o for o in scene.objects if o.type == "LIGHT" and o.name not in WARM_LIGHT_SKIP]
    for o in warm:
        o.data.color = pal.get("light_color", WARM_LIGHT)
    fx.log(f"{len(warm)} lights set to ~2700K")

    # 4. The booth facade gets its own light, and a larger pink neon heart.
    booth = scene.objects.get("Booth_Shell_MDF")
    curtain = scene.objects.get("Booth_Door_Curtain")
    if booth and curtain:
        face_x = fx.bbox_world([booth])[0].x
        clo, chi = fx.bbox_world([curtain])
        cy = (clo.y + chi.y) / 2
        for i, (dy, tz) in enumerate(((-0.35, 1.2), (0.35, 1.6))):
            fx.add_light(f"PB_Booth_Wash{i}", "SPOT", (face_x - 1.3, cy + dy, 2.95), 60,
                         color=pal.get("light_color", WARM_LIGHT), aim=(face_x, cy + dy * 0.3, tz),
                         spot_size=math.radians(38), spot_blend=0.5, shadow_soft_size=0.03)
    heart = scene.objects.get("Booth_Heart")
    if heart and pal.get("neon_heart", True):
        lo, hi = fx.bbox_world([heart])
        c = (lo + hi) / 2
        scale_mesh_verts(heart, lambda co: Vector((co.x - 0.004, c.y + (co.y - c.y) * HEART_SCALE,
                                                   c.z + (co.z - c.z) * HEART_SCALE)))
        neon = fx.mat_neon()
        fx.set_input(principled(neon), ["Emission Color", "Emission"], (1.0, 0.22, 0.42, 1.0))
        fx.set_input(principled(neon), ["Emission Strength"], 1.6)
        fx.assign([heart], neon, "heart (neon)")

    # 5. Use the empty entrance wall.
    add_entrance_wall(scene, pal)


def visible_blind(scene):
    return next((o for o in scene.objects
                 if o.name.startswith("F_Rem_") and o.name.endswith("_Spread") and not o.hide_render), None)


def main():
    args = parse_args()
    if not os.path.exists(args.blend):
        raise SystemExit(f"Blend file not found: {args.blend}")
    bpy.ops.wm.open_mainfile(filepath=args.blend)
    os.makedirs(args.out, exist_ok=True)
    scene = bpy.context.scene
    pal = PALETTES[args.palette]
    fx.log(f"palette {args.palette}")

    fx.fix_render(scene, pal.get("exposure", EXPOSURE))
    fix_visibility(scene)
    ensure_visible(scene, "Room_Ceiling")
    boost_booth_flash(scene)
    tone_down_globes()
    boost_downlights(scene, pal.get("downlight_boost", DOWNLIGHT_BOOST))

    for role, names in MATERIALS.items():
        for name in names:
            recolor(name, pal[role], metal=(role == "accent" and pal["accent_metal"]))
    if CORNICE in scene.objects:
        fx.assign([scene.objects[CORNICE]], bpy.data.materials["Ceiling"], "cornice")
    for (rem, bar, _), color in zip(BLINDS, pal["blinds"]):
        recolor(rem, color)
        recolor(bar, darker(color, 0.7))
    apply_extras(scene, pal)
    walls = [scene.objects[n] for n in fx.ROLES["walls"] if n in scene.objects]
    mount_mirror_bulbs(scene, sum(fx.bbox_world(walls), Vector()) / 2 if walls else Vector())

    base, ext = os.path.splitext(args.blend)
    target = f"{base}_{args.palette}{ext}"
    bpy.ops.wm.save_as_mainfile(filepath=target, copy=True)
    fx.log(f"saved {target}")

    if not args.no_render:
        scene.render.resolution_percentage = 100 if FULL_RES else 50
        scene.render.image_settings.file_format = "JPEG"
        scene.render.image_settings.quality = 95 if FULL_RES else 88
        if FULL_RES and hasattr(scene, "eevee"):
            scene.eevee.taa_render_samples = 128
        blind = visible_blind(scene)
        blind_for_cam = {cam: rem for rem, _, cam in BLINDS}
        cams = sorted(o.name for o in scene.objects if o.type == "CAMERA" and o.name not in PLAN_CAMERAS)
        for name in cams:
            if blind and name in blind_for_cam:
                # Show the matching backdrop colour on the blind that is rolled down.
                blind.material_slots[0].link = "OBJECT"
                blind.material_slots[0].material = bpy.data.materials[blind_for_cam[name]]
            scene.camera = scene.objects[name]
            scene.render.filepath = os.path.join(args.out, f"{args.palette}_{name}.jpg")
            bpy.ops.render.render(write_still=True)
            fx.log(f"rendered {os.path.basename(scene.render.filepath)}")

    with open(os.path.join(args.out, f"{args.palette}_log.json"), "w", encoding="utf-8") as f:
        json.dump(fx.LOG, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
