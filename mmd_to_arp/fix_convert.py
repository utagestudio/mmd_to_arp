# SPDX-License-Identifier: GPL-3.0-or-later
"""Run after Quick Rig "Make Rig!" in Convert mode with an MMD_* preset.

Quick Rig (Convert) does not copy the constraints of orphan bones, so helper bones
that the MMD model drives with IK lose their motion -- e.g. detached sleeves that
hang from the shoulder and chase IK targets parented to the arm.

The same goes for MMD "append" (付与: copy the rotation / location of another bone),
e.g. the eyes that follow the 両目 bone, highlight bones, 肩C.

This script, on the converted rig:
  - re-creates the MMD IK constraints when the IK owner and its target both exist in
    the rig as orphan bones (same name) and every bone of the IK chain is an orphan
    bone. IK on mapped bones (足ＩＫ on ひざ...) is skipped: ARP drives those bones.
  - restores append when the owner and the append target both exist in the rig as
    orphan bones, using mmd_tools' own implementation (shadow bones + Transformation
    constraints). Append from a main bone replaced by an Auto-Rig Pro bone (足, ひざ...)
    goes through a proxy bone that reproduces the local rotation of the MMD bone. Append
    on mapped owners (腕捩1 <- 腕捩...) is skipped, and so is append from bones moved by
    MMD IK that could not be re-created.
  - after a motion bake, gives the bones driven by these mechanisms their VMD keys back
    (the bake keyed their final pose, which would apply the mechanism twice), and
    corrects the root location (Auto-Rig Pro's root pivots elsewhere than 下半身).

Used by the addon; also runs standalone: select the ARP rig, open this file in
the Text Editor and Run Script.
It is safe to run several times (existing re-created IK is not duplicated).
"""
import sys

import bpy
from mathutils import Vector

CNS_NAME = 'MMD_IK'
IK_BONE_PROPS = ('lock_ik_x', 'lock_ik_y', 'lock_ik_z',
                 'use_ik_limit_x', 'use_ik_limit_y', 'use_ik_limit_z',
                 'ik_min_x', 'ik_max_x', 'ik_min_y', 'ik_max_y', 'ik_min_z', 'ik_max_z',
                 'ik_stiffness_x', 'ik_stiffness_y', 'ik_stiffness_z', 'ik_stretch')


def _find_rig_and_source():
    obj = bpy.context.active_object
    rig = obj if obj and obj.type == 'ARMATURE' and obj.data.bones.get('c_traj') else None
    if rig is None:
        rig = next((o for o in bpy.data.objects
                    if o.type == 'ARMATURE' and o.data.bones.get('c_traj')), None)
    if rig is None:
        return None, None
    names = {b.name for b in rig.data.bones}
    best, score = None, 0
    for o in bpy.data.objects:
        if o.type != 'ARMATURE' or o == rig:
            continue
        s = len(names & {b.name for b in o.data.bones})
        if s > score:
            best, score = o, s
    return rig, best


def fix(rig, src):
    src_names = {b.name for b in src.data.bones}
    created, skipped = [], []
    for spb in src.pose.bones:
        for c in spb.constraints:
            if c.type != 'IK' or c.mute or c.target != src or not c.subtarget:
                continue
            owner = rig.pose.bones.get(spb.name)
            target = rig.pose.bones.get(c.subtarget)
            if owner is None or target is None or c.chain_count == 0:
                skipped.append((spb.name, 'owner/target not in rig'))
                continue
            chain, b = [], owner
            for _ in range(c.chain_count):
                if b is None:
                    break
                chain.append(b)
                b = b.parent
            if any(cb.name not in src_names for cb in chain):
                skipped.append((spb.name, 'chain contains ARP bones'))
                continue
            if any(x.type == 'IK' and x.subtarget == c.subtarget for x in owner.constraints):
                continue  # already there
            ik = owner.constraints.new('IK')
            ik.name = CNS_NAME
            ik.target = rig
            ik.subtarget = c.subtarget
            ik.chain_count = c.chain_count
            ik.iterations = c.iterations
            ik.use_tail = c.use_tail
            ik.use_stretch = c.use_stretch
            ik.weight = c.weight
            ik.influence = c.influence
            for cb in chain:
                sb = src.pose.bones[cb.name]
                for p in IK_BONE_PROPS:
                    setattr(cb, p, getattr(sb, p))
            created.append(spb.name)
    return created, skipped


