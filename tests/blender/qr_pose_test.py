"""Test poses and twist measurement for a generated ARP rig (run inside Blender).

pose_test()     arms/elbows/fingers, left IK foot forward, spine and head.
twist_test()    twist the left arm / hand FK controls around their own axis.
twist_profile() rotation angle of the mesh around a limb axis, binned along it.
"""
import math

import bpy
from mathutils import Euler, Vector


def twist_test(rig_name='rig', arm_twist=0, hand_twist=0):
    """Twist the left arm FK controls around their own (Y) axis."""
    rig = bpy.data.objects[rig_name]
    pb = rig.pose.bones
    for b in pb:
        b.location = (0, 0, 0)
        b.rotation_quaternion = (1, 0, 0, 0)
        b.rotation_euler = (0, 0, 0)
    for name, ang in (('c_arm_fk.l', arm_twist), ('c_hand_fk.l', hand_twist)):
        b = pb[name]
        e = Euler((0, math.radians(ang), 0))
        if b.rotation_mode == 'QUATERNION':
            b.rotation_quaternion = e.to_quaternion()
        else:
            b.rotation_euler = e
    bpy.context.view_layer.update()


def _eval_coords(mesh_obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = mesh_obj.evaluated_get(dg)
    me = ev.to_mesh()
    co = [mesh_obj.matrix_world @ v.co for v in me.vertices]
    ev.to_mesh_clear()
    return co


def twist_profile(mesh_obj, start, end, radius, arm_twist=0, hand_twist=0, bins=8,
                  rig_name='rig', groups_prefix=None):
    """Rotation angle (deg) of vertices around the start->end axis, binned along the axis.

    groups_prefix: only use vertices whose weights are >= 90% in vertex groups starting
    with one of these prefixes (e.g. ('forearm', 'hand.l')).
    """
    allowed = None
    if groups_prefix:
        gi = {g.index: g.name for g in mesh_obj.vertex_groups}
        allowed = set()
        for v in mesh_obj.data.vertices:
            tot = sum(g.weight for g in v.groups if not gi[g.group].startswith('mmd_'))
            ok = sum(g.weight for g in v.groups if gi[g.group].startswith(groups_prefix))
            if tot > 0 and ok / tot >= 0.9:
                allowed.add(v.index)
    twist_test(rig_name)  # rest
    rest = _eval_coords(mesh_obj)
    twist_test(rig_name, arm_twist=arm_twist, hand_twist=hand_twist)
    posed = _eval_coords(mesh_obj)
    twist_test(rig_name)
    axis = (end - start)
    L = axis.length
    axis.normalize()
    acc = [[] for _ in range(bins)]
    for i, (a, b) in enumerate(zip(rest, posed)):
        if allowed is not None and i not in allowed:
            continue
        t = (a - start).dot(axis)
        if t < 0 or t > L:
            continue
        ra = (a - start) - axis * t
        if ra.length > radius or ra.length < 1e-4:
            continue
        tb = (b - start).dot(axis)
        rb = (b - start) - axis * tb
        if rb.length < 1e-4:
            continue
        ang = math.degrees(math.atan2(ra.cross(rb).dot(axis), ra.dot(rb)))
        acc[min(bins - 1, int(t / L * bins))].append(ang)
    return [round(sum(x) / len(x), 1) if x else None for x in acc]


def pose_test(rig_name='rig', reset=False):
    rig = bpy.data.objects[rig_name]
    pb = rig.pose.bones
    for b in pb:
        b.location = (0, 0, 0)
        b.rotation_quaternion = (1, 0, 0, 0)
        b.rotation_euler = (0, 0, 0)
    if reset:
        bpy.context.view_layer.update()
        return

    def rot(name, x=0, y=0, z=0):
        b = pb.get(name)
        if b is None:
            print('missing ctrl', name)
            return
        e = Euler((math.radians(x), math.radians(y), math.radians(z)))
        if b.rotation_mode == 'QUATERNION':
            b.rotation_quaternion = e.to_quaternion()
        else:
            b.rotation_euler = e

    # arms down (FK), bend elbows, curl fingers
    rot('c_arm_fk.l', z=-45)
    rot('c_arm_fk.r', z=45)
    rot('c_forearm_fk.l', z=-60)
    rot('c_forearm_fk.r', z=60)
    for f in ('index', 'middle', 'ring', 'pinky'):
        for i in (1, 2, 3):
            rot('c_%s%d.l' % (f, i), x=40)
            rot('c_%s%d.r' % (f, i), x=40)
    # left leg: raise IK foot forward
    b = pb.get('c_foot_ik.l')
    if b:
        b.location = Vector((0, 0.15, 0.0))
    rot('c_spine_01.x', x=15)
    rot('c_head.x', z=25)
    bpy.context.view_layer.update()
