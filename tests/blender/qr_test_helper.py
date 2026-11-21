"""Blender-side test harness for the MMD Quick Rig presets.

Run inside Blender (Text Editor or an MCP / Python console), e.g.:

    REPO = '/path/to/repo'
    for f in ('tests/blender/qr_test_helper.py', 'tests/blender/qr_pose_test.py'):
        exec(open(REPO + '/' + f, encoding='utf-8').read())
    print(validate_model(REPO + '/_local/mmd/<model>.pmx', mode='CONVERT'))

Rigs are generated through the mmd_to_arp add-on (registered from REPO when needed);
set VIA_ADDON = False to test the preset files with Quick Rig directly instead.

Requires mmd_tools, Auto-Rig Pro and Auto-Rig Pro: Quick Rig. The scene is cleared.
"""
import ast
import os
import sys

import addon_utils
import bpy


def _repo_root():
    if globals().get('REPO'):
        return globals()['REPO']
    if os.environ.get('ARPQ_MMD_REPO'):
        return os.environ['ARPQ_MMD_REPO']
    try:
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    except NameError:
        raise RuntimeError('Set REPO (or $ARPQ_MMD_REPO) to the repository root')


def repo_path(*parts):
    return os.path.join(_repo_root(), *parts)

QR_MOD = 'bl_ext.superhivemarket_com.auto_rig_pro_quick_rig.auto_rig_quick'


def _qr():
    return sys.modules[QR_MOD]


def _view3d_override():
    win = bpy.context.window_manager.windows[0]
    area = next(a for a in win.screen.areas if a.type == 'VIEW_3D')
    region = next(r for r in area.regions if r.type == 'WINDOW')
    return dict(window=win, area=area, region=region, screen=win.screen)


def object_mode():
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')


def clear_scene():
    object_mode()
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    for blocks in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials, bpy.data.actions):
        for b in list(blocks):
            if b.users == 0:
                blocks.remove(b)
    scn = bpy.context.scene
    for _ in range(len(scn.limb_map)):
        scn.limb_map.remove(0)


