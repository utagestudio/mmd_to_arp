"""Blender-side test harness for the MMD Quick Rig presets.

Run inside Blender (Text Editor or an MCP / Python console), e.g.:

    REPO = '/path/to/repo'
    for f in ('mmd_to_arp/detect.py', 'tests/blender/qr_test_helper.py',
              'tests/blender/qr_pose_test.py'):
        exec(open(REPO + '/' + f, encoding='utf-8').read())
    print(validate_model(REPO + '/_local/mmd/<model>.pmx', REPO + '/presets'))

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


def validate_model(path, presets_dir, mode='CONVERT', preset=None, make_kw=None):
    if mode == 'PRESERVE':
        return validate_model_preserve(path, presets_dir, preset, make_kw)
    import contextlib
    import io
    import os
    clear_scene()
    arm = import_mmd(path)
    meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.find_armature() == arm]
    unweighted_before = sum(_unweighted_vertices(m, arm) for m in meshes)
    orig_sig = _group_signatures(meshes)
    # effective parent: MMD append (付与) source when the bone fully copies its rotation
    # (e.g. 足D follows 足), otherwise the hierarchy parent
    orig_parents = {}
    for pbn in arm.pose.bones:
        mb = pbn.mmd_bone
        src = mb.additional_transform_bone
        if mb.has_additional_rotation and src and mb.additional_transform_influence >= 0.99 \
                and src in arm.pose.bones:
            orig_parents[pbn.name] = src
        else:
            orig_parents[pbn.name] = pbn.parent.name if pbn.parent else None
    if preset is None:
        preset, notes = detect_preset_blender(arm)
    ok, missing = apply_preset(arm, os.path.join(presets_dir, preset + '.py'))
    res = {'model': os.path.basename(path), 'preset': preset, 'missing': [m[2] for m in missing
           if m[0].endswith('.l') or m[0].endswith('.x')]}
    mmd2arp = _limb_map_to_arp()
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            make_rig(arm, mode=mode, **(make_kw or {}))
    except Exception as e:
        res['error'] = repr(e)[:300]
        return res
    rig = bpy.data.objects.get('rig')
    if rig is None:
        res['error'] = 'no rig'
        return res
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
        res['not_following'] = follow_check(orig_parents, orig_sig, rig, meshes, mmd2arp)
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


def _limb_map_to_arp():
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
            arm_obj = bpy.context.view_layer.objects.active
            for f in ('thumb', 'index', 'middle', 'ring', 'pinky'):
                out[g(f)] = f + '1' + sd
                b = arm_obj.data.bones.get(g(f)) if arm_obj and arm_obj.type == 'ARMATURE' else None
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


def build_and_pose(path, mode='CONVERT', preset=None, **make_kw):
    """Import, rig with the detected preset, apply the test pose, hide armatures."""
    import contextlib
    import io
    clear_scene()
    arm = import_mmd(path)
    notes = []
    if preset is None:
        preset, notes = detect_preset_blender(arm, preserve=(mode == 'PRESERVE'))
    apply_preset(arm, repo_path('presets', '%s.py' % preset))
    with contextlib.redirect_stdout(io.StringIO()):
        make_rig(arm, mode=mode, **make_kw)
    rig = bpy.data.objects['rig']
    if preset.startswith('MMD_P_'):
        ns = {'__name__': 'mmd_preserve_fix'}
        exec(open(repo_path('scripts', 'mmd_preserve_fix.py'), encoding='utf-8').read(), ns)
        ns['fix'](arm, rig)
    pose_test()
    sc = bpy.context.scene
    f = sc.frame_current
    sc.frame_set(f + 1)
    sc.frame_set(f)
    rig.hide_set(True)
    arm.hide_set(True)
    meshes = [m.name for m in bpy.data.objects if m.type == 'MESH' and m.find_armature() in (arm, rig)
              and len(m.data.vertices) > 100]
    return preset, notes, meshes


def validate_model_preserve(path, presets_dir, preset=None, make_kw=None, threshold=0.01):
    """Preserve mode: the mesh stays on the MMD armature. Check that every weighted
    MMD bone moves with the ARP bone of its nearest driven ancestor (append sources
    with 100% rotation count as parents, e.g. 足D -> 足)."""
    import contextlib
    import io
    import os
    clear_scene()
    arm = import_mmd(path)
    if preset is None:
        preset, notes = detect_preset_blender(arm, preserve=True)
    apply_preset(arm, os.path.join(presets_dir, preset + '.py'))
    res = {'model': os.path.basename(path), 'preset': preset}
    mmd2arp = _limb_map_to_arp()
    meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.find_armature() == arm]
    weighted = set(_group_signatures(meshes))
    eff_parent = {}
    for pbn in arm.pose.bones:
        mb = pbn.mmd_bone
        src = mb.additional_transform_bone
        if mb.has_additional_rotation and src and mb.additional_transform_influence >= 0.99 \
                and src in arm.pose.bones:
            eff_parent[pbn.name] = src
        else:
            eff_parent[pbn.name] = pbn.parent.name if pbn.parent else None
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            make_rig(arm, mode='PRESERVE', **(make_kw or {}))
    except Exception as e:
        res['error'] = repr(e)[:300]
        return res
    rig = bpy.data.objects.get('rig')
    if rig is None:
        res['error'] = 'no rig'
        return res
    if preset.startswith('MMD_P_'):
        ns = {'__name__': 'mmd_preserve_fix'}
        exec(open(repo_path('scripts', 'mmd_preserve_fix.py'), encoding='utf-8').read(), ns)
        rel, muted = ns['fix'](arm, rig)
        res['released'], res['muted_ik'] = len(rel), muted
    pose_test()
    bad = []
    for name in sorted(weighted):
        if name not in arm.pose.bones:
            continue
        a = name
        while a and a not in mmd2arp:
            a = eff_parent.get(a)
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
    res['not_following'] = bad
    return res
