# SPDX-License-Identifier: GPL-3.0-or-later
"""Scene settings of the add-on (bpy.types.Scene.mmd_to_arp)."""
import bpy
from bpy.props import EnumProperty, PointerProperty, StringProperty

from . import mapping

MODE_ITEMS = (
    ('CONVERT', 'Convert',
     'Replace the MMD skeleton with the Auto-Rig Pro rig and move the weights.\n'
     'Full Auto-Rig Pro features (export, retargeting...)'),
    ('PRESERVE', 'Preserve',
     'Keep the MMD skeleton and its append / IK helper bones; Auto-Rig Pro only\n'
     'drives the MMD operation bones. Best for models with many helper bones'),
)

IKFK_ITEMS = (('IK', 'IK', 'Inverse kinematics'), ('FK', 'FK', 'Forward kinematics'))

_preset_items_cache = []


def _preset_items(self, context):
    items = [('AUTO', 'Auto', 'Use the detected preset')]
    preserve = self.mode == 'PRESERVE'
    for i, name in enumerate(mapping.preset_names(preserve=preserve), start=1):
        items.append((name, name, '', i))
    # keep a reference: Blender requires the strings to stay alive
    _preset_items_cache[:] = items
    return _preset_items_cache


class MMDARP_Settings(bpy.types.PropertyGroup):
    mode: EnumProperty(name='Mode', items=MODE_ITEMS, default='CONVERT')
    preset: EnumProperty(name='Preset', items=_preset_items,
                         description='Quick Rig limb mapping to use')

    arm_ik_fk: EnumProperty(name='Arms', items=IKFK_ITEMS, default='FK',
                            description='IK-FK state of the arms in the generated rig')
    leg_ik_fk: EnumProperty(name='Legs', items=IKFK_ITEMS, default='IK',
                            description='IK-FK state of the legs in the generated rig')

    # cached result of the Detect operator
    detected_target: StringProperty(name='Detected armature', default='')
    detected_convert: StringProperty(name='Convert preset', default='')
    detected_preserve: StringProperty(name='Preserve preset', default='')
    detected_notes: StringProperty(name='Notes', default='')


classes = (MMDARP_Settings,)


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.mmd_to_arp = PointerProperty(type=MMDARP_Settings)


def unregister():
    del bpy.types.Scene.mmd_to_arp
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
