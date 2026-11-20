#!/usr/bin/env bash
# Validate and build the Blender extension zip into dist/.
# Usage: tools/build_extension.sh            (uses $BLENDER or `blender` on PATH)
set -euo pipefail
cd "$(dirname "$0")/.."
BLENDER="${BLENDER:-blender}"
"$BLENDER" --factory-startup -b --command extension validate mmd_to_arp
mkdir -p dist
"$BLENDER" --factory-startup -b --command extension build \
    --source-dir mmd_to_arp --output-dir dist
