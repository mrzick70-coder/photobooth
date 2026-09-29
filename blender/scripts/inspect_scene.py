"""Dump a summary of a .blend file to JSON and render a small preview from each camera.

Run: blender -b -P blender/scripts/inspect_scene.py -- --blend <file.blend> --out <dir>
"""
import argparse
import json
import os
import sys

import bpy


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--no-render", action="store_true")
    return parser.parse_args(argv)


def r(values, nd=3):
    return [round(v, nd) for v in values]


def socket_value(node, name):
    sock = node.inputs.get(name)
    if sock is None:
        return None
    if sock.is_linked:
        return "linked:" + sock.links[0].from_node.bl_idname
    val = getattr(sock, "default_value", None)
    try:
        return r(val)
    except TypeError:
        return round(val, 3) if isinstance(val, float) else val


def material_info(mat):
    info = {"users": mat.users, "use_nodes": mat.use_nodes}
    if not mat.use_nodes or not mat.node_tree:
        info["diffuse_color"] = r(mat.diffuse_color)
        return info
    nodes = mat.node_tree.nodes
    info["nodes"] = sorted({n.bl_idname for n in nodes})
    images = [n.image.name for n in nodes if n.bl_idname == "ShaderNodeTexImage" and n.image]
    if images:
        info["images"] = images
    for n in nodes:
        if n.bl_idname == "ShaderNodeBsdfPrincipled":
            info["principled"] = {
                k: socket_value(n, k)
                for k in ("Base Color", "Roughness", "Metallic", "Emission Color",
                          "Emission Strength", "Transmission Weight", "Alpha")
                if n.inputs.get(k) is not None
            }
            break
    for n in nodes:
        if n.bl_idname == "ShaderNodeEmission":
            info["emission_node"] = {k: socket_value(n, k) for k in ("Color", "Strength")}
            break
    return info


def object_info(obj):
    info = {
        "type": obj.type,
        "loc": r(obj.matrix_world.translation),
        "dim": r(obj.dimensions),
        "parent": obj.parent.name if obj.parent else None,
        "collections": [c.name for c in obj.users_collection],
        "hidden_render": obj.hide_render,
    }
    if obj.material_slots:
        info["materials"] = [s.material.name if s.material else None for s in obj.material_slots]
    if obj.modifiers:
        info["modifiers"] = [f"{m.type}:{m.name}" for m in obj.modifiers]
    if obj.type == "MESH":
        info["verts"] = len(obj.data.vertices)
        info["faces"] = len(obj.data.polygons)
    elif obj.type == "LIGHT":
        light = obj.data
        info["light"] = {"type": light.type, "energy": round(light.energy, 3), "color": r(light.color)}
        if light.type == "AREA":
            info["light"]["size"] = [round(light.size, 3), round(light.size_y, 3)]
        elif light.type in {"POINT", "SPOT"}:
            info["light"]["radius"] = round(light.shadow_soft_size, 3)
        if light.type == "SPOT":
            info["light"]["spot_size"] = round(light.spot_size, 3)
    elif obj.type == "CAMERA":
        cam = obj.data
        info["camera"] = {"lens": round(cam.lens, 2), "rot_deg": r([v * 57.2958 for v in obj.matrix_world.to_euler()], 1)}
    return info


def scene_info(scene):
    render = scene.render
    vs = scene.view_settings
    info = {
        "engine": render.engine,
        "resolution": [render.resolution_x, render.resolution_y, render.resolution_percentage],
        "view_transform": vs.view_transform,
        "look": vs.look,
        "exposure": vs.exposure,
        "gamma": vs.gamma,
        "camera": scene.camera.name if scene.camera else None,
        "unit_scale": scene.unit_settings.scale_length,
    }
    if render.engine == "CYCLES":
        info["cycles"] = {"device": scene.cycles.device, "samples": scene.cycles.samples,
                          "denoise": scene.cycles.use_denoising}
    elif hasattr(scene, "eevee"):
        info["eevee_samples"] = scene.eevee.taa_render_samples
    world = scene.world
    if world and world.use_nodes and world.node_tree:
        bg = next((n for n in world.node_tree.nodes if n.bl_idname == "ShaderNodeBackground"), None)
        info["world"] = {"name": world.name, "color": socket_value(bg, "Color") if bg else None,
                         "strength": socket_value(bg, "Strength") if bg else None}
    return info


def gpu_info():
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        return {"compute_device_type": prefs.compute_device_type,
                "devices": [(d.name, d.type, d.use) for d in prefs.devices]}
    except Exception as exc:  # cycles addon missing or prefs unavailable
        return {"error": str(exc)}


def render_previews(scene, out_dir):
    scene.render.resolution_percentage = 50
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 85
    if scene.render.engine == "CYCLES":
        scene.cycles.samples = min(scene.cycles.samples, 64)
    elif hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = min(scene.eevee.taa_render_samples, 32)
    cameras = [o for o in scene.objects if o.type == "CAMERA"]
    for cam in cameras:
        scene.camera = cam
        path = os.path.join(out_dir, f"preview_{bpy.path.clean_name(cam.name)}.jpg")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print("Rendered", path)


def main():
    args = parse_args()
    if not os.path.exists(args.blend):
        raise SystemExit(f"Blend file not found: {args.blend}")
    bpy.ops.wm.open_mainfile(filepath=args.blend)
    os.makedirs(args.out, exist_ok=True)
    scene = bpy.context.scene

    report = {
        "blender_version": bpy.app.version_string,
        "file": os.path.basename(args.blend),
        "scene": scene_info(scene),
        "gpu": gpu_info(),
        "objects": {o.name: object_info(o) for o in sorted(scene.objects, key=lambda o: o.name)},
        "materials": {m.name: material_info(m) for m in bpy.data.materials if m.users},
        "images": {i.name: {"size": list(i.size), "path": i.filepath} for i in bpy.data.images if i.users},
    }
    path = os.path.join(args.out, "scene_report.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
    print("Wrote", path, "-", len(report["objects"]), "objects,", len(report["materials"]), "materials")

    if not args.no_render:
        render_previews(scene, args.out)


if __name__ == "__main__":
    main()
