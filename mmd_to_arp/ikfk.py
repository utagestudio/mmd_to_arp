# SPDX-License-Identifier: GPL-3.0-or-later
"""IK-FK switch of the arms and legs, with snapping.

Uses Auto-Rig Pro's own snap functions (the ones behind its "Snap IK-FK" button), so
the pose is kept and keyframes are inserted when auto keying is enabled, exactly like
Auto-Rig Pro does. Unlike the Auto-Rig Pro button, the limb is given explicitly instead
of being taken from the selected bones.
"""
import sys

import bpy

SIDES = ('.l', '.r')
# limb: (control holding the ik_fk_switch property, snap to FK, snap to IK)
LIMBS = {
    'ARM': ('c_hand_ik', 'fk_to_ik_arm', 'ik_to_fk_arm'),
    'LEG': ('c_foot_ik', 'fk_to_ik_leg', 'ik_to_fk_leg'),
}


def rig_functions():
    """Auto-Rig Pro's rig_functions module (the extension repository name may vary)."""
    for name, mod in list(sys.modules.items()):
        if name.endswith('auto_rig_pro.src.rig_functions') and hasattr(mod, 'fk_to_ik_arm'):
            return mod
    return None


def state(rig, limb, side):
    """'IK', 'FK' or None when the limb does not exist."""
    pb = rig.pose.bones.get(LIMBS[limb][0] + side)
    if pb is None or 'ik_fk_switch' not in pb:
        return None
    return 'IK' if pb['ik_fk_switch'] < 0.5 else 'FK'


def switch(context, rig, limb, side, target):
    """Switch one limb to `target` ('IK' / 'FK') keeping its pose. Returns True if switched."""
    current = state(rig, limb, side)
    if current is None or current == target:
        return False
    rf = rig_functions()
    if rf is None:
        raise RuntimeError('Auto-Rig Pro is not enabled')
    # "fk_to_ik" snaps the FK controls to the IK pose, then switches to FK
    func = getattr(rf, LIMBS[limb][1] if target == 'FK' else LIMBS[limb][2])

    view_layer = context.view_layer
    active = view_layer.objects.active
    mirror = rig.pose.use_mirror_x
    view_layer.objects.active = rig  # Auto-Rig Pro looks bones up on the active object
    rig.pose.use_mirror_x = False
    try:
        func(rig, side)
    finally:
        rig.pose.use_mirror_x = mirror
        view_layer.objects.active = active
    return True


def _fcurve_collections(obj):
    """The F-Curve collections of the action of `obj` (layered actions of Blender 4.4+
    and legacy actions)."""
    adt = obj.animation_data
    act = adt.action if adt else None
    if act is None:
        return []
    if getattr(act, 'layers', None):
        slot = getattr(adt, 'action_slot', None)
        out = []
        for layer in act.layers:
            for strip in layer.strips:
                cb = strip.channelbag(slot) if slot else None
                if cb:
                    out.append(cb.fcurves)
        return out
    return [act.fcurves]


def remove_switch_keys(rig):
    """Remove the keys of the IK-FK switches (Quick Rig's animation bake keys them,
    which prevents switching the limbs later in the motion). Each switch keeps the
    value it has at the current frame. Returns the names of the controls changed."""
    frame = bpy.context.scene.frame_current
    changed = []
    for fcurves in _fcurve_collections(rig):
        for fc in list(fcurves):
            if not fc.data_path.endswith('["ik_fk_switch"]'):
                continue
            value = fc.evaluate(frame)
            name = fc.data_path.split('"')[1]
            fcurves.remove(fc)
            pb = rig.pose.bones.get(name)
            if pb is not None:
                pb['ik_fk_switch'] = value
            changed.append(name)
    return changed

