# SPDX-License-Identifier: GPL-3.0-or-later
import bpy

from bpy.props import EnumProperty

from . import detect, fix_convert, fix_preserve, ikfk, mapping, quickrig


def is_arp_rig(obj):
    return obj is not None and obj.type == 'ARMATURE' and obj.data.bones.get('c_traj') is not None


def find_mmd_armature(obj):
    """MMD armature from the active object: the armature, a mesh it deforms, or the
    mmd_tools root empty (or anything else under that root)."""
    if obj is None:
        return None
    if obj.type == 'ARMATURE' and not is_arp_rig(obj):
        return obj
    if obj.type == 'MESH':
        arm = obj.find_armature()
        if arm is not None and not is_arp_rig(arm):
            return arm
    root = obj
    while root.parent is not None:
        root = root.parent
    for c in [root] + list(root.children_recursive):
        if c.type == 'ARMATURE' and not is_arp_rig(c):
            return c
    return None


def find_source_and_rig(context):
    """(MMD armature, ARP rig) of an already generated rig, from the active object."""
    obj = context.active_object
    if is_arp_rig(obj):
        _rig, src = fix_convert._find_rig_and_source()
        return src, obj
    src = find_mmd_armature(obj)
    if src is None:
        return None, None
    # Preserve: the MMD armature is constrained to the rig
    for pb in src.pose.bones:
        for c in pb.constraints:
            if c.name == 'CopyTransforms_QR' and is_arp_rig(c.target):
                return src, c.target
    # Convert: the rig shares the orphan bone names of the MMD armature
    names = {b.name for b in src.data.bones}
    best, score = None, 0
    for o in bpy.data.objects:
        if is_arp_rig(o):
            s = len(names & {b.name for b in o.data.bones})
            if s > score:
                best, score = o, s
    return src, best


def find_rig(obj):
    """ARP rig from the active object: the rig, a mesh it deforms (Convert) or the MMD
    armature constrained to it (Preserve). Cheap enough for panel drawing."""
    if obj is None:
        return None
    if is_arp_rig(obj):
        return obj
    if obj.type == 'MESH':
        arm = obj.find_armature()
        if is_arp_rig(arm):
            return arm
        obj = arm
    if obj is not None and obj.type == 'ARMATURE':
        for pb in obj.pose.bones:
            c = pb.constraints.get('CopyTransforms_QR')
            if c is not None and is_arp_rig(c.target):
                return c.target
    return None


def is_preserve_result(src):
    return any(c.name == 'CopyTransforms_QR' for pb in src.pose.bones for c in pb.constraints)


def run_post_fix(src, rig, preserve):
    # a baked animation keys the IK-FK switches: unkey them so the limbs can be switched
    unkeyed = ikfk.remove_switch_keys(rig)
    keys_msg = ', unkeyed %d IK-FK switches' % len(unkeyed) if unkeyed else ''
    if preserve:
        released, muted = fix_preserve.fix(src, rig)
        return ('released %d bones to MMD append / IK, muted %d MMD IK'
                % (len(released), len(muted)) + keys_msg)
    created, _skipped = fix_convert.fix(rig, src)
    restored = fix_convert.fix_append(rig, src)
    return 're-created %d MMD IK, restored %d MMD append' % (len(created), len(restored)) + keys_msg


def motion_action(arm):
    """The action (VMD motion) of the MMD armature, or None."""
    adt = arm.animation_data if arm else None
    return adt.action if adt else None


def _detect(settings, arm):
    convert, notes = detect.detect_preset_blender(arm)
    preserve, _pnotes = detect.detect_preset_blender(arm, preserve=True)
    settings.detected_target = arm.name
    settings.detected_convert = convert
    settings.detected_preserve = preserve
    settings.detected_notes = '\n'.join(notes)
    return convert, preserve, notes


def resolve_preset(settings, arm):
    """Preset name for the current mode: the user's choice, or the detected one."""
    if settings.preset != 'AUTO':
        return settings.preset
    convert, preserve, _notes = _detect(settings, arm)
    return preserve if settings.mode == 'PRESERVE' else convert


class _MMDTargetMixin:
    @classmethod
    def poll(cls, context):
        return find_mmd_armature(context.active_object) is not None


class MMDARP_OT_detect(_MMDTargetMixin, bpy.types.Operator):
    """Detect the Quick Rig presets matching the selected MMD model"""
    bl_idname = 'mmd_to_arp.detect'
    bl_label = 'Detect Preset'
    bl_options = {'REGISTER'}

    def execute(self, context):
        arm = find_mmd_armature(context.active_object)
        try:
            convert, preserve, notes = _detect(context.scene.mmd_to_arp, arm)
        except RuntimeError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        self.report({'INFO'}, 'Convert: %s / Preserve: %s' % (convert, preserve))
        for n in notes:
            self.report({'WARNING'}, n)
        return {'FINISHED'}


class MMDARP_OT_load_mapping(_MMDTargetMixin, bpy.types.Operator):
    """Load the limb mapping into Quick Rig without generating the rig.
Use it to review or edit the mapping in Quick Rig before "Make Rig!\""""
    bl_idname = 'mmd_to_arp.load_mapping'
    bl_label = 'Load Mapping to Quick Rig'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            quickrig.check_dependencies()
            arm = find_mmd_armature(context.active_object)
            name = resolve_preset(context.scene.mmd_to_arp, arm)
            quickrig.apply_mapping(context.scene, arm, mapping.get_preset(name))
            quickrig.fix_elbow_direction(context.scene, arm)
        except RuntimeError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        context.view_layer.objects.active = arm
        self.report({'INFO'}, 'Loaded %s into Quick Rig' % name)
        return {'FINISHED'}


