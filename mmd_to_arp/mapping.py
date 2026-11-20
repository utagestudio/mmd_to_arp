# SPDX-License-Identifier: GPL-3.0-or-later
"""Quick Rig limb mappings for MMD skeletons imported with mmd_tools.

Bone names assume mmd_tools' default import ("Rename bones - L / R suffix" ON),
e.g. "左腕" -> "腕.L".

Pure Python (no bpy): also used by tools/make_presets.py to write preset files.

- Convert-mode presets (MMD_*): skeleton is replaced by ARP and weights are moved.
- Preserve-mode presets (MMD_P_*): ARP only drives the MMD operation bones.
"""
# Spine variants: list of bones after the root (下半身)
SPINES = {
    'std': ['上半身', '上半身2'],             # 上半身 > 上半身2  (most models)
    'spine3': ['上半身', '上半身2', '上半身3'],  # 上半身 > 上半身2 > 上半身3
    'spine1': ['上半身', '上半身1', '上半身2'],  # 上半身 > 上半身1 > 上半身2
    'nospine2': ['上半身'],                   # 上半身 only (old PMD)
}

# Thumb variants: first thumb bone
THUMBS = {
    '': '親指０',      # 親指０ > 親指１ > 親指２ (standard PMX)
    '_nothumb0': '親指１',  # 親指１ > 親指２ (old models without 親指０)
}


def base_limb(name, ltype, side):
    return {
        'name': name, 'type': ltype, 'side': side,
        'bone_01': '', 'bone_02': '', 'bone_03': '', 'bone_04': '',
        'bone_05': '', 'bone_06': '', 'bone_07': '',
        'bone_twist_02_01': '', 'bone_twist_02_02': '',
        'bone_twist_03_01': '', 'bone_twist_03_02': '',
        'bone_twist_04_01': '', 'bone_twist_04_02': '',
        'override_bone_01': '', 'override_bone_02': '', 'override_bone_03': '',
        'override_bone_04': '', 'override_bone_05': '', 'override_bone_06': '',
        'override_bone_07': '', 'override_upper_thigh': '', 'upper_thigh': '',
        'weights_override': False,
        'thumb': '', 'index': '', 'middle': '', 'ring': '', 'pinky': '',
        'fingers': 'NONE', 'manual_phalanges': False,
        'connect': True, 'connect_foot_to_calf': False,
        'force_up_axis': True, 'force_z_axis': True,
        'primary_axis': 'Y', 'primary_axis_auto': True,
        'up_axis': 'X', 'up_axis_arm': 'DEFAULT',
        'auto_knee': True, 'auto_elbow': False, 'auto_ik_roll': False,
        'leg_type': '2', 'IK_axis_correc': 'Y',
        'twist_bones_amount': 1, 'spine_amount': 4, 'neck_bones_amount': 1,
        'pelvis_up': False, 'straight_head': True, 'foot_dir_axis': 'Y',
        'toes_parent_foot': False,
    }


def make_preset(spine_bones, thumb, d_bones=False, arm_extra=None, leg_extra=None):
    p = {}

    s = base_limb('Spine.x', 'SPINE', 'CENTER')
    chain = ['下半身'] + spine_bones
    for i, b in enumerate(chain):
        s['bone_%02d' % (i + 1)] = b
    s['spine_amount'] = len(chain)
    s['pelvis_up'] = True  # 下半身 points downward in MMD
    p['Spine.x'] = s

    h = base_limb('Head.x', 'HEAD', 'CENTER')
    h['bone_01'] = '首'
    h['bone_02'] = '頭'
    h['neck_bones_amount'] = 1
    p['Head.x'] = h

    for side, sfx in (('LEFT', 'L'), ('RIGHT', 'R')):
        a = base_limb('Arm.' + sfx.lower(), 'ARM', side)
        a.update({
            'bone_01': '肩.' + sfx,
            'bone_02': '腕.' + sfx,
            'bone_03': '腕捩.' + sfx,
            'bone_04': 'ひじ.' + sfx,
            'bone_05': '手捩.' + sfx,
            'bone_06': '手首.' + sfx,
            'fingers': '3',
            'thumb': thumb + '.' + sfx,
            'index': '人指１.' + sfx,
            'middle': '中指１.' + sfx,
            'ring': '薬指１.' + sfx,
            'pinky': '小指１.' + sfx,
            # --- twist ---
            # ARP upper arm : c_arm_twist_offset = 0% twist, arm_twist_2/3/4 = 25/50/75%,
            #                 arm_stretch = 100%
            # ARP forearm   : forearm_stretch = 0%, forearm_twist_2/3/4 = 75/50/25%,
            #                 forearm_twist = 100%
            # MMD           : 腕 = 0%, 腕捩1/2/3 = 25/50/75%, 腕捩 = 100%
            #                 ひじ = 0%, 手捩1/2/3 = 25/50/75%, 手捩 = 100%
            # -> upper arm: swap weights of 腕 and 腕捩 with weights override,
            #    forearm: map 手捩3/2/1 in reverse order.
            # Missing names (old models without semi-standard bones) are left empty.
            'weights_override': True,
            'override_bone_02': '腕捩.' + sfx,   # 腕捩 weights -> arm_stretch (100%)
            'override_bone_03': '腕.' + sfx,     # 腕 weights   -> arm twist (0%)
            'bone_twist_02_01': '腕捩1.' + sfx,
            'bone_twist_03_01': '腕捩2.' + sfx,
            'bone_twist_04_01': '腕捩3.' + sfx,
            'bone_twist_02_02': '手捩3.' + sfx,
            'bone_twist_03_02': '手捩2.' + sfx,
            'bone_twist_04_02': '手捩1.' + sfx,
            'twist_bones_amount': 4,
            # mmd_tools: left arm bones have Z up, right arm bones have X up
            'up_axis': 'Z' if sfx == 'L' else 'X',
            'up_axis_arm': 'DEFAULT',
        })
        if arm_extra:
            a.update({k: (v + '.' + sfx if v else '') for k, v in arm_extra.items()})
        p['Arm.' + sfx.lower()] = a

        l = base_limb('Leg.' + sfx.lower(), 'LEG', side)
        l.update({
            'bone_01': '足.' + sfx,
            'bone_03': 'ひざ.' + sfx,
            'bone_05': '足首.' + sfx,
            'bone_06': '足先EX.' + sfx,   # optional, missing -> foot direction from 足首
            'twist_bones_amount': 1,
            'up_axis': 'Z',
            'foot_dir_axis': 'Y',          # 足首 points to the toe
        })
        if d_bones:
            # Semi-standard D bones carry the leg weights. They are mapped as the main
            # bones (not as weight overrides) so that their children (toe fingers,
            # accessories...) get parented to the ARP leg bones.
            # D bones point straight up, their local Z axis points forward.
            l.update({
                'bone_01': '足D.' + sfx,
                'bone_03': 'ひざD.' + sfx,
                'bone_05': '足首D.' + sfx,
                'foot_dir_axis': 'Z',
            })
            if d_bones == 'ankle':  # 足D / ひざD only, regular 足首
                l.update({'bone_05': '足首.' + sfx, 'foot_dir_axis': 'Y'})
            elif d_bones == 'empty':
                # D bones exist (and hold children) but the weights are on 足/ひざ/足首
                l.update({
                    'weights_override': True,
                    'override_bone_01': '足.' + sfx,
                    'override_bone_03': 'ひざ.' + sfx,
                    'override_bone_05': '足首.' + sfx,
                })
        if leg_extra:
            l.update({k: (v + '.' + sfx if v else '') for k, v in leg_extra.items()})
        p['Leg.' + sfx.lower()] = l
    return p


