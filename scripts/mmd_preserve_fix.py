"""Run after Quick Rig "Make Rig!" in Preserve mode with an MMD_P_* preset.

Quick Rig (Preserve) constrains *every* bone of the source skeleton to the ARP rig,
including bones that mmd_tools drives with MMD append (付与) / IK: D bones,
腕捩1-3 / 手捩1-3, helper bones and the internal _shadow_ / _dummy_ bones.
This script removes the Quick Rig constraints from those bones (and from their
descendants, until a bone mapped in the preset is reached), so they keep moving
through the model's own mechanisms -- the same way a VMD motion drives a model.
It first mutes the MMD IK whose chain contains a mapped bone (足ＩＫ / つま先ＩＫ,
hair IK reaching 頭...), since ARP now drives those bones.

Bones hanging under mapped bones without any MMD mechanism (hair, skirt...) keep
their Quick Rig constraints, so they can still be posed with the ARP controllers.

Usage: select the ARP rig or the MMD armature, open this file in the Text Editor
and Run Script. It is safe to run several times.
"""
import bpy

QR_CNS = ('CopyTransforms_QR', 'CopyScale_QR')


def _find_pair():
    obj = bpy.context.active_object
    cands = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    if obj and obj.type != 'ARMATURE':
        obj = next((c for c in obj.children_recursive if c.type == 'ARMATURE'), obj)
    # the MMD armature is the one carrying CopyTransforms_QR constraints
    src = None
    if obj and obj.type == 'ARMATURE' and any(
            c.name == 'CopyTransforms_QR' for pb in obj.pose.bones for c in pb.constraints):
        src = obj
    if src is None:
        for o in cands:
            for pb in o.pose.bones:
                for c in pb.constraints:
                    if c.name == 'CopyTransforms_QR' and (obj is None or c.target == obj):
                        src = o
                        break
                if src:
                    break
            if src:
                break
    if src is None:
        return None, None
    rig = next(c.target for pb in src.pose.bones for c in pb.constraints
               if c.name == 'CopyTransforms_QR')
    return src, rig


def _mmd_driven(pb):
    if pb.name.startswith(('_dummy_', '_shadow_')):
        return True
    for c in pb.constraints:
        if c.name in QR_CNS or c.mute:
            continue
        if c.type == 'IK' or c.name.startswith('mmd_'):
            return True
    return False


def fix(src, rig):
    # mapped bones: Quick Rig created a "<name>_qr_offset" helper for them
    mapped = {pb.name for pb in src.pose.bones if rig.data.bones.get(pb.name + '_qr_offset')}

    # 1) MMD IK whose chain contains a mapped bone (足ＩＫ on ひざ/足, つま先ＩＫ on 足首,
    #    long hair IK chains reaching 頭...) would pull ARP-driven bones away: mute it.
    #    IK chains made only of helper bones (e.g. arm helper bones) stay active.
    muted = []
    for pb in src.pose.bones:
        for c in pb.constraints:
            if c.type != 'IK' or c.mute:
                continue
            chain, b, n = [], pb, c.chain_count or 255
            while b and n > 0:
                chain.append(b.name)
                b, n = b.parent, n - 1
            if any(x in mapped for x in chain):
                c.mute = True
                muted.append(pb.name)

    # 2) release bones still driven by MMD append / IK (and their descendants)
    released = []

    def walk(pb, inherited):
        rel = False
        if pb.name not in mapped:
            rel = inherited or _mmd_driven(pb)
        if rel:
            n = 0
            for c in list(pb.constraints):
                if c.name in QR_CNS:
                    pb.constraints.remove(c)
                    n += 1
            if n:
                released.append(pb.name)
        for ch in pb.children:
            walk(ch, rel)

    for pb in src.pose.bones:
        if pb.parent is None:
            walk(pb, False)
    return released, muted


def main():
    src, rig = _find_pair()
    if src is None:
        print('No Quick Rig (Preserve) constraints found. Run Make Rig! in Preserve mode first.')
        return []
    released, muted = fix(src, rig)
    print('mmd_preserve_fix: %s: released %d bones to MMD append / IK, muted %d MMD IK (%s)'
          % (src.name, len(released), len(muted), ', '.join(muted)))
    return released, muted


if __name__ == '__main__':
    main()