class MMDARP_OT_convert(_MMDTargetMixin, bpy.types.Operator):
    """Generate the Auto-Rig Pro rig for the selected MMD model:
detect the preset, run Quick Rig "Make Rig!" and the MMD post-fix"""
    bl_idname = 'mmd_to_arp.convert'
    bl_label = 'Convert to Auto-Rig Pro'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.mmd_to_arp
        try:
            quickrig.check_dependencies()
            arm = find_mmd_armature(context.active_object)
            name = resolve_preset(settings, arm)
            skipped = quickrig.apply_mapping(context.scene, arm, mapping.get_preset(name))
            quickrig.fix_elbow_direction(context.scene, arm)
            preserve = settings.mode == 'PRESERVE'
            action = motion_action(arm) if settings.bake_motion else None
            options = {'arm_ik_fk': settings.arm_ik_fk, 'leg_ik_fk': settings.leg_ik_fk,
                       'orphan_bones_shape': quickrig.quickrig_orphan_shape(settings.orphan_shape)}
            if action:
                # retarget to the FK controls: the IK poles would not follow the MMD
                # knees / elbows. The limbs can be switched to IK anywhere afterwards
                # (the post-fix unkeys the IK-FK switches).
                options.update(animation='ANIM_BAKE', arm_ik_fk='FK', leg_ik_fk='FK')
            if preserve and not name.startswith('MMD_P_'):
                # Convert presets swap arm twist weights through weight overrides
                options['constrain_overrides'] = True
            rig = quickrig.make_rig(context, arm, 'PRESERVE' if preserve else 'CONVERT', **options)
            quickrig.set_orphan_shape(rig, settings.orphan_shape)
            fix_msg = run_post_fix(arm, rig, preserve)
            if action:
                fix_msg += ', baked motion %s (arms and legs in FK)' % action.name
        except RuntimeError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        for o in context.view_layer.objects:
            o.select_set(False)
        rig.select_set(True)
        context.view_layer.objects.active = rig
        self.report({'INFO'}, '%s: %s rig generated with %s (%d optional bones absent), %s'
                    % (arm.name, settings.mode.title(), name, len(skipped), fix_msg))
        if settings.detected_notes and settings.preset == 'AUTO':
            for n in settings.detected_notes.split('\n'):
                self.report({'WARNING'}, n)
        return {'FINISHED'}


class MMDARP_OT_post_fix(bpy.types.Operator):
    """Run the MMD post-fix on a rig generated with Quick Rig's own "Make Rig!".
Convert: re-create MMD IK and append (eyes following 両目...) of helper bones. Preserve: hand append / IK driven bones
back to MMD"""
    bl_idname = 'mmd_to_arp.post_fix'
    bl_label = 'Run Post-Fix'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return is_arp_rig(obj) or find_mmd_armature(obj) is not None

    def execute(self, context):
        src, rig = find_source_and_rig(context)
        if src is None or rig is None:
            self.report({'ERROR'}, 'Select a rig generated by Quick Rig from an MMD model')
            return {'CANCELLED'}
        preserve = is_preserve_result(src)
        msg = run_post_fix(src, rig, preserve)
        self.report({'INFO'}, '%s (%s): %s' % (rig.name, 'Preserve' if preserve else 'Convert', msg))
        return {'FINISHED'}


class MMDARP_OT_switch_ikfk(bpy.types.Operator):
    """Switch the limbs between IK and FK, keeping the current pose
(Auto-Rig Pro "Snap IK-FK"; keys are inserted when auto keying is on)"""
    bl_idname = 'mmd_to_arp.switch_ikfk'
    bl_label = 'Switch IK-FK'
    bl_options = {'REGISTER', 'UNDO'}

    limb: EnumProperty(name='Limb', items=(('ARM', 'Arm', ''), ('LEG', 'Leg', ''),
                                           ('ALL', 'All', 'Arms and legs')))
    side: EnumProperty(name='Side', items=(('.l', 'Left', ''), ('.r', 'Right', ''),
                                           ('BOTH', 'Both', '')), default='BOTH')
    target: EnumProperty(name='To', items=(('IK', 'IK', ''), ('FK', 'FK', '')))

    @classmethod
    def poll(cls, context):
        return find_rig(context.active_object) is not None

    def execute(self, context):
        rig = find_rig(context.active_object)
        limbs = ikfk.LIMBS if self.limb == 'ALL' else (self.limb,)
        sides = ikfk.SIDES if self.side == 'BOTH' else (self.side,)
        switched = []
        try:
            for limb in limbs:
                for side in sides:
                    if ikfk.switch(context, rig, limb, side, self.target):
                        switched.append(limb.title() + side.upper())
        except RuntimeError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        if switched:
            self.report({'INFO'}, '%s -> %s' % (', '.join(switched), self.target))
        return {'FINISHED'}


classes = (MMDARP_OT_detect, MMDARP_OT_load_mapping, MMDARP_OT_convert, MMDARP_OT_post_fix,
           MMDARP_OT_switch_ikfk)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
