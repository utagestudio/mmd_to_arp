# SPDX-License-Identifier: GPL-3.0-or-later
"""Publish a release zip to the extension repository of the site.

Copies the zip into site/public/repository/, removes the other mmd_to_arp zips there
(unless --keep), and writes index.json with Blender's own generator:

    python3 tools/make_repository.py dist/mmd_to_arp-<version>.zip [--keep]

Uses $BLENDER (default: blender on PATH). Commit site/public/repository/ afterwards:
the push deploys the site, and Blender sees the new version through
https://mmd-to-arp.utage.studio/repository/index.json.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REPO_DIR = REPO_ROOT / 'site' / 'public' / 'repository'
ZIP_RE = re.compile(r'^mmd_to_arp-(\d+\.\d+\.\d+)\.zip$')


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('zip', type=Path, help='release zip built by tools/build_extension.sh')
    ap.add_argument('--keep', action='store_true', help='keep the zips of other versions')
    args = ap.parse_args()

    if not ZIP_RE.match(args.zip.name):
        sys.exit('not a release zip (mmd_to_arp-<major>.<minor>.<fix>.zip): %s' % args.zip.name)
    if not args.zip.is_file():
        sys.exit('zip not found: %s' % args.zip)

    REPO_DIR.mkdir(parents=True, exist_ok=True)
    if not args.keep:
        for old in REPO_DIR.glob('mmd_to_arp-*.zip'):
            if old.name != args.zip.name:
                old.unlink()
                print('removed', old.name)
    shutil.copy2(args.zip, REPO_DIR / args.zip.name)
    print('copied', args.zip.name)

    blender = os.environ.get('BLENDER', 'blender')
    subprocess.run([blender, '--factory-startup', '-b', '--command', 'extension', 'server-generate',
                    '--repo-dir', str(REPO_DIR)], check=True)
    print('wrote', (REPO_DIR / 'index.json').relative_to(REPO_ROOT))


if __name__ == '__main__':
    main()