APPEND_PROPS = ('has_additional_rotation', 'has_additional_location',
                'additional_transform_influence')


def _mmd_fnbone():
    """mmd_tools' FnBone (the extension repository name may vary)."""
    for name, mod in list(sys.modules.items()):
        if name.endswith('mmd_tools.core.bone') and hasattr(mod, 'FnBone'):
            return mod.FnBone
    return None


def _ik_chain_bones(arm, skip=()):
    """Names of the bones moved by enabled IK constraints of `arm`, except the IK of the
    owners in `skip`."""
    names = set()
    for pb in arm.pose.bones:
        if pb.name in skip:
            continue
        for c in pb.constraints:
            if c.type != 'IK' or c.mute or c.influence == 0 or not c.subtarget:
                continue
            b = pb if c.use_tail else pb.parent
            for _ in range(c.chain_count or 255):
                if b is None:
                    break
                names.add(b.name)
                b = b.parent
    return names


PROXY_PREFIX = '_mmd_proxy_'
PROXY_CNS = 'mmd_proxy'


def mapped_bones(src):
    """MMD bone -> Auto-Rig Pro deform bone for the main bones of the current Quick Rig
    limb mapping (spine, neck, head, shoulder, arm, elbow, wrist, leg bones). Twist
    bones are left out: MMD and Auto-Rig Pro split the twist differently."""
    out = {}
    for limb in getattr(bpy.context.scene, 'limb_map', ()):
        sd = {'LEFT': '.l', 'RIGHT': '.r', 'CENTER': '.x'}.get(limb.side, '.x')
        if limb.type == 'SPINE':
            items = [(i, 'root' if i == 1 else 'spine_%02d' % (i - 1))
                     for i in range(1, limb.spine_amount + 1)]
        elif limb.type == 'HEAD':
            items = [(1, 'neck'), (2, 'head')]
        elif limb.type == 'ARM':
            items = [(1, 'shoulder'), (2, 'arm_stretch'), (4, 'forearm_stretch'), (6, 'hand')]
        elif limb.type == 'LEG':
            items = [(1, 'thigh_stretch'), (3, 'leg_stretch'), (5, 'foot'), (6, 'toes_01')]
        else:
            continue
        for i, arp in items:
            name = getattr(limb, 'bone_%02d' % i, '')
            if name and name in src.data.bones:
                out[name] = arp + sd
    return out


def _rig_equivalent(rig, src, name, mapped):
    """The rig bone that moves like the MMD bone `name` (or its nearest ancestor)."""
    b = src.data.bones.get(name)
    while b is not None:
        if b.name in rig.data.bones:
            return b.name
        if b.name in mapped and mapped[b.name] in rig.data.bones:
            return mapped[b.name]
        b = b.parent
    return None


def _make_proxies(rig, src, targets, mapped):
    """For append targets that are mapped bones (replaced by Auto-Rig Pro bones), build a
    proxy bone with the rest pose of the MMD bone, under the rig equivalent of its MMD
    parent, copying the world transform of a follower parented to the Auto-Rig Pro bone:
    its local rotation is the one of the MMD bone. Returns {target: proxy name}."""
    view_layer = bpy.context.view_layer
    active, mode = view_layer.objects.active, rig.mode
    hidden = rig.hide_get()
    rig.hide_set(False)
    view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    proxies = {}
    try:
        eb = rig.data.edit_bones
        to_rig = rig.matrix_world.inverted() @ src.matrix_world
        for t in targets:
            sb = src.data.bones[t]
            parent = _rig_equivalent(rig, src, sb.parent.name, mapped) if sb.parent else None
            if parent is None:
                continue
            m = to_rig @ sb.matrix_local
            name = PROXY_PREFIX + t
            for bname, bparent in ((name + '_follow', mapped[t]), (name, parent)):
                b = eb.get(bname) or eb.new(bname)
                b.head = (0.0, 0.0, 0.0)
                b.tail = (0.0, sb.length, 0.0)
                b.matrix = m.normalized()
                b.parent = eb[bparent]
                b.use_connect = False
                b.use_deform = False
            proxies[t] = name
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')
    coll = rig.data.collections.get('mmd_shadow')
    for t, name in proxies.items():
        for bname in (name, name + '_follow'):
            bone = rig.data.bones[bname]
            if coll is not None:
                for c in list(bone.collections):
                    c.unassign(bone)
                coll.assign(bone)
        pb = rig.pose.bones[name]
        pb.rotation_mode = 'QUATERNION'
        c = pb.constraints.get(PROXY_CNS) or pb.constraints.new('COPY_TRANSFORMS')
        c.name = PROXY_CNS
        c.target = rig
        c.subtarget = name + '_follow'
    view_layer.objects.active = rig
    if mode != 'OBJECT':
        bpy.ops.object.mode_set(mode=mode)
    view_layer.objects.active = active
    rig.hide_set(hidden)
    return proxies


