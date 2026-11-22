"""Export copy/literal ASAR deltas usable with built-in Windows PowerShell."""
import gzip
import hashlib
import json
import pathlib
import shutil
import zipfile
from asar_tool import read_header, entries

ROOT = pathlib.Path(__file__).resolve().parent.parent
VERSION = 'GoldMiner-Solo-Coop-v0.1.0'
DEST = ROOT / 'mod-release' / VERSION


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    source = ROOT / 'resources/app.asar.pre-coop-mod'
    target = ROOT / 'mod-work/app-coop.asar'
    old, oldbase = read_header(source)
    new, newbase = read_header(target)
    oldfiles = dict(entries(old))
    DEST.mkdir(parents=True, exist_ok=True)
    literals = bytearray()
    operations = []

    def append(kind, length, offset=None):
        if not length:
            return
        if operations and operations[-1]['kind'] == kind:
            last = operations[-1]
            if kind == 'data' or last['offset'] + last['length'] == offset:
                last['length'] += length
                return
        operation = {'kind': kind, 'length': length}
        if offset is not None:
            operation['offset'] = offset
        operations.append(operation)

    with source.open('rb') as a, target.open('rb') as b:
        literals.extend(b.read(newbase))
        append('data', newbase)
        for name, entry in entries(new):
            if entry.get('unpacked') or 'link' in entry:
                continue
            oldentry = oldfiles[name]
            a.seek(oldbase + int(oldentry['offset']))
            b.seek(newbase + int(entry['offset']))
            original, updated = a.read(oldentry['size']), b.read(entry['size'])
            if original == updated:
                append('copy', len(updated), oldbase + int(oldentry['offset']))
            else:
                assert name in ('electron-main.js', 'swf.pack'), name
                if name == 'electron-main.js':
                    # Reuse the original launcher, including its embedded keys.
                    # Distribute only the changed hash-table expression.
                    prefix = 0
                    while prefix < min(len(original), len(updated)) and original[prefix] == updated[prefix]:
                        prefix += 1
                    suffix = 0
                    while suffix < min(len(original), len(updated)) - prefix and original[-suffix-1] == updated[-suffix-1]:
                        suffix += 1
                    changed = updated[prefix:len(updated)-suffix if suffix else len(updated)]
                    assert b'SWF_PACK_KEY_B64' not in changed and b'__GMT_' not in changed
                    append('copy', prefix, oldbase + int(oldentry['offset']))
                    literals.extend(changed)
                    append('data', len(changed))
                    if suffix:
                        append('copy', suffix, oldbase + int(oldentry['offset']) + len(original) - suffix)
                else:
                    literals.extend(updated)
                    append('data', len(updated))
    payload = DEST / 'payload.gz'
    payload.write_bytes(gzip.compress(bytes(literals), compresslevel=9, mtime=0))
    manifest = {
        'format': 'goldminer-coop-delta-v1', 'modVersion': '0.1.0',
        'game': 'Gold Miner: Classic Edition', 'steamAppId': 3777060,
        'steamBuildId': '26673644', 'gameVersion': '2.0.0',
        'source': {'size': source.stat().st_size, 'sha256': sha(source)},
        'target': {'size': target.stat().st_size, 'sha256': sha(target)},
        'payload': {'sha256': sha(payload), 'uncompressedSize': len(literals)},
        'operations': operations,
    }
    (DEST / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf8')
    for p in (ROOT / 'mod-tools/portable').iterdir():
        # BOM is required for non-ASCII PowerShell 5.1 source; cmd uses CRLF.
        if p.suffix == '.ps1':
            (DEST / p.name).write_text(p.read_text(encoding='utf8'), encoding='utf-8-sig')
        elif p.suffix == '.cmd':
            (DEST / p.name).write_bytes(p.read_text(encoding='utf8').replace('\n', '\r\n').encode('utf8'))
        else:
            shutil.copy2(p, DEST / p.name)
    archive = DEST.parent / (VERSION + '.zip')
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(DEST.iterdir()):
            z.write(p, VERSION + '/' + p.name,
                    compress_type=zipfile.ZIP_STORED if p.name == 'payload.gz' else zipfile.ZIP_DEFLATED)
    (DEST.parent / (VERSION + '.zip.sha256')).write_text(sha(archive) + '  ' + archive.name + '\n', encoding='ascii')
    print(json.dumps({'zip': str(archive), 'bytes': archive.stat().st_size,
                      'operations': len(operations), 'literalBytes': len(literals)}, indent=2))


if __name__ == '__main__':
    main()
