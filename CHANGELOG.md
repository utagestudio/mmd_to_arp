# Changelog

English | [日本語](CHANGELOG.ja.md)

All notable changes to MMD to Auto-Rig Pro are listed here.
The version format is `<major>.<minor>.<fix>`.

## Unreleased

### Fixed
- Convert: on models whose thigh deforms through helper bones (a thigh twist bone moved by append from an IK helper), the thigh bent in its middle. These helper bones now follow the thigh.
- Bake Motion: bones moved by MMD append or IK (eyes following 両目, leg helpers...) moved twice as much. They now use the VMD keys.

## [0.5.0] - 2026-11-22

### Added
- The panel shows a small note when the installed Auto-Rig Pro or Quick Rig version has not been tested with this add-on.
- The add-on zip now includes the full license text (LICENSE).

### Changed
- Blender 4.5 or later is required (tested with 4.5 and 5.3).
- The README is now available in English (README.md) and Japanese (README.ja.md).

## [0.4.0] - 2026-11-21

### Added
- **Bake Motion**: when the MMD armature has a motion (VMD), Convert bakes it to the FK controls of the arms and legs.
- The post-fix removes the keys of the IK-FK switches. You can switch the limbs to IK anywhere in the motion. This also applies to motions baked with Quick Rig's own Make Rig.

### Changed
- IK / FK panel: switching a limb with a baked motion back to FK no longer snaps. The limb returns to the motion as it is.
- IK / FK panel: with auto keying, the IK-FK switch is keyed with constant interpolation. IK and FK are no longer blended between two keys.

### Fixed
- Baking an animation from Convert failed with an error in Quick Rig.

## [0.3.0] - 2026-11-21

### Added
- **Other Bones** option: the controller shape of the bones that are not mapped (hair, skirts, accessories...). The new default, **Line**, draws a line along each bone. **Sphere** and **Box** are the Quick Rig shapes.

## [0.2.0] - 2026-11-21

### Added
- **IK / FK** panel: switch each arm and leg between IK and FK while keeping the pose (same as Auto-Rig Pro's "Snap IK-FK").
- **Arms / Legs** options: choose whether the arms and legs of the generated rig start in IK or FK.
- Convert restores MMD append (付与) on the bones that are not mapped, such as the eyes following the 両目 bone.

### Fixed
- In IK, the arms of some models bent the wrong way. Arms that are almost straight in the rest pose now get the elbow pointed backward.

## [0.1.0] - 2026-11-21

### Added
- First release.
- Detects the Quick Rig mapping (preset) that fits the skeleton of the MMD model.
- Convert and Preserve modes: runs Quick Rig's Make Rig and the MMD post-fix in one click.
- Convert post-fix: re-creates the MMD IK of helper bones.
- Preserve post-fix: hands helper bones driven by append or IK back to MMD.
- Quick Rig preset files that can be used without the add-on.

[0.5.0]: https://github.com/utagestudio/mmd_to_arp/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/utagestudio/mmd_to_arp/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/utagestudio/mmd_to_arp/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/utagestudio/mmd_to_arp/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/utagestudio/mmd_to_arp/releases/tag/v0.1.0
