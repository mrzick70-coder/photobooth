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
import os
import sys

import bpy

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
}

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


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--palette", default="dem_than", choices=sorted(PALETTES))
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

    fx.fix_render(scene)
    fix_visibility(scene)
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

    base, ext = os.path.splitext(args.blend)
    target = f"{base}_{args.palette}{ext}"
    bpy.ops.wm.save_as_mainfile(filepath=target, copy=True)
    fx.log(f"saved {target}")

    if not args.no_render:
        scene.render.resolution_percentage = 50
        scene.render.image_settings.file_format = "JPEG"
        scene.render.image_settings.quality = 88
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
