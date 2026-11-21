# SPDX-License-Identifier: GPL-3.0-or-later
"""Bridge to Auto-Rig Pro: Quick Rig.

Only Quick Rig's scene data (scene.limb_map) and its "Make Rig!" operator are used.
The operator is executed without its dialog, so the preparation that Quick Rig
does in invoke() (base armature, Auto-Rig Pro version) is reproduced here.
"""
import functools
import sys

import addon_utils
import bpy

# Limb properties that hold bone names (Quick Rig skips names missing in the armature)
_BONE_PROPS_PREFIX = ('bone_', 'override_bone_')
_BONE_PROPS = ('thumb', 'index', 'middle', 'ring', 'pinky', 'upper_thigh', 'override_upper_thigh')


class DependencyError(RuntimeError):
    pass


def quickrig_module():
    """The loaded Quick Rig module (extension repository name may vary)."""
    for name, mod in list(sys.modules.items()):
        if name.endswith('auto_rig_quick') and hasattr(mod, 'ARP_OT_quick_make_rig'):
            return mod
    return None


def arp_version():
    """Auto-Rig Pro version as Quick Rig expects it (e.g. (3, 79, 22) -> 37922)."""
    for mod in addon_utils.modules():
        if mod.bl_info.get('name') in ('Auto-Rig Pro', 'Auto-Rig Pro (Light)'):
            if addon_utils.check(mod.__name__)[1]:
                v = mod.bl_info['version']
                return int('%d%d%d' % (v[0], v[1], v[2])), 'Light' in mod.bl_info['name']
    return None, False


# (major, minor) range of the dependency versions this add-on was tested with. Other
# versions may work, the panel only shows a small warning: the add-on uses internals
# of Quick Rig and of Auto-Rig Pro's snap functions, which may change.
TESTED_VERSIONS = {
    'Auto-Rig Pro': ((3, 79), (3, 79)),
    'Auto-Rig Pro: Quick Rig': ((1, 28), (1, 28)),
}


def addon_version(name):
    """Version tuple of the enabled add-on / extension named `name`, or None."""
    for mod in addon_utils.modules():
        if mod.bl_info.get('name') == name and addon_utils.check(mod.__name__)[1]:
            return tuple(mod.bl_info.get('version', ()))
    return None


@functools.lru_cache(maxsize=1)  # add-on updates need a Blender restart anyway
def untested_versions():
    """[(name, installed 'x.y.z', tested 'x.y' or 'x.y-x.y')] for the enabled
    dependencies whose version is outside TESTED_VERSIONS."""
    out = []
    for name, (lo, hi) in TESTED_VERSIONS.items():
        v = addon_version(name)
        if not v or len(v) < 2:
            continue
        if not lo <= tuple(v[:2]) <= hi:
            tested = '%d.%d' % lo if lo == hi else '%d.%d-%d.%d' % (lo + hi)
            out.append((name, '.'.join(str(x) for x in v), tested))
    return tuple(out)


def mmd_tools_enabled():
    # bpy.ops returns a wrapper for any name, so check what mmd_tools registers
    if not hasattr(bpy.types.PoseBone, 'mmd_bone'):
        return False
    try:
        bpy.ops.mmd_tools.import_model.get_rna_type()
    except KeyError:
        return False
    return True


def missing_dependencies():
    missing = []
    if not mmd_tools_enabled():
        missing.append('mmd_tools')
    if arp_version()[0] is None:
        missing.append('Auto-Rig Pro')
    if quickrig_module() is None or not hasattr(bpy.types.Scene, 'limb_map'):
        missing.append('Auto-Rig Pro: Quick Rig')
    return missing


def check_dependencies():
    missing = missing_dependencies()
    if missing:
        raise DependencyError('Required add-ons are not enabled: ' + ', '.join(missing))


def _is_bone_prop(key):
    return key.startswith(_BONE_PROPS_PREFIX) or key in _BONE_PROPS


def apply_mapping(scene, armature, mapping):
    """Replace Quick Rig's limb list with `mapping` ({limb_name: {prop: value}}).

    Bone names missing in `armature` are left empty, like Quick Rig's preset import.
    Returns [(limb_name, prop, bone_name)] of the skipped bone names.
    """
    bones = armature.data.bones
    skipped = []
    scene.arp_quick_hold_update = True
    try:
        scene.limb_map.clear()
        for limb_name, props in mapping.items():
            item = scene.limb_map.add()
            for key, value in props.items():
                if _is_bone_prop(key) and isinstance(value, str) and value and value not in bones:
                    skipped.append((limb_name, key, value))
                    value = ''
                try:
                    setattr(item, key, value)
                except (AttributeError, TypeError, ValueError):
                    pass  # property unknown to this Quick Rig version
        scene.limb_map_index = 0
    finally:
        scene.arp_quick_hold_update = False
    return skipped


# An elbow bent backward by less than this (relative to the arm length) may get its IK
# pole in front of the arm: Quick Rig places the pole from the arm bone roll, not from
# the bend, so almost straight or forward bent MMD arms can bend backward in IK.
ELBOW_BACK_MIN = 0.004


def elbow_back_ratio(armature, limb):
    """How far the elbow is bent backward (+Y, MMD models face -Y), relative to the arm
    length. None if the arm bones are missing."""
    bones = armature.data.bones
    names = (limb.bone_02, limb.bone_04, limb.bone_06)
    if not all(n and n in bones for n in names):
        return None
    mw = armature.matrix_world
    sh, el, wr = (mw @ bones[n].head_local for n in names)
    axis = wr - sh
    if axis.length == 0:
        return None
    t = (el - sh).dot(axis) / axis.length_squared
    offset = el - (sh + axis * t)
    return offset.y / axis.length