def import_mmd(path):
    object_mode()
    before = set(bpy.data.objects)
    bpy.ops.mmd_tools.import_model(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    return next(o for o in new if o.type == 'ARMATURE')


def apply_preset(arm, preset_path):
    """Same as Quick Rig 'Import Preset' (without fuzzy match)."""
    object_mode()
    bpy.ops.object.select_all(action='DESELECT')
    arm.hide_set(False)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    scn = bpy.context.scene
    for _ in range(len(scn.limb_map)):
        scn.limb_map.remove(0)
    with open(preset_path, encoding='utf-8') as f:
        d = ast.literal_eval(f.readline())

    class _Op:
        preset_name = 'MMD'
        fuzzy_match = False

    scn.arp_quick_hold_update = True
    try:
        ok = _qr().set_mapping_from_dict(d, arm, _Op())
    finally:
        scn.arp_quick_hold_update = False
    # report unresolved names
    missing = []
    for limb_name, props in d.items():
        limb = scn.limb_map[limb_name]
        for k, v in props.items():
            if isinstance(v, str) and v and (k.startswith('bone_') or k.startswith('override_bone_')
                                             or k in ('thumb', 'index', 'middle', 'ring', 'pinky')):
                if getattr(limb, k) != v:
                    missing.append((limb_name, k, v))
    return ok, missing


def make_rig(arm, mode='CONVERT', **kw):
    object_mode()
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    C = _qr().ARP_OT_quick_make_rig
    C.base_armature_name = arm.name
    C.base_armature_pos = arm.location.copy()
    C.arp_light = False
    for a in addon_utils.modules():
        if a.bl_info['name'] == 'Auto-Rig Pro':
            v = a.bl_info['version']
            C.arp_ver_int = int(str(v[0]) + str(v[1]) + str(v[2]))
    with bpy.context.temp_override(**_view3d_override()):
        return bpy.ops.arp.quick_make_rig('EXEC_DEFAULT', mode=mode, **kw)


# ---------------------------------------------------------------------------
# batch validation
# ---------------------------------------------------------------------------
KEY_GROUPS = ['root.x', 'spine_01.x', 'neck.x', 'head.x',
              'shoulder.l', 'c_arm_twist_offset.l', 'arm_stretch.l', 'forearm_stretch.l',
              'forearm_twist.l', 'hand.l', 'thumb1.l', 'index1.l', 'pinky1.l',
              'thigh_stretch.l', 'leg_stretch.l', 'foot.l', 'toes_01.l']


def _unweighted_vertices(mesh_obj, arm_obj):
    deform = {b.name for b in arm_obj.data.bones if b.use_deform}
    gi = {g.index: g.name for g in mesh_obj.vertex_groups}
    n = 0
    for v in mesh_obj.data.vertices:
        if sum(g.weight for g in v.groups if gi[g.group] in deform) <= 1e-6:
            n += 1
    return n


# How rigs are generated in the tests:
#   True  -> through the add-on (mmd_to_arp.convert operator, post-fix included)
#   False -> through the preset files + Quick Rig + the post-fix modules
VIA_ADDON = True


def ensure_addon():
    """Register mmd_to_arp from the repository if it is not registered yet."""
    root = _repo_root()
    if root not in sys.path:
        sys.path.insert(0, root)
    import mmd_to_arp
    if not hasattr(bpy.types.Scene, 'mmd_to_arp'):
        mmd_to_arp.register()
    return mmd_to_arp


def _effective_parents(arm):
    """Effective parent: the MMD append (付与) source when the bone fully copies its
    rotation (e.g. 足D follows 足), otherwise the hierarchy parent."""
    out = {}
    for pbn in arm.pose.bones:
        mb = pbn.mmd_bone
        src = mb.additional_transform_bone
        if mb.has_additional_rotation and src and mb.additional_transform_influence >= 0.99 \
                and src in arm.pose.bones:
            out[pbn.name] = src
        else:
            out[pbn.name] = pbn.parent.name if pbn.parent else None
    return out


def _absent_bones(arm, preset_name):
    from mmd_to_arp import mapping
    absent = []
    for limb, props in mapping.get_preset(preset_name).items():
        if not (limb.endswith('.l') or limb.endswith('.x')):
            continue
        for k, v in props.items():
            if isinstance(v, str) and v and (k.startswith(('bone_', 'override_bone_'))
                                             or k in ('thumb', 'index', 'middle', 'ring', 'pinky')):
                if v not in arm.data.bones:
                    absent.append(v)
    return absent


def generate_rig(arm, mode='CONVERT', preset=None, make_kw=None, via_addon=None):
    """Generate the ARP rig for `arm`. Returns (rig, preset_name, info)."""
    import contextlib
    import io
    addon = ensure_addon()
    from mmd_to_arp import detect, fix_convert, fix_preserve, mapping, quickrig
    if via_addon is None:
        via_addon = VIA_ADDON
    info = {}
    object_mode()
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    with contextlib.redirect_stdout(io.StringIO()):
        if via_addon:
            if make_kw:
                raise ValueError('make_kw is only supported with via_addon=False')
            st = bpy.context.scene.mmd_to_arp
            st.mode = mode
            st.preset = preset or 'AUTO'
            if bpy.ops.mmd_to_arp.convert() != {'FINISHED'}:
                raise RuntimeError('mmd_to_arp.convert failed')
            rig = bpy.context.active_object
            if preset is None:
                preset = st.detected_preserve if mode == 'PRESERVE' else st.detected_convert
        else:
            if preset is None:
                preset, _ = detect.detect_preset_blender(arm, preserve=(mode == 'PRESERVE'))
            apply_preset(arm, repo_path('presets', preset + '.py'))
            before = set(bpy.data.objects)
            make_rig(arm, mode=mode, **(make_kw or {}))
            rig = next(o for o in bpy.data.objects if o not in before and o.type == 'ARMATURE')
            if mode == 'PRESERVE' and preset.startswith('MMD_P_'):
                rel, muted = fix_preserve.fix(arm, rig)
                info.update(released=len(rel), muted_ik=muted)
            elif mode == 'CONVERT':
                created, _ = fix_convert.fix(rig, arm)
                info['ik_restored'] = created
                info['append_restored'] = [o for o, _t in fix_convert.fix_append(rig, arm)]
    info['absent'] = _absent_bones(arm, preset)
    return rig, preset, info


def validate_model(path, presets_dir=None, mode='CONVERT', preset=None, make_kw=None,
                   via_addon=None, threshold=0.01):
    """Import `path`, generate the rig and check it. presets_dir is kept for backward
    compatibility (preset files are always read from REPO/presets)."""
    import os
    clear_scene()
    arm = import_mmd(path)
    meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.find_armature() == arm]
    unweighted_before = sum(_unweighted_vertices(m, arm) for m in meshes)
    orig_sig = _group_signatures(meshes)
    eff_parents = _effective_parents(arm)
    res = {'model': os.path.basename(path), 'mode': mode}
    try:
        rig, preset, info = generate_rig(arm, mode, preset, make_kw, via_addon)
    except Exception as e:
        res['error'] = repr(e)[:300]
        return res
    res['preset'] = preset
    res.update(info)
    mmd2arp = _limb_map_to_arp(arm)
    if mode == 'CONVERT':
        meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.find_armature() == rig]
        w = {}
        for m in meshes:
            gi = {g.index: g.name for g in m.vertex_groups}
            for v in m.data.vertices:
                for g in v.groups:
                    w[gi[g.group]] = w.get(gi[g.group], 0) + g.weight
        res['empty_groups'] = [g for g in KEY_GROUPS if w.get(g, 0) < 0.5]
        res['unweighted_new'] = sum(_unweighted_vertices(m, rig) for m in meshes) - unweighted_before
        res['not_following'] = follow_check(eff_parents, orig_sig, rig, meshes, mmd2arp, threshold)
    else:
        res['not_following'] = follow_check_preserve(eff_parents, orig_sig, arm, rig, mmd2arp,
                                                     threshold)
    return res


