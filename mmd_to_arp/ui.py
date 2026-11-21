# SPDX-License-Identifier: GPL-3.0-or-later
import textwrap

import bpy

from . import quickrig
from .operators import find_mmd_armature, is_arp_rig


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


classes = (MMDARP_PT_main, MMDARP_PT_advanced)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
