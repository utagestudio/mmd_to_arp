# MMD to Auto-Rig Pro

English | [日本語](README.ja.md) | Website: https://mmd-to-arp.utage.studio/

A Blender add-on that converts MMD models into Auto-Rig Pro rigs.

- It works on MMD models (PMX / PMD) imported with mmd_tools.
- Auto-Rig Pro: Quick Rig does the conversion itself.
- This add-on picks the limb mapping that fits the skeleton of the model.
- After the conversion, it also fixes the MMD-specific mechanisms: helper bones driven by "append" (付与) or by IK.
- The bone structures of 241 distributed models were analyzed. For each structure pattern, the conversion was checked on 36 representative models.

**Check the terms of use of the model.** Even if the add-on can convert a model, whether you may use it in Blender, modify it or publish what you make is decided by the terms of use of each model and motion. Some models do not allow use outside MMD or modification. Check the terms and use the model within them.

## Requirements

| Software | Tested version |
|---|---|
| Blender 4.5 or later | 4.5, 5.3 |
| [mmd_tools](https://extensions.blender.org/add-ons/mmd-tools/) | Extension version |
| [Auto-Rig Pro](https://lucky3d.fr/auto-rig-pro/) (paid) | 3.79 |
| Auto-Rig Pro: Quick Rig (paid) | 1.28 |

- Install and enable the three add-ons above.
- Other versions of Auto-Rig Pro and Quick Rig may also work. In that case, the panel shows a small note.

## Installation

### Add the repository (recommended, updates automatically)

1. In Blender, open "Edit > Preferences > Get Extensions".
2. In "Repositories" at the top right, press "+" and choose "Add Remote Repository".
3. Enter this URL: `https://mmd-to-arp.utage.studio/repository/index.json`
4. Search for "MMD to Auto-Rig Pro" and press "Install".

New versions then appear as updates in Blender.

### Install the zip

1. Download the zip file (`mmd_to_arp-<version>.zip`) from [Releases](https://github.com/utagestudio/mmd_to_arp/releases). Do not unzip it.
2. In Blender, open "Edit > Preferences > Get Extensions".
3. In the menu at the top right, choose "Install from Disk" and select the zip file.
   - You can also drag and drop the zip file onto the Blender window.

## Usage

1. Import a PMX / PMD file with mmd_tools.
   - Keep "Rename Bones - L / R Suffix" enabled. This is the default.
   - Do not use "Use Underscore" or the dictionary translation to English.
2. Select the model. The root, the armature or a mesh are all fine.
3. Open the "**MMD ARP**" tab in the sidebar of the 3D Viewport.
4. Choose the **Mode**. If you are not sure, choose Convert.
5. Press "**Detect Preset**" to see the detected preset and notes. This step is optional.
6. Press "**Convert to Auto-Rig Pro**". It sets the mapping, runs Quick Rig's Make Rig, and fixes the result.

### Mode

| Mode | What it does | Use it when |
|---|---|---|
| Convert | Replaces the MMD skeleton with the Auto-Rig Pro skeleton. The weights move to the Auto-Rig Pro bones. | You want all Auto-Rig Pro features, such as export to game engines or retargeting. |
| Preserve | Keeps the MMD skeleton, append and helper bones. Auto-Rig Pro only drives the MMD operation bones, like a VMD motion does. | The model has many helper bones and you want its original deformation. |

### Options

- **Preset**: When set to anything other than "Auto", the chosen mapping is used instead of the detected one.
- **Arms / Legs**: Whether the arms and legs of the generated rig start in IK or FK. The default is the same as Quick Rig: arms in FK, legs in IK.
- **Other Bones**: The controller shape of the bones other than the arms, legs and body, such as hair, skirts and accessories.
  - **Line** (default): A line along each bone. It shows how the bones are connected.
  - **Sphere** / **Box**: The standard sphere and box of Quick Rig.
- **Bake Motion**: Shown when the MMD armature has a motion (VMD).
  - The motion is baked to the FK controls of the arms and legs.
  - The IK-FK switches are not keyed. You can switch to IK anywhere in the motion.
  - After the bake, the root motion is corrected frame by frame. The sidebar shows the progress. A motion of a few thousand frames takes about one minute.
  - Press Esc or "Stop" to stop the correction. The frames corrected so far are kept. Undo (Ctrl+Z) goes back to the rig before the correction, and once more to before Convert.

## Switching IK / FK

When you select the rig, the "**IK / FK**" panel appears in the sidebar. It also appears when you select a mesh deformed by the rig.

- Switch each arm and leg between IK and FK. "All" switches all of them at once.
- You do not need to select any bone.
- It works like the "Snap IK-FK" of Auto-Rig Pro. The pose is kept when switching.
- When auto keying is on, keys are inserted.

### Rigs with a baked motion

- Switch to IK to place a hand or a foot anywhere. The VMD motion no longer moves that arm or leg.
- Switch back to FK to return to the VMD motion.
- When auto keying is on, the IK-FK switch is keyed with constant interpolation. IK and FK are not blended between two keys.
  - Example: switch to IK at frame 100 and back to FK at frame 150. Only frames 100 to 149 are in IK.
  - Frames before the first key use the value of the first key. To keep the earlier frames in FK, also switch to FK at an earlier frame.

### Note

The FK elbows and knees are locked so that they bend only around the Z axis. A pose bent around another axis (with the locks removed) cannot be reproduced in IK. Switching changes the twist of the arm in that case.

## IK direction of the arms

Quick Rig places the IK pole of the elbow from the roll of the arm bone. Because of this, the arms of some MMD models bend the wrong way in IK. This happens when the arm is almost straight in the rest pose, or when the elbow is bent slightly forward.

This add-on finds the arms whose elbow is not clearly bent backward. For those arms, it enables Quick Rig's "Auto-Elbow Direction" (Force Straight Direction) before the conversion. The elbow joint then moves onto the line between the shoulder and the wrist. It usually moves a few millimeters. The largest move in the tested models was about 1 cm.

## Using other motions (Auto-Rig Pro Remap)

The converted model is an Auto-Rig Pro rig. You can apply motions made for other skeletons, such as Mixamo FBX files or BVH motion capture, with the Remap feature of Auto-Rig Pro.

- Checked with a Convert rig and a Mixamo motion.

MMD models stand in an A-pose: the upper arms point about 40° down. Many motions, such as Mixamo motions, are made for a T-pose. Match the rest pose of the motion to the rig first. Otherwise the arms turn too far, and the hands go behind the back.

1. Open the Remap panel of Auto-Rig Pro. Set the armature with the motion as the source and the rig as the target.
2. Click "Build Bones List".
3. In "Mapping Presets", import a preset for the source. For Mixamo, use the Mixamo preset with FK arms and legs.
4. Click "Redefine Rest Pose".
5. Select the arm bones of the source (upper arm, forearm and hand).
6. Click "Copy Selected Bones Rotation". The selected bones point in the same direction as the bones of the rig.
7. Click "Apply".
8. Click "Re-Target".

If the legs also point in different directions, match them in steps 5 and 6 too.

## Running the steps separately

The "Step by Step" section of the sidebar runs each step on its own.

1. **Load Mapping to Quick Rig**: Loads the mapping into Quick Rig. You can check and edit it in the Quick Rig panel.
2. Run "Make Rig!" of Quick Rig.
3. Select the generated rig and press **Run Post-Fix**. It detects whether the rig was made in Convert or Preserve mode.

## What the post-fix does

### Convert

Quick Rig does not copy the constraints of the bones that are not mapped. The MMD bones moved by IK or append stop moving. This add-on restores two things on the rig.

- **IK**: Re-creates the IK of helper bones that follow the arms, such as sleeves.
- **Append**: Re-creates append, such as the eyes following the "両目" bone, highlights and "肩C". It uses the same mechanism as mmd_tools.
  - Thigh helper bones that take the thigh swing through an IK helper and append (such as 膝捩) work too: both the IK and the append are re-created.
- **Motion**: When a motion is baked, the bones moved by IK or append get the original VMD keys. The baked final pose already includes the IK and append, so it would apply them twice.

### Preserve

Quick Rig constrains every bone of the original skeleton to Auto-Rig Pro. This overrides the append of the D bones and twist bones. This add-on fixes it as follows.

- Mutes the MMD IK that contains mapped bones, such as 足ＩＫ and つま先ＩＫ.
- Removes the Quick Rig constraints from the bones moved by append or IK. These bones move by the original mechanism of the model.
- Bones that simply hang, such as hair and skirts, stay controllable with Auto-Rig Pro controllers.

### Both modes

For rigs with a baked motion, the keys of the IK-FK switches are removed. This also applies to motions baked with Quick Rig's own Make Rig.

## FAQ and troubleshooting

**The panel says "Required add-ons not enabled"**
- Enable the add-ons listed there (mmd_tools, Auto-Rig Pro, Auto-Rig Pro: Quick Rig).

**The panel says "untested"**
- The installed Auto-Rig Pro or Quick Rig version has not been tested with this add-on.
- It often works anyway. If the conversion fails, compare with the tested versions (see "Requirements").

**The detected preset is wrong, or the arms or legs are misplaced**
- Check the import settings of mmd_tools. "Rename Bones - L / R Suffix" must be enabled. "Use Underscore" and the translation to English must be disabled.
- Choose another preset in **Preset** and convert again.
- You can also load the mapping with **Load Mapping to Quick Rig** ("Step by Step") and fix the bone assignment in the Quick Rig panel.

**After the conversion, some meshes (sleeves, decorations, parts moved by helper bones) do not move correctly**
- Convert again in **Preserve** mode. Preserve keeps the helper bone mechanisms of the model.
- Models detected with "helper-bone system that mmd_tools cannot reproduce" do not deform correctly in either mode.

**The arms bend the wrong way in IK**
- Rigs converted with a version older than 0.2.0 can have this problem. Convert again with the latest version.
- If it still happens, move the IK pole of the elbow (c_arms_pole).

**I want to redo the conversion**
- Press Ctrl+Z to go back to before the conversion. If that does not work well, import the model again.

**"Bake Motion" is not shown**
- The MMD armature has no motion. Select the model, import the motion (VMD) with mmd_tools, then convert.

**On a rig with a baked motion, the limbs go back to the motion when switched to FK**
- This is expected. The baked motion is on the FK controls. Switch to IK only where you want to move the limbs freely (see "Switching IK / FK").

**The rig broke after enabling "Copy Constraints" in Make Rig**
- "Copy Constraints" breaks the internal bones of mmd_tools. Keep it disabled. The post-fix restores the MMD IK and append.

## Limitations

- If the append parent is a twist bone (腕捩, 手捩...), Convert loses that append. The helper bone only follows its parent bone, because MMD and Auto-Rig Pro split the twist differently. Use Preserve if this matters. Append from the other mapped bones, such as the arms and legs, is restored.
- Do not enable "Copy Constraints" in Make Rig. It breaks the internal bones of mmd_tools.
- Some models drive their helper bones with their own systems that mmd_tools itself does not reproduce exactly as in MMD. The converted rig follows mmd_tools, so it may deform differently from MMD. A note is shown when the preset is detected.
- Preserve mutes the MMD IK that contains mapped bones. Hair IK and similar IK stop working. Move the hair with the Auto-Rig Pro controllers.
- On old models without arm twist bones (腕捩), twisting the upper arm in Convert does not twist the upper arm mesh. Bending works.
- Physics (rigid bodies and joints) are not reproduced.

## Using only the presets, without the add-on

The files in the `presets/` folder are Quick Rig presets.

1. Copy `presets/*.py` to the Quick Rig preset folder (Custom Presets Path) and restart Blender.
   - The default folder is `~/Documents/AutoRigPro/Quick Rig Presets/`.
2. To find the preset to use, run `mmd_to_arp/detect.py`. After importing the model, open the file in the Text Editor and press "Run Script".
3. Run Make Rig in Convert mode with a Convert preset (`MMD_*`), or in Preserve mode with a Preserve preset (`MMD_P_*`).
   - To use a Convert preset in Preserve mode, enable "Constrain Overrides".
4. Select the generated rig, open the following file in the Text Editor and press "Run Script".
   - Convert: `mmd_to_arp/fix_convert.py`
   - Preserve: `mmd_to_arp/fix_preserve.py` (required)

See [docs/presets.md](docs/presets.md) (in Japanese) for the list of presets and the mapping design.

## Disclaimer

- This add-on is an unofficial tool. It is not affiliated with or endorsed by:
  - Artell, the developer of Auto-Rig Pro and Auto-Rig Pro: Quick Rig
  - The developers of mmd_tools
  - The author of MikuMikuDance
  - The Blender Foundation
- The rights to MMD models and motions belong to their authors. This add-on grants no rights to models or motions.
- Even if the add-on can convert a model, whether you may use it in Blender, modify it or publish what you make is decided by the terms of use of each model and motion. Some models do not allow use outside MMD or modification. Check the terms and use the model within them.
- The author is not liable for any damage caused by using this add-on.

## License

GPL-3.0-or-later. See [LICENSE](LICENSE) for the full text.

- Report bugs and ask questions in [GitHub Issues](https://github.com/utagestudio/mmd_to_arp/issues).
- Changes in each version: [CHANGELOG.md](CHANGELOG.md).
- Reporting bugs and contributing: [CONTRIBUTING.md](CONTRIBUTING.md).
- Information for developers is in [DEVELOPMENT.md](DEVELOPMENT.md) (in Japanese).
