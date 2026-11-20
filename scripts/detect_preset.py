"""Pick the Quick Rig preset (Convert: MMD_*, Preserve: MMD_P_*) for an MMD skeleton.

Works with mmd_tools bone names ("腕.L") and raw PMX names ("左腕").

In Blender: right after importing the model with mmd_tools, select its root or
armature, open this file in the Text Editor and Run Script. The result is shown
in a popup and printed to the console.

Offline, on the JSON written by tools/pmx_bones.py:
    python scripts/detect_preset.py bones.json [--preserve]
"""


def _normalize(names):
    out = {}
    for n, w in names.items():
        if n.startswith('左'):
            n = n[1:] + '.L'
        elif n.startswith('右'):
            n = n[1:] + '.R'
        out[n] = w
    return out


# models whose weights live in many helper bones (auxiliary twist/muscle bones driven by
# MMD append/IK constraints). Convert mode cannot keep those mechanisms -> Preserve mode.
COMPLEX_MARKERS = ('腕変形0.L', '腕軸D.L', '足軸D.L', 'ひじ軸D.L')


def _spine_thumb(names):
    if '上半身3' in names and '上半身2' in names:
        spine = 'spine3'
    elif '上半身1' in names and '上半身2' in names:
        spine = 'spine1'
    elif '上半身2' in names:
        spine = 'std'
    else:
        spine = 'nospine2'
    thumb = '' if '親指０.L' in names else '_nothumb0'
    return spine, thumb


def detect_preset(bone_weights):
    """Convert-mode preset. bone_weights: {bone_name: total_weight}.

    Returns (preset_name, notes).
    """
    names = _normalize(bone_weights)
    notes = []

    def w(*ns):
        return sum(names.get(n + '.L', 0) for n in ns)

    empty_parts = []
    if w('腕', '腕捩', '腕捩1', '腕捩2', '腕捩3') < 1:
        empty_parts.append('upper arm')
    if w('ひじ', '手捩', '手捩1', '手捩2', '手捩3') < 1:
        empty_parts.append('forearm')
    if w('足', '足D') < 1 and w('ひざ', 'ひざD') < 1:
        empty_parts.append('leg')
    if any(m in names for m in COMPLEX_MARKERS) or empty_parts:
        notes.append('complex helper-bone rig (no weights on main bones: %s): use Preserve mode'
                     % (', '.join(empty_parts) or 'helper bones'))
    if '上半身2-' in names and '上半身1-' in names:
        return 'MMD_spine1m', notes
    if '手首.L' not in names and '手.L' in names:
        notes.append('wrist bone is named 手 (MMD_std_hand assumes 上半身2 / 親指０ / no D bones)')
        return 'MMD_std_hand', notes
    spine, thumb = _spine_thumb(names)
    d = ''
    if '足D.L' in names and (w('足D', 'ひざD') > w('足', 'ひざ')
                             or w('足D', 'ひざD', '足首D') > w('足', 'ひざ', '足首')):
        d = '_D'
        if '足首D.L' not in names:
            if spine == 'std' and not thumb:
                return 'MMD_std_D_ankle', notes
            notes.append('no 足首D: set Leg bone_05 to 足首 manually')
    elif '足首D.L' in names and '足首EX.L' in names:
        if spine == 'std' and not thumb:
            return 'MMD_std_Dempty', notes
        notes.append('D bones without weights')
    return 'MMD_%s%s%s' % (spine, thumb, d), notes


def detect_preset_preserve(bone_weights):
    """Preset for Quick Rig Preserve mode (MMD_P_*). Only operation bones matter."""
    names = _normalize(bone_weights)
    notes = []
    if any(m in names for m in COMPLEX_MARKERS):
        notes.append('helper-bone rig that mmd_tools may not reproduce')
    if '上半身2-' in names and '上半身1-' in names:
        return 'MMD_P_spine1m', notes
    if '手首.L' not in names and '手.L' in names:
        return 'MMD_P_std_hand', notes
    spine, thumb = _spine_thumb(names)
    return 'MMD_P_%s%s' % (spine, thumb), notes


def detect_preset_blender(arm_obj, preserve=False):
    """Detect from an mmd_tools armature and the meshes deformed by it."""
    import bpy
    w = {b.name: 0.0 for b in arm_obj.data.bones}
    for o in bpy.data.objects:
        if o.type != 'MESH' or o.find_armature() != arm_obj:
            continue
        gi = {g.index: g.name for g in o.vertex_groups}
        for v in o.data.vertices:
            for g in v.groups:
                n = gi[g.group]
                if n in w:
                    w[n] += g.weight
    if preserve:
        return detect_preset_preserve(w)
    if sum(w.values()) == 0:
        raise RuntimeError('No mesh is deformed by %s. Run this before "Make Rig!" '
                           '(right after importing the MMD model).' % arm_obj.name)
    return detect_preset(w)


def _main_blender():
    import bpy
    obj = bpy.context.active_object
    if obj and obj.type != 'ARMATURE':
        # mmd_tools root empty -> its armature child
        obj = next((c for c in obj.children_recursive if c.type == 'ARMATURE'), obj)
    if not obj or obj.type != 'ARMATURE':
        print('Select the MMD armature (or its mmd root) first')
        return
    name, notes = detect_preset_blender(obj)
    pname, pnotes = detect_preset_blender(obj, preserve=True)
    msg = 'Quick Rig preset for %s: Convert = %s / Preserve = %s' % (obj.name, name, pname)
    if notes:
        msg += '  (' + '; '.join(notes) + ')'
    print(msg)

    def draw(self, context):
        self.layout.label(text='Convert : ' + name)
        self.layout.label(text='Preserve: ' + pname)
        for n in notes:
            self.layout.label(text=n)
    bpy.context.window_manager.popup_menu(draw, title='MMD Quick Rig preset', icon='INFO')


if __name__ == '__main__':
    try:
        import bpy  # noqa: F401
        _in_blender = True
    except ImportError:
        _in_blender = False
    if _in_blender:
        _main_blender()
    else:
        import json
        import sys
        d = json.load(open(sys.argv[1], encoding='utf-8'))
        for path, v in sorted(d.items()):
            bw = {b['name']: b.get('weight', 0) for b in v['bones']}
            if '左腕' in bw and '左足' in bw:
                name, notes = detect_preset(bw)
                if '--preserve' in sys.argv:
                    name, notes = detect_preset_preserve(bw)
                print(name, path, ('# ' + '; '.join(notes)) if notes else '')
