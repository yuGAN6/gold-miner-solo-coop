"""Package Flash overlays and a structure-aware Windows installer."""
import argparse
import hashlib
import json
import pathlib
import shutil
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
VERSION = 'GoldMiner-Solo-Coop-v0.1.1'
DEST = ROOT / 'mod-release' / VERSION


def sha(path):
    with open(path, 'rb') as f:
        h = hashlib.sha256()
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--flash-dir', type=pathlib.Path, default=ROOT / 'mod-work/coop-swf')
    args = parser.parse_args()
    DEST.mkdir(parents=True, exist_ok=True)
    # New version directory: never mix a historical fixed-offset payload into this package.
    flash = []
    for variant in ('', 'l10n-cjk', 'l10n-latin', 'l10n-pad'):
        name = (variant + '/' if variant else '') + 'rf.swf'
        relative = 'flash/' + name
        target = DEST / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.flash_dir / name, target)
        flash.append({'name': name, 'path': relative, 'sha256': sha(target)})
    for p in (ROOT / 'mod-tools/portable').iterdir():
        if p.suffix == '.ps1':
            (DEST / p.name).write_text(p.read_text(encoding='utf8'), encoding='utf-8-sig')
        elif p.suffix == '.cmd':
            (DEST / p.name).write_bytes(p.read_text(encoding='utf8').replace('\n', '\r\n').encode('utf8'))
        else:
            shutil.copy2(p, DEST / p.name)
    files = [{'path': str(p.relative_to(DEST)).replace('\\', '/'), 'sha256': sha(p)}
             for p in sorted(DEST.rglob('*')) if p.is_file() and p.name != 'manifest.json']
    manifest = {'format': 'goldminer-flash-overlay-v2', 'modVersion': '0.1.1',
                'flash': flash, 'files': files}
    (DEST / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf8')
    archive = DEST.parent / (VERSION + '.zip')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(DEST.rglob('*')):
            if p.is_file(): z.write(p, VERSION + '/' + str(p.relative_to(DEST)).replace('\\', '/'))
    (DEST.parent / (VERSION + '.zip.sha256')).write_text(sha(archive) + '  ' + archive.name + '\n', encoding='ascii')
    print(json.dumps({'zip': str(archive), 'bytes': archive.stat().st_size, 'flashFiles': len(flash)}, indent=2))


if __name__ == '__main__':
    main()
