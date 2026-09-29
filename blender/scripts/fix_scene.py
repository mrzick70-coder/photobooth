"""Apply the design review to the photobooth studio scene and save a copy.

The original file is never overwritten: the result is saved next to it as <name>_v2.blend
and previews from every camera are rendered to --out.

Fill ROLES with object names from blender/output/inspect_scene/scene_report.json.
Roles left empty are auto-detected by name keywords; roles that still match nothing are skipped.

Run: blender -b -P blender/scripts/fix_scene.py -- --blend <file.blend> --out <dir>
"""
import argparse
import json
import math
import os
import sys

import bpy
from mathutils import Vector

# Object names per role. Empty list = auto-detect by keywords (object or material name).
ROLES = {
    "floor": [],
    "walls": [],
    "ceiling": [],
    "cornice": [],        # crown molding, painted to match the ceiling
    "curtain": [],        # booth curtain -> burgundy velvet
    "booth": [],          # booth body
    "booth_trim": [],     # booth frame edges and photo slot -> brushed brass
    "heart": [],          # heart sign above the booth -> warm pink neon
    "counter_top": [],
    "counter_front": [],  # reception counter front -> fluted panels
    "vanity_top": [],
    "mirror_frame": [],
    "picture_frames": [],
    "remove": [],         # objects to hide from render (e.g. green cactus)
    "pendants": [],       # glowing globe pendants; empty = detect emissive spheres
}

KEYWORDS = {
    "floor": ["floor", "san"],
    "walls": ["wall", "tuong"],
    "ceiling": ["ceiling", "tran"],
    "cornice": ["cornice", "molding", "moulding", "phao"],
    "curtain": ["curtain", "rem", "drape"],
    "booth": ["booth"],
    "booth_trim": ["trim", "slot", "khe"],
    "heart": ["heart", "tim"],
    "counter_top": ["counter_top", "countertop", "desk_top", "quay_mat"],
    "counter_front": ["counter_front", "quay_than"],
    "vanity_top": ["vanity", "dresser"],
    "mirror_frame": ["mirror_frame", "mirror frame", "guong_vien"],
    "picture_frames": ["picture_frame", "frame", "khung"],
    "remove": ["cactus", "xuong_rong"],
}

PENDANTS_KEEP = 3

# Palette from the review (60-30-10).
CHARCOAL = "#2B2724"
CREAM = "#EDE4D8"
TRAVERTINE = "#E2D6C3"
BRASS = "#B08D57"
BURGUNDY = "#5E1A24"
BLACK_TILE = "#1C1A19"
WARM_2700K = (1.0, 0.64, 0.33)
NEON_PINK = (1.0, 0.35, 0.45)

LOG = []


def log(msg):
    print("[fix]", msg)
    LOG.append(msg)


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--no-render", action="store_true")
    return parser.parse_args(argv)


def hex_rgba(h):
    h = h.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
    return (*lin, 1.0)


# ---------------------------------------------------------------- lookup

def resolve_roles(scene):
    meshes = [o for o in scene.objects if o.type == "MESH"]
    found = {}
    for role, names in ROLES.items():
        if names:
            objs = [scene.objects[n] for n in names if n in scene.objects]
            missing = [n for n in names if n not in scene.objects]
            if missing:
                log(f"{role}: not found {missing}")
        elif role in KEYWORDS:
            keys = KEYWORDS[role]
            objs = [o for o in meshes if any(k in o.name.lower() for k in keys)
                    or any(s.material and any(k in s.material.name.lower() for k in keys)
                           for s in o.material_slots)]
        else:
            objs = []
        found[role] = objs
    if not found["pendants"]:
        found["pendants"] = detect_pendants(meshes)
    for role, objs in found.items():
        log(f"{role}: {[o.name for o in objs] or 'skipped'}")
    return found


