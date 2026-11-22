# SPDX-License-Identifier: GPL-3.0-or-later
import textwrap

import bpy

from . import ikfk, quickrig
from .operators import find_mmd_armature, find_rig, is_arp_rig, motion_action, root_motion


def _wrapped(layout, text, icon='NONE', width=42):
    for i, line in enumerate(textwrap.wrap(text, width) or ['']):
        layout.label(text=line, icon=icon if i == 0 else 'BLANK1')


class MMDARP_PT_main(bpy.types.Panel):
    bl_label = 'MMD to Auto-Rig Pro'
    bl_idname = 'MMDARP_PT_main'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'MMD ARP'

    def draw(self, context):
        layout = self.layout
        missing = quickrig.missing_dependencies()
        if missing:
            box = layout.box()
            box.label(text='Required add-ons not enabled:', icon='ERROR')
            for m in missing:
                box.label(text=m, icon='BLANK1')
            return
        for name, installed, tested in quickrig.untested_versions():
            col = layout.column(align=True)
            col.scale_y = 0.8
            col.label(text='%s %s: untested' % (name, installed), icon='INFO')
            col.label(text='(tested with %s)' % tested, icon='BLANK1')

        job = root_motion['job']
        if job is not None:
            box = layout.box()
            box.label(text='Correcting the root motion', icon='TIME')
            box.progress(factor=job.index / max(job.total, 1),
                         text='Frame %d / %d' % (job.index, job.total))
            box.operator('mmd_to_arp.stop_root_motion', icon='CANCEL')
            return

        settings = context.scene.mmd_to_arp
        arm = find_mmd_armature(context.active_object)
        if arm is None:
            layout.label(text='Select an MMD model', icon='INFO')
            if is_arp_rig(context.active_object):
                layout.operator('mmd_to_arp.post_fix', icon='MODIFIER')
            return

        layout.label(text=arm.name, icon='ARMATURE_DATA')
        layout.row().prop(settings, 'mode', expand=True)
        layout.prop(settings, 'preset')
        row = layout.row(align=True)
        row.label(text='Arms')
        row.prop(settings, 'arm_ik_fk', expand=True)
        row = layout.row(align=True)
        row.label(text='Legs')
        row.prop(settings, 'leg_ik_fk', expand=True)
        layout.prop(settings, 'orphan_shape')
        action = motion_action(arm)
        if action:
            row = layout.row()
            row.prop(settings, 'bake_motion')
            row.label(text=action.name)

        box = layout.box()
        if settings.detected_target == arm.name:
            col = box.column(align=True)
            col.label(text='Convert:  ' + settings.detected_convert)
            col.label(text='Preserve: ' + settings.detected_preserve)
            for note in filter(None, settings.detected_notes.split('\n')):
                _wrapped(box, note, icon='ERROR')
            box.operator('mmd_to_arp.detect', text='Detect Again', icon='FILE_REFRESH')
        else:
            box.operator('mmd_to_arp.detect', icon='VIEWZOOM')

        row = layout.row()
        row.scale_y = 1.5
        row.operator('mmd_to_arp.convert', icon='OUTLINER_OB_ARMATURE')


class MMDARP_PT_advanced(bpy.types.Panel):
    bl_label = 'Step by Step'
    bl_idname = 'MMDARP_PT_advanced'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'MMD ARP'
    bl_parent_id = 'MMDARP_PT_main'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return not quickrig.missing_dependencies()

    def draw(self, context):
        col = self.layout.column()
        col.label(text='1. Load the mapping, edit it in Quick Rig')
        col.operator('mmd_to_arp.load_mapping', icon='IMPORT')
        col.label(text='2. Quick Rig "Make Rig!"')
        col.label(text='3. Run the MMD post-fix on the rig')
        col.operator('mmd_to_arp.post_fix', icon='MODIFIER')


class MMDARP_PT_ikfk(bpy.types.Panel):
    bl_label = 'IK / FK'
    bl_idname = 'MMDARP_PT_ikfk'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'MMD ARP'

    @classmethod
    def poll(cls, context):
        return find_rig(context.active_object) is not None

    @staticmethod
    def _buttons(layout, states, limb, side):
        row = layout.row(align=True)
        for target in ('IK', 'FK'):
            op = row.operator('mmd_to_arp.switch_ikfk', text=target,
                              depress=bool(states) and all(s == target for s in states))
            op.limb, op.side, op.target = limb, side, target

    def draw(self, context):
        rig = find_rig(context.active_object)
        layout = self.layout
        layout.label(text=rig.name, icon='OUTLINER_OB_ARMATURE')
        col = layout.column(align=True)
        everything = []
        for limb, label in (('ARM', 'Arm'), ('LEG', 'Leg')):
            for side in ikfk.SIDES:
                st = ikfk.state(rig, limb, side)
                if st is None:
                    continue
                everything.append(st)
                split = col.split(factor=0.35, align=True)
                split.label(text='%s %s' % (label, side[1].upper()))
                self._buttons(split, [st], limb, side)
        if everything:
            col.separator()
            split = col.split(factor=0.35, align=True)
            split.label(text='All')
            self._buttons(split, everything, 'ALL', 'BOTH')
        else:
            layout.label(text='No IK-FK limbs', icon='INFO')


classes = (MMDARP_PT_main, MMDARP_PT_advanced, MMDARP_PT_ikfk)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