def fix_append(rig, src):
    """Restore MMD append on orphan bones. Returns [(owner, target)] restored."""
    fn = _mmd_fnbone()
    if fn is None or not hasattr(bpy.types.PoseBone, 'mmd_bone'):
        return []
    # append owner -> target, for owners that are orphan bones of the rig and targets that
    # are orphan bones too, or main bones replaced by Auto-Rig Pro bones (through a proxy)
    mapped = {k: v for k, v in mapped_bones(src).items() if v in rig.data.bones}
    pairs = {}
    for spb in src.pose.bones:
        mb = spb.mmd_bone
        if spb.is_mmd_shadow_bone or not (mb.has_additional_rotation or mb.has_additional_location):
            continue
        target = mb.additional_transform_bone
        if target and spb.name in rig.pose.bones and (target in rig.pose.bones or target in mapped):
            pairs[spb.name] = target
    # a target moved by an MMD IK that is not re-created on the rig, or by an append that
    # is not restored, moves differently in the rig: skip such appends. IK re-created by
    # fix() (owner, chain and target all orphan bones) moves like in MMD, e.g. helper
    # bones that extract the thigh swing for the thigh twist / deform bones.
    recreated = {pb.name for pb in rig.pose.bones
                 if any(c.type == 'IK' and c.name == CNS_NAME for c in pb.constraints)}
    lost = _ik_chain_bones(src, skip=recreated)
    lost |= {b.name for b in src.pose.bones if not b.is_mmd_shadow_bone and b.name not in pairs
             and (b.mmd_bone.has_additional_rotation or b.mmd_bone.has_additional_location)
             and b.mmd_bone.additional_transform_bone}
    changed = True
    while changed:
        changed = False
        for owner, target in list(pairs.items()):
            # mapped targets move like in MMD: Auto-Rig Pro drives them, IK included
            if target in lost and target not in mapped:
                del pairs[owner]
                lost.add(owner)
                changed = True
    proxies = _make_proxies(rig, src, sorted({t for t in pairs.values() if t in mapped
                                              and t not in rig.pose.bones}), mapped)
    restored = []
    for spb in src.pose.bones:
        if spb.name not in pairs:
            continue
        mb = spb.mmd_bone
        target = pairs[spb.name]
        if target not in rig.pose.bones:
            if target not in proxies:
                continue
            target = proxies[target]
        owner = rig.pose.bones[spb.name]
        rb = owner.mmd_bone
        for p in APPEND_PROPS:
            setattr(rb, p, getattr(mb, p))
        rb.additional_transform_bone = target
        restored.append((spb.name, target))
    if restored:
        fn.setup_special_bone_collections(rig)
        fn.apply_additional_transformation(rig)
    return restored


def _action_fcurves(obj):
    """F-Curve collections of the action of `obj` (layered and legacy actions)."""
    adt = obj.animation_data
    act = adt.action if adt else None
    if act is None:
        return []
    if getattr(act, 'layers', None):
        slot = getattr(adt, 'action_slot', None)
        return [cb.fcurves for layer in act.layers for strip in layer.strips
                for cb in [strip.channelbag(slot) if slot else None] if cb]
    return [act.fcurves]


def _driven_bones(rig):
    """Orphan bones of the rig moved by re-created MMD constraints: append owners and
    their shadow / dummy bones, IK owners and the rest of their IK chains."""
    names = set()
    for pb in rig.pose.bones:
        if pb.is_mmd_shadow_bone or pb.name.startswith(('_dummy_', '_shadow_')):
            names.add(pb.name)
        for c in pb.constraints:
            if c.name in ('mmd_additional_rotation', 'mmd_additional_location'):
                names.add(pb.name)
            elif c.type == 'IK' and c.name == CNS_NAME:
                b = pb if c.use_tail else pb.parent
                for _ in range(c.chain_count or 255):
                    if b is None:
                        break
                    names.add(b.name)
                    b = b.parent
    return names


