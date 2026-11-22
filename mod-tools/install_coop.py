"""Install or restore the built mod, retaining the exact original ASAR."""
import hashlib
import pathlib
import shutil
import sys
from asar_tool import repack, read_header, entries

ROOT = pathlib.Path(__file__).resolve().parent.parent
archive = ROOT / 'resources/app.asar'
backup = ROOT / 'resources/app.asar.pre-coop-mod'
mode = sys.argv[1] if len(sys.argv) > 1 else 'build'
if mode == 'restore':
    if not backup.exists():
        raise SystemExit('Original backup is missing; nothing was changed.')
    shutil.copy2(backup, archive)
    print('Restored original app.asar')
else:
    source = backup if backup.exists() else archive
    out = ROOT / 'mod-work/app-coop.asar'
    replacements = {name: ROOT / 'mod-work/patched' / name
                    for name in ('electron-main.js', 'swf.pack')}
    repack(source, out, replacements)
    # Compare every entry to the original, including packed and unpacked flags.
    old, oldbase = read_header(source)
    new, newbase = read_header(out)
    oldfiles, newfiles = dict(entries(old)), dict(entries(new))
    assert oldfiles.keys() == newfiles.keys()
    changed = []
    with source.open('rb') as a, out.open('rb') as b:
        for name, entry in oldfiles.items():
            target = newfiles[name]
            if entry.get('unpacked') or 'link' in entry:
                assert entry == target
                continue
            a.seek(oldbase + int(entry['offset']))
            b.seek(newbase + int(target['offset']))
            ab, bb = a.read(entry['size']), b.read(target['size'])
            if ab != bb:
                changed.append(name)
                assert name in replacements
                assert hashlib.sha256(bb).hexdigest() == target['integrity']['hash']
    assert set(changed) == set(replacements)
    print('ASAR verified; changed entries:', ', '.join(changed))
    if mode == 'install':
        if not backup.exists():
            shutil.copy2(archive, backup)
        shutil.copy2(out, archive)
        print('Installed co-op mod; original:', backup)
