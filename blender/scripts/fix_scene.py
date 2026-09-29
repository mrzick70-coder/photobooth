"""Apply the design review to Photobooth_Cinema.blend and save copies next to the original.

The original file is never overwritten. Two wall variants are produced so they can be compared:
  <name>_v2_toi.blend   warm charcoal walls and ceiling ("moody Hollywood")
  <name>_v2_sang.blend  original beige walls kept
Shared changes: lights that were hidden from render are switched back on, plan/annotation objects
are hidden, AgX colour management, EEVEE, dimmed 3-globe pendant cluster over the counter,
black/cream checker floor, burgundy velvet booth curtain, lacquered booth with brass trims and
a pink neon heart, travertine tops, fluted counter front, booth spot, cove and picture lights.

Object names come from blender/output/inspect_scene/scene_report.json.

Run: blender -b -P blender/scripts/fix_scene.py -- --blend <file.blend> --out <dir>
"""
import argparse
import json
import math
import os
import sys

import bpy
from mathutils import Vector

ROLES = {
    "floor": ["Room_Floor"],
    "walls": ["Room_Wall_Back", "Room_Wall_Entrance", "Room_Wall_Left", "Room_Wall_Right"],
    "ceiling": ["Room_Ceiling"],
    "cornice": ["Room_Crown_Moulding"],
    "curtain": ["Booth_Door_Curtain"],
    "booth": ["Booth_Shell_MDF", "Booth_Roof"],
    "booth_trim": ["Booth_Door_Alu_Frame", "Booth_PhotoSlot_Frame", "Booth_Hatch_Frame",
                   "Booth_Hatch_Handle"],
    "heart": ["Booth_Heart"],
    "counter_top": ["C_Counter_Top", "C_Counter_WorkTop"],
    "counter_front": ["C_Counter_Front"],
    "vanity_top": ["D_Table_Top"],
    "mirror_frame": ["D_Mirror_Frame"],
    "picture_frames": ["A_Frame1_Border", "A_Frame2_Border", "A_Frame3_Border"],
    "pendant_globes": ["Room_Pendant1_Globe1", "Room_Pendant1_Globe2", "Room_Pendant1_Globe3"],
}

# Hidden from render: second pendant cluster (review asks for one cluster of 3 over the counter),
# the green potted plant, and the floor-plan annotations drawn for the top-down cameras.
HIDE_PREFIXES = ("Room_Pendant2", "B_PotPlant", "Plan_", "PL_")
PREVIEW_CAMERAS = ["Cam_02_toan_canh_sanh", "Cam_03_tu_loi_vao", "Cam_04_mat_tien_buong",
                   "Cam_s7_guong", "Cam_s8_khu_sofa"]

CHARCOAL = "#2B2724"
CREAM = "#EDE4D8"
TRAVERTINE = "#E2D6C3"
BRASS = "#B08D57"
BURGUNDY = "#5E1A24"
BOOTH_LACQUER = "#1F1C1A"
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


def objs(role):
    scene = bpy.context.scene
    found = [scene.objects[n] for n in ROLES[role] if n in scene.objects]
    missing = [n for n in ROLES[role] if n not in scene.objects]
    if missing:
        log(f"{role}: missing {missing}")
    return found


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


def mat_lacquer():
    mat, bsdf = new_material("PB_Booth_Lacquer")
    bsdf.inputs["Base Color"].default_value = hex_rgba(BOOTH_LACQUER)
    bsdf.inputs["Roughness"].default_value = 0.28
    set_input(bsdf, ["Coat Weight", "Clearcoat"], 0.5)
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
    geo = nodes.new("ShaderNodeNewGeometry")
    wave = nodes.new("ShaderNodeTexWave")
    wave.wave_type = "RINGS"  # rings around Z = vertical flutes on every face of the L counter
    wave.rings_direction = "Z"
    wave.wave_profile = "SIN"
    wave.inputs["Scale"].default_value = 25.0  # ~4 cm flutes
    links.new(geo.outputs["Position"], wave.inputs["Vector"])
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