def restore_driven_motion(rig, src):
    """After a motion bake: Quick Rig bakes the final pose of the orphan bones, which
    already includes the effect of MMD append / IK. With those mechanisms restored on
    the rig the effect would apply twice, so the keys of the driven bones are replaced
    by the keys of the MMD armature (the VMD motion itself). Returns the bone names."""
    rig_cols = _action_fcurves(rig)
    if not rig_cols:
        return []
    src_fcs = [fc for col in _action_fcurves(src) for fc in col]
    driven = {n for n in _driven_bones(rig) if n in src.pose.bones}
    if not driven:
        return []
    col = rig_cols[0]
    for c in rig_cols:
        for fc in list(c):
            name = fc.data_path.split('"')[1] if fc.data_path.startswith('pose.bones["') else None
            if name in driven:
                c.remove(fc)
    for fc in src_fcs:
        name = fc.data_path.split('"')[1] if fc.data_path.startswith('pose.bones["') else None
        if name not in driven:
            continue
        new = col.new(fc.data_path, index=fc.array_index)
        new.keyframe_points.add(len(fc.keyframe_points))
        for kp, sk in zip(new.keyframe_points, fc.keyframe_points):
            kp.co = sk.co
            kp.interpolation = sk.interpolation
            kp.handle_left_type = sk.handle_left_type
            kp.handle_right_type = sk.handle_right_type
            kp.handle_left = sk.handle_left
            kp.handle_right = sk.handle_right
        new.update()
    for name in driven:
        rig.pose.bones[name].rotation_mode = src.pose.bones[name].rotation_mode
        rig.pose.bones[name].matrix_basis = src.pose.bones[name].matrix_basis.copy()
    return sorted(driven)


# Auto-Rig Pro deform bone -> controller that carries its baked location
POSITION_CTRLS = (('root.x', 'c_root_master.x'),
                  ('spine_01.x', 'c_spine_01.x'), ('spine_02.x', 'c_spine_02.x'),
                  ('spine_03.x', 'c_spine_03.x'), ('neck.x', 'c_neck.x'), ('head.x', 'c_head.x'),
                  ('shoulder.l', 'c_shoulder.l'), ('shoulder.r', 'c_shoulder.r'))