def _group_signatures(meshes):
    """{group_name: (vertex_count, rounded weight sum)} over all meshes."""
    sig = {}
    for m in meshes:
        gi = {g.index: g.name for g in m.vertex_groups}
        for v in m.data.vertices:
            for g in v.groups:
                n = gi[g.group]
                c, w = sig.get(n, (0, 0.0))
                sig[n] = (c + 1, w + g.weight)
    return {k: (c, round(w, 3)) for k, (c, w) in sig.items() if w > 1e-3}


def _limb_map_to_arp(arm_obj):
    """mmd bone -> ARP deform bone, from the current Quick Rig limb mapping."""
    scn = bpy.context.scene
    out = {}
    for limb in scn.limb_map:
        sd = {'LEFT': '.l', 'RIGHT': '.r', 'CENTER': '.x'}[limb.side]
        g = lambda k: getattr(limb, k)
        if limb.type == 'SPINE':
            for i in range(1, limb.spine_amount + 1):
                arp = 'root.x' if i == 1 else 'spine_%02d.x' % (i - 1)
                out[g('bone_%02d' % i)] = arp
        elif limb.type == 'HEAD':
            out[g('bone_01')] = 'neck.x'
            out[g('bone_02')] = 'head.x'
        elif limb.type == 'ARM':
            names = {1: 'shoulder', 2: 'arm_stretch', 3: 'c_arm_twist_offset',
                     4: 'forearm_stretch', 5: 'forearm_twist', 6: 'hand'}
            for i, n in names.items():
                out[g('bone_%02d' % i)] = n + sd
                if limb.weights_override:
                    out[g('override_bone_%02d' % i)] = n + sd
            for i in range(2, limb.twist_bones_amount + 1):
                out[g('bone_twist_%02d_01' % i)] = 'arm_twist_%d%s' % (i, sd)
                out[g('bone_twist_%02d_02' % i)] = 'forearm_twist_%d%s' % (i, sd)
            for f in ('thumb', 'index', 'middle', 'ring', 'pinky'):
                out[g(f)] = f + '1' + sd
                b = arm_obj.data.bones.get(g(f))
                for k in (2, 3):  # follow the first child chain: phalanges 2 and 3
                    if b is None:
                        break
                    b = next((c for c in b.children if not c.name.startswith('_')), None)
                    if b is not None:
                        out[b.name] = 'c_%s%d%s' % (f, k, sd)
        elif limb.type == 'LEG':
            names = {1: 'thigh_stretch', 3: 'leg_stretch', 5: 'foot', 6: 'toes_01'}
            for i, n in names.items():
                out[g('bone_%02d' % i)] = n + sd
                if limb.weights_override:
                    out[g('override_bone_%02d' % i)] = n + sd
    out.pop('', None)
    return out