def assign(targets, mat, role):
    for o in targets:
        if o.type not in {"MESH", "FONT", "CURVE"}:
            continue
        if not o.material_slots:
            o.data.materials.append(mat)
        for slot in o.material_slots:
            slot.link = "OBJECT"  # per-object, so shared materials elsewhere stay untouched
            slot.material = mat
    if targets:
        log(f"{role}: {[o.name for o in targets]} -> {mat.name}")


# ---------------------------------------------------------------- visibility and pendants

def fix_visibility(scene):
    hidden = []
    for o in scene.objects:
        if o.name.startswith(HIDE_PREFIXES):
            if not o.hide_render:
                hidden.append(o.name)
            o.hide_render = True
    log(f"hidden from render: {len(hidden)} objects ({', '.join(sorted({n.split('_')[0] for n in hidden}))})")
    enabled = []
    for o in scene.objects:
        if o.type == "LIGHT" and o.hide_render and not o.name.startswith(HIDE_PREFIXES):
            o.hide_render = False
            enabled.append(o.name)
    log(f"lights switched on: {enabled}")


def fix_pendants(globes):
    done = set()
    for o in globes:
        if not any(m.type == "SUBSURF" for m in o.modifiers):
            mod = o.modifiers.new("PB_Smooth", "SUBSURF")
            mod.levels = 1
            mod.render_levels = 2
        for poly in o.data.polygons:
            poly.use_smooth = True
        for slot in o.material_slots:
            mat = slot.material
            if mat and mat.name not in done and mat.use_nodes:
                done.add(mat.name)
                for n in mat.node_tree.nodes:
                    if n.bl_idname == "ShaderNodeBsdfPrincipled":
                        n.inputs["Emission Strength"].default_value *= 0.35
                        set_input(n, ["Emission Color", "Emission"], (*WARM_2700K, 1.0))
                        n.inputs["Base Color"].default_value = hex_rgba("#F4EEE6")
                        n.inputs["Roughness"].default_value = 0.6
                log(f"pendant material {mat.name}: emission x0.35, 2700K opal")


# ---------------------------------------------------------------- lights

def bbox_world(targets):
    pts = [o.matrix_world @ Vector(c) for o in targets for c in o.bound_box]
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


def add_booth_spot(booth, room_center):
    lo, hi = bbox_world(booth)
    target = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z + (hi.z - lo.z) * 0.55))
    out = room_center.xy - target.xy
    out = out.normalized() if out.length > 1e-3 else Vector((-1.0, 0.0))
    loc = Vector((target.x + out.x * 2.0, target.y + out.y * 2.0, 2.85))
    add_light("PB_Booth_Spot", "SPOT", loc, 150, aim=target,
              spot_size=math.radians(40), spot_blend=0.6, shadow_soft_size=0.05)


def add_cove_lights(ceiling_z, lo, hi):
    """Hidden LED strips in the crown molding: thin area lights facing up along each wall."""
    inset, z = 0.2, ceiling_z - 0.1
    w, d = hi.x - lo.x, hi.y - lo.y
    specs = [
        ("N", ((lo.x + hi.x) / 2, hi.y - inset, z), w),
        ("S", ((lo.x + hi.x) / 2, lo.y + inset, z), w),
        ("E", (hi.x - inset, (lo.y + hi.y) / 2, z), d),
        ("W", (lo.x + inset, (lo.y + hi.y) / 2, z), d),
    ]
    for side, loc, length in specs:
        light = add_light(f"PB_Cove_{side}", "AREA", loc, 12 * length, rotation=(math.pi, 0, 0))
        light.data.shape = "RECTANGLE"
        light.data.size = length * 0.9 if side in "NS" else 0.03
        light.data.size_y = 0.03 if side in "NS" else length * 0.9


