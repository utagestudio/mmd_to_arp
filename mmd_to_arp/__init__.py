# SPDX-License-Identifier: GPL-3.0-or-later
"""MMD to Auto-Rig Pro.

Converts MMD models imported with mmd_tools into Auto-Rig Pro rigs, using
Auto-Rig Pro: Quick Rig with skeleton-specific limb mappings.

Requires mmd_tools, Auto-Rig Pro and Auto-Rig Pro: Quick Rig.
"""

from . import operators, props, ui

_modules = (props, operators, ui)


def register():
    for m in _modules:
        m.register()


def unregister():
    for m in reversed(_modules):
        m.unregister()