def emission_strength(mat):
    if not mat or not mat.use_nodes:
        return 0.0
    best = 0.0
    for n in mat.node_tree.nodes:
        if n.bl_idname == "ShaderNodeEmission":
            best = max(best, n.inputs["Strength"].default_value)
        elif n.bl_idname == "ShaderNodeBsdfPrincipled":
            s = n.inputs.get("Emission Strength")
            c = n.inputs.get("Emission Color") or n.inputs.get("Emission")
            if s and c and max(c.default_value[:3]) > 0:
                best = max(best, s.default_value)
    return best


def detect_pendants(meshes):
    out = []
    for o in meshes:
        d = o.dimensions
        if min(d) <= 0.05 or max(d) > 1.0 or max(d) / min(d) > 1.3:
            continue
        if any(emission_strength(s.material) > 0 for s in o.material_slots):
            out.append(o)
    return out


# ---------------------------------------------------------------- materials

def new_material(name):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (400, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    mat.node_tree.links.new(bsdf.outputs[0], out.inputs["Surface"])
    return mat, bsdf


def set_input(node, names, value):
    for name in names if isinstance(names, (list, tuple)) else [names]:
        sock = node.inputs.get(name)
        if sock is not None:
            sock.default_value = value
            return True
    return False


def add_bump(mat, bsdf, tex, strength, distance=0.01):
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = distance
    links.new(tex.outputs[0], bump.inputs["Height"])
    links.new(bump.outputs[0], bsdf.inputs["Normal"])


def mat_warm_charcoal():
    mat, bsdf = new_material("PB_WarmCharcoal_Limewash")
    bsdf.inputs["Base Color"].default_value = hex_rgba(CHARCOAL)
    bsdf.inputs["Roughness"].default_value = 0.85
    noise = mat.node_tree.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.0
    noise.inputs["Detail"].default_value = 8.0
    add_bump(mat, bsdf, noise, 0.08)
    return mat


def mat_travertine():
    mat, bsdf = new_material("PB_Travertine_Matte")
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    wave = nodes.new("ShaderNodeTexWave")
    wave.inputs["Scale"].default_value = 1.5
    wave.inputs["Distortion"].default_value = 6.0
    wave.inputs["Detail"].default_value = 4.0
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = hex_rgba("#D3C4AC")
    ramp.color_ramp.elements[1].color = hex_rgba(TRAVERTINE)
    links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.5
    return mat


def mat_fluted():
    mat, bsdf = new_material("PB_Fluted_Charcoal")
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf.inputs["Base Color"].default_value = hex_rgba("#332E2A")
    bsdf.inputs["Roughness"].default_value = 0.6
    coord = nodes.new("ShaderNodeTexCoord")
    wave = nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.wave_profile = "SIN"
    wave.inputs["Scale"].default_value = 1.0
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (25.0, 25.0, 25.0)  # ~4 cm flutes in object space
    links.new(coord.outputs["Object"], mapping.inputs["Vector"])
    links.new(mapping.outputs[0], wave.inputs["Vector"])
    add_bump(mat, bsdf, wave, 0.6, 0.02)
    return mat


def mat_brass():
    mat, bsdf = new_material("PB_Brass_Brushed")
    bsdf.inputs["Base Color"].default_value = hex_rgba(BRASS)
    bsdf.inputs["Metallic"].default_value = 1.0
    bsdf.inputs["Roughness"].default_value = 0.32
    set_input(bsdf, ["Anisotropic"], 0.6)
    return mat


def mat_velvet():
    mat, bsdf = new_material("PB_Velvet_Burgundy")
    bsdf.inputs["Base Color"].default_value = hex_rgba(BURGUNDY)
    bsdf.inputs["Roughness"].default_value = 0.8
    set_input(bsdf, ["Sheen Weight", "Sheen"], 1.0)
    set_input(bsdf, ["Sheen Roughness"], 0.35)
    set_input(bsdf, ["Sheen Tint"], (1.0, 0.55, 0.6, 1.0))
    return mat


def mat_checker(tile=0.4):
    mat, bsdf = new_material("PB_Checker_BlackCream")
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    geo = nodes.new("ShaderNodeNewGeometry")
    checker = nodes.new("ShaderNodeTexChecker")
    checker.inputs["Color1"].default_value = hex_rgba(CREAM)
    checker.inputs["Color2"].default_value = hex_rgba(BLACK_TILE)
    # Checker cell size is 1/(2*Scale) world units when fed world positions.
    checker.inputs["Scale"].default_value = 1.0 / (2.0 * tile)
    links.new(geo.outputs["Position"], checker.inputs["Vector"])
    links.new(checker.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.35
    return mat


def mat_neon():
    mat, bsdf = new_material("PB_Neon_Pink")
    bsdf.inputs["Base Color"].default_value = (*NEON_PINK, 1.0)
    set_input(bsdf, ["Emission Color", "Emission"], (*NEON_PINK, 1.0))
    set_input(bsdf, ["Emission Strength"], 12.0)
    return mat


def assign(objs, mat, role):
    for o in objs:
        if o.type != "MESH":
            continue
        if not o.material_slots:
            o.data.materials.append(mat)
        for slot in o.material_slots:
            slot.link = "OBJECT"
            slot.material = mat
    if objs:
        log(f"{role}: material -> {mat.name}")


# ---------------------------------------------------------------- pendants

def fix_pendants(pendants, counter):
    if not pendants:
        return
    if counter:
        center = sum((o.matrix_world.translation for o in counter), Vector()) / len(counter)
        pendants.sort(key=lambda o: (o.matrix_world.translation.xy - center.xy).length)
    keep, drop = pendants[:PENDANTS_KEEP], pendants[PENDANTS_KEEP:]
    for o in drop:
        o.hide_render = True
        o.hide_viewport = True
        for child in o.children_recursive:
            child.hide_render = True
            child.hide_viewport = True
    for o in drop:
        for cord in find_cords(o):
            cord.hide_render = True
            cord.hide_viewport = True
    log(f"pendants: kept {[o.name for o in keep]}, hid {[o.name for o in drop]}")

    done = set()
    for o in keep:
        if not any(m.type == "SUBSURF" for m in o.modifiers):
            mod = o.modifiers.new("PB_Smooth", "SUBSURF")
            mod.levels = 2
            mod.render_levels = 3
        for poly in o.data.polygons:
            poly.use_smooth = True
        for slot in o.material_slots:
            mat = slot.material
            if mat and mat.name not in done:
                done.add(mat.name)
                dim_emission(mat, 0.35)


def find_cords(pendant):
    p = pendant.matrix_world.translation
    cords = []
    for o in bpy.context.scene.objects:
        if o.type not in {"MESH", "CURVE"} or o is pendant:
            continue
        d = o.dimensions
        c = o.matrix_world.translation
        if max(d.x, d.y) < 0.05 and d.z > 0.1 and (c.xy - p.xy).length < 0.05 and c.z > p.z:
            cords.append(o)
    return cords


def dim_emission(mat, factor):
    for n in mat.node_tree.nodes:
        if n.bl_idname == "ShaderNodeEmission":
            n.inputs["Strength"].default_value *= factor
            n.inputs["Color"].default_value = (*WARM_2700K, 1.0)
        elif n.bl_idname == "ShaderNodeBsdfPrincipled":
            s = n.inputs.get("Emission Strength")
            if s and s.default_value > 0:
                s.default_value *= factor
                set_input(n, ["Emission Color", "Emission"], (*WARM_2700K, 1.0))
                set_input(n, ["Transmission Weight", "Transmission"], 0.0)
                n.inputs["Base Color"].default_value = hex_rgba("#F4EEE6")
                n.inputs["Roughness"].default_value = 0.6
    log(f"pendant material {mat.name}: emission x{factor}, 2700K")


# ---------------------------------------------------------------- lights

def bbox_world(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def pb_collection():
    coll = bpy.data.collections.get("PB_Lighting")
    if coll is None:
        coll = bpy.data.collections.new("PB_Lighting")
        bpy.context.scene.collection.children.link(coll)
    return coll


def add_light(name, kind, location, energy, color=WARM_2700K, aim=None, rotation=None, **props):
    data = bpy.data.lights.new(name, kind)
    data.energy = energy
    data.color = color
    for k, v in props.items():
        setattr(data, k, v)
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    if aim is not None:
        obj.rotation_euler = (Vector(aim) - Vector(location)).to_track_quat("-Z", "Y").to_euler()
    elif rotation is not None:
        obj.rotation_euler = rotation
    pb_collection().objects.link(obj)
    log(f"light {name}: {kind} {energy:.0f}W at {tuple(round(v, 2) for v in location)}")
    return obj


def add_booth_spot(booth_objs, room_center):
    lo, hi = bbox_world(booth_objs)
    target = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z + (hi.z - lo.z) * 0.55))
    out = room_center.xy - target.xy
    out = out.normalized() if out.length > 1e-3 else Vector((0.0, -1.0))
    loc = Vector((target.x + out.x * 2.2, target.y + out.y * 2.2, hi.z + 0.3))
    add_light("PB_Booth_Spot", "SPOT", loc, 250, aim=target,
              spot_size=math.radians(45), spot_blend=0.6, shadow_soft_size=0.05)


def add_cove_lights(ceiling_z, lo, hi):
    """Hidden LED strips in the crown molding: thin area lights facing up along each wall."""
    inset, z = 0.12, ceiling_z - 0.08
    w, d = hi.x - lo.x, hi.y - lo.y
    specs = [
        ("N", ((lo.x + hi.x) / 2, hi.y - inset, z), w),
        ("S", ((lo.x + hi.x) / 2, lo.y + inset, z), w),
        ("E", (hi.x - inset, (lo.y + hi.y) / 2, z), d),
        ("W", (lo.x + inset, (lo.y + hi.y) / 2, z), d),
    ]
    for side, loc, length in specs:
        light = add_light(f"PB_Cove_{side}", "AREA", loc, 25 * length, rotation=(math.pi, 0, 0))
        light.data.shape = "RECTANGLE"
        light.data.size = length * 0.95 if side in "NS" else 0.03
        light.data.size_y = 0.03 if side in "NS" else length * 0.95


def add_under_led(objs, name, energy_per_m=30):
    for i, o in enumerate(objs):
        lo, hi = bbox_world([o])
        light = add_light(f"{name}_{i}", "AREA", ((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z - 0.02),
                          energy_per_m * max(hi.x - lo.x, hi.y - lo.y))
        light.data.shape = "RECTANGLE"
        light.data.size = max(hi.x - lo.x - 0.05, 0.05)
        light.data.size_y = max(hi.y - lo.y - 0.05, 0.05)


def add_picture_lights(frames, room_center):
    for i, o in enumerate(frames):
        lo, hi = bbox_world([o])
        c = (lo + hi) / 2
        out = room_center.xy - c.xy
        out = out.normalized() if out.length > 1e-3 else Vector((0.0, -1.0))
        loc = Vector((c.x + out.x * 0.25, c.y + out.y * 0.25, hi.z + 0.12))
        add_light(f"PB_Picture_{i}", "SPOT", loc, 15, aim=c,
                  spot_size=math.radians(70), spot_blend=0.8, shadow_soft_size=0.02)


# ---------------------------------------------------------------- render setup

def fix_color_management(scene):
    vs = scene.view_settings
    items = [i.identifier for i in vs.bl_rna.properties["view_transform"].enum_items]
    for vt in ("AgX", "Filmic"):
        if vt in items:
            vs.view_transform = vt
            break
    looks = [i.identifier for i in vs.bl_rna.properties["look"].enum_items]
    for look in ("AgX - Medium High Contrast", "Medium High Contrast", "None"):
        if look in looks:
            vs.look = look
            break
    vs.exposure = 0.0
    log(f"color management: {vs.view_transform} / {vs.look}")


def fix_cameras(scene):
    for cam in (o for o in scene.objects if o.type == "CAMERA"):
        old = cam.location.z
        cam.location.z = 1.5
        rx = cam.rotation_euler.x
        cam.rotation_euler.x = min(max(rx, math.radians(80)), math.radians(92))
        log(f"camera {cam.name}: z {old:.2f}->1.50, tilt {math.degrees(rx):.0f}->"
            f"{math.degrees(cam.rotation_euler.x):.0f} deg")


def render_previews(scene, out_dir):
    scene.render.resolution_percentage = 50
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 85
    if scene.render.engine == "CYCLES":
        scene.cycles.samples = min(scene.cycles.samples, 128)
        scene.cycles.use_denoising = True
    for cam in (o for o in scene.objects if o.type == "CAMERA"):
        scene.camera = cam
        scene.render.filepath = os.path.join(out_dir, f"v2_{bpy.path.clean_name(cam.name)}.jpg")
        bpy.ops.render.render(write_still=True)
        log(f"rendered {scene.render.filepath}")


# ---------------------------------------------------------------- main

def main():
    args = parse_args()
    if not os.path.exists(args.blend):
        raise SystemExit(f"Blend file not found: {args.blend}\n"
                         "Set repo variable BLEND_FILE (Settings > Secrets and variables > Actions > Variables) "
                         "to the full path of your .blend file.")
    bpy.ops.wm.open_mainfile(filepath=args.blend)
    os.makedirs(args.out, exist_ok=True)
    scene = bpy.context.scene
    roles = resolve_roles(scene)

    fix_color_management(scene)
    fix_pendants(roles["pendants"], roles["counter_top"])

    charcoal = mat_warm_charcoal()
    assign(roles["walls"] + roles["ceiling"] + roles["cornice"], charcoal, "walls/ceiling/cornice")
    assign(roles["booth"], charcoal, "booth")
    assign(roles["floor"], mat_checker(), "floor")
    assign(roles["curtain"], mat_velvet(), "curtain")
    brass = mat_brass()
    assign(roles["booth_trim"] + roles["mirror_frame"] + roles["picture_frames"], brass, "brass trims")
    assign(roles["heart"], mat_neon(), "heart")
    travertine = mat_travertine()
    assign(roles["counter_top"] + roles["vanity_top"], travertine, "counter/vanity tops")
    assign(roles["counter_front"], mat_fluted(), "counter front")
    for o in roles["remove"]:
        o.hide_render = True
        o.hide_viewport = True
        log(f"hidden: {o.name}")

    room = roles["walls"] + roles["floor"] + roles["ceiling"]
    if room:
        lo, hi = bbox_world(room)
        center = (lo + hi) / 2
        ceiling_z = bbox_world(roles["ceiling"])[0].z if roles["ceiling"] else hi.z
        add_cove_lights(ceiling_z, lo, hi)
    else:
        center = Vector((0, 0, 0))
        log("room bounds unknown: skipped cove lights")
    if roles["booth"]:
        add_booth_spot(roles["booth"], center)
    add_under_led(roles["counter_top"], "PB_Counter_LED")
    add_picture_lights(roles["picture_frames"], center)

    fix_cameras(scene)

    base, ext = os.path.splitext(args.blend)
    target = base + "_v2" + ext
    bpy.ops.wm.save_as_mainfile(filepath=target, copy=True)
    log(f"saved {target}")

    if not args.no_render:
        render_previews(scene, args.out)
    with open(os.path.join(args.out, "fix_log.json"), "w", encoding="utf-8") as f:
        json.dump(LOG, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
