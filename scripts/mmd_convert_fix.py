"""Run after Quick Rig "Make Rig!" in Convert mode with an MMD_* preset.

Quick Rig (Convert) does not copy the constraints of orphan bones, so helper bones
that the MMD model drives with IK lose their motion -- e.g. detached sleeves that
hang from the shoulder and chase IK targets parented to the arm.

This script re-creates the MMD IK constraints on the converted rig when:
  - the IK owner and its target both exist in the rig as orphan bones (same name),
  - every bone of the IK chain is an orphan bone (no ARP bone is affected).
IK on mapped bones (足ＩＫ on ひざ...) is skipped: ARP drives those bones.

Usage: select the ARP rig, open this file in the Text Editor and Run Script.
It is safe to run several times (existing re-created IK is not duplicated).
"""
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


def main():
    rig, src = _find_rig_and_source()
    if rig is None or src is None:
        print('ARP rig or source MMD armature not found. Run Make Rig! (Convert) first.')
        return [], []
    created, skipped = fix(rig, src)
    print('mmd_convert_fix: %s <- %s: re-created %d IK (%s), skipped %d'
          % (rig.name, src.name, len(created), ', '.join(created), len(skipped)))
    return created, skipped


if __name__ == '__main__':
    main()