def follow_check(orig_parents, orig_sig, rig, meshes, mmd2arp, threshold=0.01):
    """Check that weighted orphan bones move with the ARP bone that replaced their
    nearest mapped ancestor. Returns list of (orphan, expected_arp_bone, error_m)."""
    pose_test()
    bad = []
    pb = rig.pose.bones
    for name in orig_sig:
        if name not in pb or name in mmd2arp:
            continue
        a = orig_parents.get(name)
        while a and a not in mmd2arp:
            a = orig_parents.get(a)
        if not a:
            continue
        e = pb.get(mmd2arp[a])
        o = pb[name]
        if e is None:
            continue
        de = e.matrix @ e.bone.matrix_local.inverted()
        do = o.matrix @ o.bone.matrix_local.inverted()
        p = o.bone.head_local
        err = ((de @ p) - (do @ p)).length * rig.matrix_world.to_scale()[0]
        if err > threshold:
            bad.append((name, mmd2arp[a], round(err, 3)))
    pose_test(reset=True)
    return bad


def follow_check_preserve(eff_parents, orig_sig, arm, rig, mmd2arp, threshold=0.01):
    """Preserve mode: the mesh stays on the MMD armature. Every weighted MMD bone must
    move with the ARP bone of its nearest mapped (effective) ancestor."""
    pose_test()
    bad = []
    for name in sorted(orig_sig):
        if name not in arm.pose.bones:
            continue
        a = name
        while a and a not in mmd2arp:
            a = eff_parents.get(a)
        if not a:
            continue
        e = rig.pose.bones.get(mmd2arp[a])
        if e is None:
            continue
        o = arm.pose.bones[name]
        de = rig.matrix_world @ e.matrix @ e.bone.matrix_local.inverted() @ rig.matrix_world.inverted()
        do = arm.matrix_world @ o.matrix @ o.bone.matrix_local.inverted() @ arm.matrix_world.inverted()
        p = arm.matrix_world @ o.bone.head_local
        err = ((de @ p) - (do @ p)).length
        if err > threshold:
            bad.append((name, mmd2arp[a], round(err, 3)))
    pose_test(reset=True)
    return bad


def build_and_pose(path, mode='CONVERT', preset=None, via_addon=None, **make_kw):
    """Import, generate the rig, apply the test pose and hide the armatures."""
    clear_scene()
    arm = import_mmd(path)
    rig, preset, info = generate_rig(arm, mode, preset, make_kw or None, via_addon)
    pose_test()
    sc = bpy.context.scene
    f = sc.frame_current
    sc.frame_set(f + 1)
    sc.frame_set(f)
    rig.hide_set(True)
    arm.hide_set(True)
    meshes = [m.name for m in bpy.data.objects if m.type == 'MESH' and m.find_armature() in (arm, rig)
              and len(m.data.vertices) > 100]
    return preset, info, meshes
