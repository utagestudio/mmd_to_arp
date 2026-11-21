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
    constraints). Append on mapped bones (腕捩1 <- 腕捩...) is skipped, and so is append
    from bones moved by MMD IK.

Used by the addon; also runs standalone: select the ARP rig, open this file in
the Text Editor and Run Script.
It is safe to run several times (existing re-created IK is not duplicated).
"""
import sys

import bpy

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


def _ik_chain_bones(arm):
    """Names of the bones moved by enabled IK constraints of `arm`."""
    names = set()
    for pb in arm.pose.bones:
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


def fix_append(rig, src):
    """Restore MMD append on orphan bones. Returns [(owner, target)] restored."""
    fn = _mmd_fnbone()
    if fn is None or not hasattr(bpy.types.PoseBone, 'mmd_bone'):
        return []
    # append owner -> target, for owners and targets that are orphan bones of the rig
    pairs = {}
    for spb in src.pose.bones:
        mb = spb.mmd_bone
        if spb.is_mmd_shadow_bone or not (mb.has_additional_rotation or mb.has_additional_location):
            continue
        target = mb.additional_transform_bone
        if target and spb.name in rig.pose.bones and target in rig.pose.bones:
            pairs[spb.name] = target
    # a target moved by MMD IK (even re-created, it solves against ARP bones) or by an
    # append that is not restored moves differently in the rig: skip such appends
    lost = _ik_chain_bones(src)
    lost |= {b.name for b in src.pose.bones if not b.is_mmd_shadow_bone and b.name not in pairs
             and (b.mmd_bone.has_additional_rotation or b.mmd_bone.has_additional_location)
             and b.mmd_bone.additional_transform_bone}
    changed = True
    while changed:
        changed = False
        for owner, target in list(pairs.items()):
            if target in lost:
                del pairs[owner]
                lost.add(owner)
                changed = True
    restored = []
    for spb in src.pose.bones:
        if spb.name not in pairs:
            continue
        mb = spb.mmd_bone
        target = pairs[spb.name]
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
