#!/usr/bin/env bash
# Validate and build the Blender extension zip into dist/.
# The add-on is staged in a temporary directory together with the repository LICENSE,
# so the zip carries the full license text.
# Usage: tools/build_extension.sh            (uses $BLENDER or `blender` on PATH)
set -euo pipefail
cd "$(dirname "$0")/.."
BLENDER="${BLENDER:-blender}"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
cp -r mmd_to_arp "$STAGE/"
rm -rf "$STAGE/mmd_to_arp/__pycache__"
cp LICENSE "$STAGE/mmd_to_arp/LICENSE"
"$BLENDER" --factory-startup -b --command extension validate "$STAGE/mmd_to_arp"
mkdir -p dist
"$BLENDER" --factory-startup -b --command extension build \
    --source-dir "$STAGE/mmd_to_arp" --output-dir dist
