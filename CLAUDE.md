# CLAUDE.md

Project rules for AI coding assistants (and humans) working on this repository.
MMD to Auto-Rig Pro is a Blender extension that converts MMD models (imported with
mmd_tools) into Auto-Rig Pro rigs through Auto-Rig Pro: Quick Rig. This repository is
public.

Repository layout, build, tests, versioning and branches: @DEVELOPMENT.md

## Never publish model names or model data

- Do not write the names of MMD models, characters, model authors or "〇〇式" model
  families anywhere that gets committed: code, comments, preset names, docs, README,
  commit messages, test names.
- Describe a case by its bone structure instead, e.g. "spine 上半身1- / 上半身2-",
  "wrist bone named 手", "D bones without weights". Name presets after the structure
  (`MMD_spine1m`, not a model name).
- MMD models and motions are third-party works. Never commit them, never bundle them in
  the zip, and do not commit test outputs or images made from them. They live in
  `_local/` (git-ignored).
- Check every commit message and new text for model names before committing.

## Testing in Blender

- Run tests in a separate background Blender: `blender -b --python <script>`.
- Never clear or modify the scene of a Blender session someone is working in (for
  example one connected through MCP). The test helpers call `clear_scene()`, which
  deletes everything, unsaved work included.
- The helpers in `tests/blender/` are loaded with `exec()` into one namespace (see
  DEVELOPMENT.md). Models are read from `_local/mmd/`.
- Compare results against the MMD source (vertex positions, bone matrices) rather than
  only checking that the operator finished.

## Code

- Every Python file starts with `# SPDX-License-Identifier: GPL-3.0-or-later`.
- Python only, no network access, no bundled binaries. Bundled assets (images...) must be
  CC0 (Blender extension rules). Do not put e-mail addresses in the manifest or docs.
- Minimum Blender is 4.5. When using an API that changed in 5.x (for example layered
  actions), keep a path that works in 4.5.
- After changing `mmd_to_arp/mapping.py`, regenerate the presets with
  `python3 tools/make_presets.py presets` and commit them. Presets must stay ASCII
  (`\uXXXX` escapes): Quick Rig reads them in the OS default encoding.
- The add-on uses internals of Quick Rig (the Make Rig operator state, reproduced in
  `quickrig.make_rig`) and of Auto-Rig Pro (snap and bake functions in
  `rig_functions`). Keep these calls in `quickrig.py` and `ikfk.py`. After testing a new
  Auto-Rig Pro / Quick Rig version, update `TESTED_VERSIONS` in `quickrig.py` and the
  tested versions in both READMEs.
- Auto-Rig Pro functions read `bpy.context.active_object`: set the rig active around
  the call and restore the previous state.

## Docs

- `README.md` (English) and `README.ja.md` (Japanese) are kept in sync: change both in
  the same commit.
- Many readers use browser translation: short sentences, one idea per sentence, the
  same term for the same thing, lists for steps and conditions. Use the English labels
  of the Blender and add-on UI.
- Avoid naming specific models even as examples (see above).
