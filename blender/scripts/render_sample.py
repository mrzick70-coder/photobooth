"""Sample scene: a cube on a floor with a light and camera, rendered to PNG.

Run: blender -b --factory-startup -P blender/scripts/render_sample.py -- --out <dir>
"""
import argparse
import os
import sys

import bpy


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=os.path.join(os.getcwd(), "blender", "output"))
    return parser.parse_args(argv)


def build_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    bpy.ops.mesh.primitive_plane_add(size=10)
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 1))
    cube = bpy.context.active_object
    mat = bpy.data.materials.new("CubeMaterial")
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.9, 0.3, 0.2, 1)
    cube.data.materials.append(mat)

    bpy.ops.object.light_add(type="SUN", location=(4, -4, 8))
    bpy.context.active_object.data.energy = 4

    bpy.ops.object.camera_add(location=(6, -6, 4.5), rotation=(1.1, 0, 0.785))
    scene.camera = bpy.context.active_object

    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.8, 0.85, 0.9, 1)
    scene.world = world
    return scene


def main():
    args = parse_args()
    scene = build_scene()
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 32
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.image_settings.file_format = "PNG"
    os.makedirs(args.out, exist_ok=True)
    scene.render.filepath = os.path.join(args.out, "sample.png")
    bpy.ops.render.render(write_still=True)
    print("Rendered", scene.render.filepath)


if __name__ == "__main__":
    main()