class RootMotionFix:
    """After a motion bake: Auto-Rig Pro's Remap places the root at the location of the
    MMD root bone (下半身) only, but root.x pivots elsewhere (the MMD bone's head is at
    the top of the hips), so a turning hip shifts the whole body. Correct the location
    keys of the root controller first, then of the controls and orphan bones baked with
    absolute locations (shoulders, hair...), which the root correction moved.

    Runs frame by frame with `step()` so that it can be spread over timer events and
    stopped; `finish()` writes the corrections found so far into the keys. The keys are
    only changed at the end: changing a key makes Blender evaluate the whole action
    again, which is slower than the correction itself."""

    def __init__(self, rig, src):
        self.rig, self.src = rig, src
        self.frames, self.items, self.keys, self.loc_fcs = [], [], {}, {}
        self.offsets = {}  # (bone, frame) -> local offset (Vector)
        self.index = 0
        self.meshes = None
        mmd_of = {v: k for k, v in mapped_bones(src).items()}
        for col in _action_fcurves(rig):
            for fc in col:
                if fc.data_path.startswith('pose.bones["') and fc.data_path.endswith('"].location'):
                    self.loc_fcs.setdefault(fc.data_path.split('"')[1], [None] * 3)[fc.array_index] = fc
        root_ctrl = POSITION_CTRLS[0][1]
        if 'root.x' not in mmd_of or root_ctrl not in self.loc_fcs or 'root.x' not in rig.pose.bones:
            return
        items = [(mmd_of['root.x'], 'root.x', root_ctrl)]
        for deform, ctrl in POSITION_CTRLS[1:]:
            if deform in mmd_of and deform in rig.pose.bones and ctrl in self.loc_fcs:
                items.append((mmd_of[deform], deform, ctrl))
        # orphan bones baked with absolute locations: the first orphan bone of each chain
        # (its parent is an Auto-Rig Pro bone); the rest of the chain follows its parent
        driven = _driven_bones(rig)
        for pb in rig.pose.bones:
            if ('cc' not in pb.keys() or pb.name not in src.pose.bones or pb.name in driven
                    or pb.name not in self.loc_fcs or (pb.parent is not None and 'cc' in pb.parent.keys())
                    or any('cc' not in c.keys() for c in pb.children_recursive)):
                continue  # also skip orphans above Auto-Rig Pro controls (全ての親, 肩P...)
            items.append((pb.name, pb.name, pb.name))
        self.items = items
        for bone in {c for *_x, c in items}:
            for axis, fc in enumerate(self.loc_fcs[bone]):
                for kp in (fc.keyframe_points if fc else ()):
                    self.keys.setdefault((bone, int(round(kp.co[0]))), [None] * 3)[axis] = kp
        self.frames = sorted(f for b, f in self.keys if b == root_ctrl)

    @property
    def total(self):
        return len(self.frames)

    @property
    def done(self):
        return self.index >= len(self.frames)

    def _begin(self):
        scn = bpy.context.scene
        self.frame = scn.frame_current
        # only the armatures are needed: skip mesh evaluation
        self.meshes = [o for o in scn.objects if o.type == 'MESH' and not o.hide_viewport]
        for o in self.meshes:
            o.hide_viewport = True

    def step(self, count=1):
        """Correct the next `count` frames. Returns True when all frames are done."""
        if self.meshes is None:
            self._begin()
        scn = bpy.context.scene
        view_layer = bpy.context.view_layer
        rig, src = self.rig, self.src
        mw = rig.matrix_world
        for f in self.frames[self.index:self.index + count]:
            scn.frame_set(f)
            for mmd, deform, ctrl in self.items:
                kps = self.keys.get((ctrl, f))
                if kps is None:
                    continue
                spb = src.pose.bones[mmd]
                if mmd == deform:  # orphan bone: same rest pose as in MMD
                    target = src.matrix_world @ spb.head
                else:
                    sbone = src.data.bones[mmd]
                    d = (src.matrix_world @ spb.matrix) @ (src.matrix_world @ sbone.matrix_local).inverted()
                    target = d @ (mw @ rig.data.bones[deform].head_local)
                delta = target - mw @ rig.pose.bones[deform].head
                if delta.length < 1e-4:  # 0.1 mm
                    continue
                pb = rig.pose.bones[ctrl]
                rest = (pb.parent.matrix @ pb.parent.bone.matrix_local.inverted() @ pb.bone.matrix_local
                        if pb.parent else pb.bone.matrix_local)
                local = (mw @ rest).to_3x3().inverted() @ delta
                for axis, (kp, v) in enumerate(zip(kps, local)):
                    if kp is not None:
                        pb.location[axis] += v
                self.offsets[(ctrl, f)] = local
                if mmd != deform:
                    # the bones below (also through Auto-Rig Pro constraints) move with
                    # it; orphan chains do not depend on each other
                    view_layer.update()
            self.index += 1
        return self.done

    def finish(self):
        """Write the corrections into the keys and restore the scene. Returns the number
        of keys changed."""
        for (ctrl, f), local in self.offsets.items():
            for kp, v in zip(self.keys[(ctrl, f)], local):
                if kp is not None:
                    kp.co[1] += v
                    kp.handle_left[1] += v
                    kp.handle_right[1] += v
        for fcs in self.loc_fcs.values():
            for fc in fcs:
                if fc:
                    fc.update()
        if self.meshes is not None:
            for o in self.meshes:
                try:
                    o.hide_viewport = False
                except ReferenceError:
                    pass
            bpy.context.scene.frame_set(self.frame)
            self.meshes = None
        return len(self.offsets)


def fix_root_motion(rig, src):
    """Run RootMotionFix on all frames at once. Returns the number of keys changed."""
    job = RootMotionFix(rig, src)
    if not job.frames:
        return 0
    try:
        job.step(len(job.frames))
    finally:
        changed = job.finish()
    return changed


def main():
    rig, src = _find_rig_and_source()
    if rig is None or src is None:
        print('ARP rig or source MMD armature not found. Run Make Rig! (Convert) first.')
        return [], [], []
    created, skipped = fix(rig, src)
    restored = fix_append(rig, src)
    print('mmd_convert_fix: %s <- %s: re-created %d IK (%s), skipped %d, restored %d append (%s)'
          % (rig.name, src.name, len(created), ', '.join(created), len(skipped),
             len(restored), ', '.join(o for o, _t in restored)))
    return created, skipped, restored


if __name__ == '__main__':
    main()
