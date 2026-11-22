"""Prepare ignored local build inputs from an owned compatible game install."""
import argparse
import pathlib
import shutil
import subprocess
from asar_tool import extract
from export_portable import ROOT, sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--game-dir', required=True, type=pathlib.Path)
    args = parser.parse_args()
    expected = '751653bc50d01951a450a3cc24a1a7b7682e96033a38218c5adc9cb5f2225727'
    candidates = [args.game_dir / 'resources' / name for name in
                  ('app.asar.goldminer-coop-original', 'app.asar.pre-coop-mod', 'app.asar')]
    original = next((p for p in candidates if p.is_file() and sha(p) == expected), None)
    if original is None:
        raise SystemExit('No matching original archive was found. Required Steam build: 26673644.')
    local = ROOT / 'resources/app.asar.pre-coop-mod'
    local.parent.mkdir(exist_ok=True)
    if not local.exists():
        shutil.copy2(original, local)
    if sha(local) != expected:
        raise SystemExit('Local build input differs; it was not overwritten.')
    extract(local, ROOT / 'mod-work/original-app')
    subprocess.run(['node', str(ROOT / 'mod-tools/extract-swf.cjs')], cwd=ROOT, check=True)
    # Import after prerequisites and build inputs have been checked.
    from build_coop import ffdec, WORK
    ffdec('-export', 'script', WORK / 'rf-scripts', WORK / 'swf/rf.swf')
    print('Development inputs prepared. No files in the game installation were changed.')


if __name__ == '__main__':
    main()