def fix_elbow_direction(scene, armature):
    """Make Quick Rig point the elbow backward (Auto-Elbow, straight) on arms that are
    not clearly bent backward. Returns the limb names changed."""
    changed = []
    for limb in scene.limb_map:
        if limb.type != 'ARM':
            continue
        ratio = elbow_back_ratio(armature, limb)
        if ratio is not None and ratio < ELBOW_BACK_MIN:
            limb.auto_elbow = True
            limb.auto_elbow_straight = True
            limb.IK_axis_correc = 'Y'
            changed.append(limb.name)
    return changed


# Quick Rig only offers spheres and boxes for the orphan bones (the MMD hair, skirt,
# accessory bones...): many overlapping spheres hide which bone is which, a line along
# each bone shows the chains.
ORPHAN_SHAPES = {'LINE': 'cs_line', 'SPHERE': 'cs_sphere', 'BOX': 'cs_box'}
QR_ORPHAN_SHAPES = ('SPHERE', 'BOX')  # natively supported by Quick Rig


def quickrig_orphan_shape(shape):
    """Value of Quick Rig's orphan_bones_shape for our `shape` setting."""
    return ORPHAN_SHAPES[shape if shape in QR_ORPHAN_SHAPES else 'SPHERE']


def _shape_object(rig, name):
    """The Auto-Rig Pro shape object `name` used by this rig (several rigs in a file
    may have their own copies, cs_line.001...)."""
    for pb in rig.pose.bones:
        cs = pb.custom_shape
        if cs and (cs.name == name or cs.name.startswith(name + '.')):
            return cs
    return bpy.data.objects.get(name)


def set_orphan_shape(rig, shape):
    """Give the orphan bones (tagged "cc" by Quick Rig) the custom shape `shape`, for
    the shapes Quick Rig cannot assign itself. Returns the number of bones changed."""
    if shape in QR_ORPHAN_SHAPES:
        return 0
    qr_shape = quickrig_orphan_shape(shape)
    cs = _shape_object(rig, ORPHAN_SHAPES[shape])
    if cs is None:
        return 0
    count = 0
    for pb in rig.pose.bones:
        cur = pb.custom_shape
        if 'cc' not in pb.keys() or cur is None or cur.name.split('.')[0] != qr_shape:
            continue
        pb.custom_shape = cs
        pb.custom_shape_scale_xyz = (1.0, 1.0, 1.0)  # the line spans the whole bone
        count += 1
    return count


def validate_mapping(scene, armature):
    """Required bones, as checked by Quick Rig before generating the rig."""
    bones = armature.data.bones
    errors = []

    def ok(name):
        return bool(name) and name in bones

    for limb in scene.limb_map:
        side = limb.side.lower()
        if limb.type == 'SPINE':
            for i in range(1, limb.spine_amount + 1):
                if not ok(getattr(limb, 'bone_%02d' % i)):
                    errors.append('Spine: bone_%02d' % i)
        elif limb.type == 'HEAD':
            if not ok(limb.bone_02):
                errors.append('Head: head bone')
        elif limb.type == 'ARM':
            for key, label in (('bone_02', 'arm'), ('bone_04', 'forearm'), ('bone_06', 'hand')):
                if not ok(getattr(limb, key)):
                    errors.append('Arm %s: %s' % (side, label))
        elif limb.type == 'LEG':
            for key, label in (('bone_01', 'thigh'), ('bone_03', 'calf'), ('bone_05', 'foot')):
                if not ok(getattr(limb, key)):
                    errors.append('Leg %s: %s' % (side, label))
    return errors


def _view3d_override(context):
    for win in context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == 'VIEW_3D':
                region = next(r for r in area.regions if r.type == 'WINDOW')
                return dict(window=win, area=area, region=region, screen=win.screen)
    raise RuntimeError('A 3D Viewport is required')


def make_rig(context, armature, mode='CONVERT', **options):
    """Run Quick Rig "Make Rig!" on `armature` with the current limb list.

    Returns the generated ARP armature object.
    """
    check_dependencies()
    qr = quickrig_module()
    errors = validate_mapping(context.scene, armature)
    if errors:
        raise RuntimeError('Missing required bones: ' + ', '.join(errors))

    if context.object and context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for o in context.view_layer.objects:
        o.select_set(False)
    armature.hide_set(False)
    armature.select_set(True)
    context.view_layer.objects.active = armature

    ver, light = arp_version()
    op = qr.ARP_OT_quick_make_rig
    # state normally prepared by the operator's invoke()
    op.base_armature_name = armature.name
    op.base_armature_pos = armature.location.copy()
    op.arp_ver_int = ver
    op.arp_light = light
    op.error_mess = ''
    op.error_qr_data = False
    for attr in ('fingers_ctrl', 'toes_ctrl', 'tail_ctrl', 'spline_ctrl',
                 'meshes_parented_to_bones', 'skin_dict', 'orphan_bones_dict'):
        setattr(op, attr, {})

    before = set(bpy.data.objects)
    with context.temp_override(**_view3d_override(context)):
        bpy.ops.arp.quick_make_rig('EXEC_DEFAULT', mode=mode, **options)
    new_arms = [o for o in bpy.data.objects if o not in before and o.type == 'ARMATURE']
    if not new_arms:
        raise RuntimeError('Quick Rig did not create a rig' +
                           (': ' + op.error_mess if getattr(op, 'error_mess', '') else ''))
    return new_arms[0]
