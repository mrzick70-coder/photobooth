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
        "brass_objects": ["D_Mirror_Frame"], "hide_prefixes": ["C_"],
    },
}
DEFAULT_PALETTE = "cherry"

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


def boost_downlights(scene):
    for o in scene.objects:
        if o.type == "LIGHT" and o.name.startswith("Room_Downlight"):
            o.data.energy *= DOWNLIGHT_BOOST
    fx.log(f"downlights x{DOWNLIGHT_BOOST}")


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
    if pal.get("floor_checker") and "Room_Floor" in scene.objects:
        fx.assign([scene.objects["Room_Floor"]], fx.mat_checker(), "floor")
    brass = [scene.objects[n] for n in pal.get("brass_objects", []) if n in scene.objects]
    if brass:
        fx.assign(brass, fx.mat_brass(), "brass")
    prefixes = tuple(pal.get("hide_prefixes", []))
    if prefixes:
        hidden = [o.name for o in scene.objects if o.name.startswith(prefixes)]
        for name in hidden:
            scene.objects[name].hide_render = True
        fx.log(f"hidden: {hidden}")


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

    fx.fix_render(scene, EXPOSURE)
    fix_visibility(scene)
    ensure_visible(scene, "Room_Ceiling")
    boost_booth_flash(scene)
    tone_down_globes()
    boost_downlights(scene)

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
