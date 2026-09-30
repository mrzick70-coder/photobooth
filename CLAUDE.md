# photobooth

3D model of a self-service photobooth lobby (6 × 3 m) rendered in Blender on the owner's Windows PC
through a self-hosted GitHub Actions runner.

## Render pipeline
- `.github/workflows/blender.yml` runs on the runner labelled `blender`. It runs the script named in
  `blender/run.txt` against the scene file in repo variable `BLEND_FILE`, then commits the output to
  `blender/output/<script>/` with a `[skip ci]` commit.
- A push that touches `blender/scripts/**` or `blender/run.txt` starts a render. Wait for the
  "Add Blender output from run N" commit on the branch, then `git pull`.
- `blender/scripts/apply_palette.py` builds the current concept (`DEFAULT_PALETTE`) and saves
  `<name>_<palette>.blend` next to the original. The original file is never overwritten.

## Rules
- After every render run finishes, pull the output and send the rendered images to the user right
  away with `SendUserFile` (`display: "render"`), without waiting to be asked. Send the main views
  (Cam_03, Cam_02, Cam_04, Cam_08, Cam_s8, Cam_s2, Cam_s7 and any view the change targets), look at
  them first, and say in one line what changed and what still looks wrong.
- Talk to the user in Vietnamese.