def add_picture_lights(frames, room_center):
    for i, o in enumerate(frames):
        lo, hi = bbox_world([o])
        c = (lo + hi) / 2
        out = room_center.xy - c.xy
        out = out.normalized() if out.length > 1e-3 else Vector((0.0, -1.0))
        loc = Vector((c.x + out.x * 0.25, c.y + out.y * 0.25, hi.z + 0.12))
        add_light(f"PB_Picture_{i}", "SPOT", loc, 8, aim=c,
                  spot_size=math.radians(70), spot_blend=0.8, shadow_soft_size=0.02)


# ---------------------------------------------------------------- render setup

def enum_ids(obj, prop):
    return [i.identifier for i in obj.bl_rna.properties[prop].enum_items]


def fix_render(scene):
    engines = enum_ids(scene.render, "engine")
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
        if eng in engines:
            scene.render.engine = eng
            break
    if hasattr(scene, "eevee"):
        if hasattr(scene.eevee, "use_raytracing"):
            scene.eevee.use_raytracing = True
        scene.eevee.taa_render_samples = 64
    vs = scene.view_settings
    for vt in ("AgX", "Filmic"):
        if vt in enum_ids(vs, "view_transform"):
            vs.view_transform = vt
            break
    for look in ("AgX - Medium High Contrast", "Medium High Contrast"):
        if look in enum_ids(vs, "look"):
            vs.look = look
            break
    vs.exposure = 0.0
    log(f"render: {scene.render.engine}, {vs.view_transform} / {vs.look}")


def render_previews(scene, out_dir, tag):
    scene.render.resolution_percentage = 50
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 85
    for name in PREVIEW_CAMERAS:
        cam = scene.objects.get(name)
        if cam is None:
            log(f"camera {name} not found")
            continue
        scene.camera = cam
        scene.render.filepath = os.path.join(out_dir, f"{tag}_{name}.jpg")
        bpy.ops.render.render(write_still=True)
        log(f"rendered {os.path.basename(scene.render.filepath)}")


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

    fix_render(scene)
    fix_visibility(scene)
    fix_pendants(objs("pendant_globes"))

    assign(objs("floor"), mat_checker(), "floor")
    assign(objs("curtain"), mat_velvet(), "curtain")
    assign(objs("booth"), mat_lacquer(), "booth")
    assign(objs("booth_trim") + objs("mirror_frame") + objs("picture_frames"), mat_brass(), "brass")
    assign(objs("heart"), mat_neon(), "heart")
    assign(objs("counter_top") + objs("vanity_top"), mat_travertine(), "tops")
    assign(objs("counter_front"), mat_fluted(), "counter front")

    walls = objs("walls")
    lo, hi = bbox_world(walls)
    center = (lo + hi) / 2
    ceiling_z = bbox_world(objs("ceiling"))[0].z
    add_cove_lights(ceiling_z, lo, hi)
    add_booth_spot(objs("booth"), center)
    add_picture_lights(objs("picture_frames"), center)

    base, ext = os.path.splitext(args.blend)
    ceiling_mat = bpy.data.materials.get("Ceiling")
    variants = [
        ("toi", mat_warm_charcoal(), None),
        ("sang", None, ceiling_mat),
    ]
    for tag, wall_mat, cornice_mat in variants:
        log(f"--- variant {tag}")
        if wall_mat:
            assign(walls + objs("ceiling") + objs("cornice"), wall_mat, "walls/ceiling/cornice")
        else:
            for o in walls + objs("ceiling"):
                for slot in o.material_slots:
                    slot.link = "DATA"  # back to the file's own paint
            if cornice_mat:
                assign(objs("cornice"), cornice_mat, "cornice")
        scene.camera = scene.objects.get(PREVIEW_CAMERAS[0]) or scene.camera
        target = f"{base}_v2_{tag}{ext}"
        bpy.ops.wm.save_as_mainfile(filepath=target, copy=True)
        log(f"saved {target}")
        if not args.no_render:
            render_previews(scene, args.out, tag)

    with open(os.path.join(args.out, "fix_log.json"), "w", encoding="utf-8") as f:
        json.dump(LOG, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