def make_preset_preserve(spine_bones, thumb, wrist='手首'):
    """Preset for Quick Rig *Preserve* mode.

    Only the MMD "operation" bones (the ones VMD motions key) are driven by ARP.
    Everything behind them -- D bones, 腕捩1-3 / 手捩1-3, 腰キャンセル, helper bones --
    keeps following through the model's own append (付与) / IK constraints that
    mmd_tools sets up. No weights override is used, so "Constrain Overrides" is
    not needed.
    """
    p = make_preset(spine_bones, thumb)
    for sfx in ('L', 'R'):
        a = p['Arm.' + sfx.lower()]
        for k in list(a):
            if k.startswith('bone_twist_') or k.startswith('override_bone_'):
                a[k] = ''
        a.update({
            'weights_override': False,
            'bone_03': '',               # 腕捩 not driven: upper arm twists with 腕 like in MMD
            'bone_05': '手捩.' + sfx,     # ARP forearm_twist (100% hand twist) -> 手捩,
                                         # 手捩1-3 follow it through MMD append
            'bone_06': wrist + '.' + sfx,
            'twist_bones_amount': 1,
        })
    return p


def _build_registry():
    reg = {}
    for sname, spine in SPINES.items():
        for tname, thumb in THUMBS.items():
            for dname, d_bones in (('', False), ('_D', True)):
                reg['MMD_%s%s%s' % (sname, tname, dname)] = (
                    lambda sp=spine, th=thumb, d=d_bones: make_preset(sp, th, d))

    # Model specific presets ------------------------------------------------
    # spine is 上半身1- > 上半身2- (上半身 is an unused sibling),
    # forearm twist uses 手捩1-5 and 手首 is parented to 手捩5.
    reg['MMD_spine1m'] = lambda: make_preset(['上半身1-', '上半身2-'], '親指１', arm_extra={
        'bone_05': '手捩5',
        'bone_twist_02_02': '手捩4',
        'bone_twist_03_02': '手捩3',
        'bone_twist_04_02': '手捩2',
    })
    # wrist bone named 手 instead of 手首
    reg['MMD_std_hand'] = lambda: make_preset(SPINES['std'], '親指０', arm_extra={'bone_06': '手'})
    # 足D / ひざD exist but no 足首D
    reg['MMD_std_D_ankle'] = lambda: make_preset(SPINES['std'], '親指０', d_bones='ankle')
    # D bones exist without weights, toe bone 足首EX is a child of 足首D
    reg['MMD_std_Dempty'] = lambda: make_preset(SPINES['std'], '親指０', d_bones='empty',
                                                leg_extra={'bone_06': '足首EX'})

    # Preserve-mode presets (prefix MMD_P_) ----------------------------------
    for sname, spine in SPINES.items():
        for tname, thumb in THUMBS.items():
            reg['MMD_P_%s%s' % (sname, tname)] = (
                lambda sp=spine, th=thumb: make_preset_preserve(sp, th))
    reg['MMD_P_spine1m'] = lambda: make_preset_preserve(['上半身1-', '上半身2-'], '親指１')
    reg['MMD_P_std_hand'] = lambda: make_preset_preserve(SPINES['std'], '親指０', wrist='手')
    return reg


PRESETS = _build_registry()


def preset_names(preserve=None):
    """All preset names; preserve=True/False filters Preserve (MMD_P_*) / Convert ones."""
    names = list(PRESETS)
    if preserve is not None:
        names = [n for n in names if n.startswith('MMD_P_') == preserve]
    return names


def get_preset(name):
    """Limb mapping dict for a preset name (same content as the preset file)."""
    return PRESETS[name]()
