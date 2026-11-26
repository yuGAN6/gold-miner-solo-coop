"""Test named-resource installation on modified archives and standalone Flash."""
import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import uuid
import zipfile
from asar_tool import read_header, entries, repack
from export_portable import ROOT, VERSION, sha


def read(archive, name):
    h, base = read_header(archive)
    entry = dict(entries(h))[name]
    with archive.open('rb') as f:
        f.seek(base + int(entry['offset']))
        return f.read(entry['size'])


def entry_hashes(archive):
    header, base = read_header(archive)
    result = {}
    with archive.open('rb') as f:
        for name, item in entries(header):
            if item.get('unpacked') or 'link' in item: continue
            f.seek(base + int(item['offset']))
            result[name] = hashlib.sha256(f.read(item['size'])).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=pathlib.Path, default=ROOT / 'resources/app.asar.pre-coop-mod')
    parser.add_argument('--reference-tools', type=pathlib.Path, default=ROOT / 'mod-tools')
    args = parser.parse_args()
    test = ROOT / 'mod-work' / ('overlay-test-' + uuid.uuid4().hex)
    test.mkdir(parents=True)
    package = test / 'package'
    with zipfile.ZipFile(ROOT / 'mod-release' / (VERSION + '.zip')) as z:
        z.extractall(package)
    package = package / VERSION
    manifest = json.loads((package / 'manifest.json').read_text())
    assert not any(k in manifest for k in ('source', 'target', 'steamAppId', 'steamBuildId', 'gameVersion'))
    checks = []

    def run(folder, mode='Install', expected=0, pkg=package):
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                                 '-File', str(pkg / 'Manage-Mod.ps1'), '-Mode', mode,
                                 '-GameDirectory', str(folder), '-NonInteractive'], capture_output=True, timeout=180)
        if result.returncode != expected:
            raise AssertionError(result.stdout.decode(errors='replace') + result.stderr.decode(errors='replace'))

    # Changed launcher and unrelated package data: input deliberately differs from
    # the old supported ASAR hash. No EXE or Steam files are present in the fixture.
    game = test / '游戏副本 with spaces'
    resources = game / 'resources'
    resources.mkdir(parents=True)
    archive = resources / 'app.asar'
    main_source = read(args.archive, 'electron-main.js') + b'\n// Preserve another launcher mod.\n'
    other = json.loads(read(args.archive, 'package.json'))
    other['unrelatedModTest'] = True
    main_input = test / 'main-input.js'; main_input.write_bytes(main_source)
    other_input = test / 'package-input.json'; other_input.write_text(json.dumps(other), encoding='utf8')
    repack(args.archive, archive, {'electron-main.js': main_input, 'package.json': other_input})
    before = sha(archive)
    before_entries = entry_hashes(archive)
    original_pack = read(archive, 'main/swf-pack.js')
    swfpack = read(archive, 'swf.pack')
    run(game)
    assert sha(archive) != before
    after_entries = entry_hashes(archive)
    assert after_entries.keys() == before_entries.keys()
    assert {name for name in before_entries if before_entries[name] != after_entries[name]} == {'electron-main.js', 'main/swf-pack.js'}
    checks.append('All packed ASAR entries compared: only the two intended launcher/reader entries change')
    assert read(archive, 'swf.pack') == swfpack
    assert read(archive, 'package.json') == other_input.read_bytes()
    assert b'Preserve another launcher mod' in read(archive, 'electron-main.js')
    state = json.loads((resources / 'goldminer-solo-coop/install-state.json').read_text(encoding='utf-8-sig'))
    assert sha(pathlib.Path(state['backup'])) == before
    checks.append('Accept modified archives without Steam metadata/EXE or whole-archive hash checks; preserve other entries and snapshot input')

    first_main = read(archive, 'electron-main.js')
    first_pack = read(archive, 'main/swf-pack.js')
    run(game)
    assert read(archive, 'electron-main.js') == first_main
    assert read(archive, 'main/swf-pack.js') == first_pack
    checks.append('Repeated installation keeps a single hash wrapper and loader')

    # Exercise the actual original pack reader with the new overlay and all four
    # supplied Flash files, using keys recovered only from the local original.
    module_dir = resources / 'app/main'; module_dir.mkdir(parents=True)
    loader = module_dir / 'swf-pack.cjs'; loader.write_bytes(first_pack)
    main_check = test / 'main-check.cjs'; main_check.write_bytes(first_main)
    subprocess.run(['node', '--check', str(main_check)], check=True)
    probe = test / 'probe.cjs'
    probe.write_text("""const fs=require('fs'),path=require('path'),assert=require('assert'),crypto=require('crypto'),vm=require('vm');
const u=require(path.join(process.argv[2],'unpack-flash.cjs'));
const mod=require(process.argv[3]);
const p=mod.open(fs.readFileSync(path.join(u.root,'swf.pack')),u.key);
const manifest=JSON.parse(fs.readFileSync(path.join(process.argv[4],'manifest.json')));
for(const f of manifest.flash){ const expected=fs.readFileSync(path.join(process.argv[4],f.path));
assert(p.read(f.name).equals(expected)); assert.equal(p.sha256(f.name),crypto.createHash('sha256').update(expected).digest('hex')); }
assert(p.read('main.swf').equals(u.opened.read('main.swf')));
const main=fs.readFileSync(process.argv[5],'utf8');
const begin=main.indexOf('SWF_SHA_BAKED=')+'SWF_SHA_BAKED='.length;
const marker='/* GOLDMINER_COOP_HASHES_END */';
const end=main.indexOf(marker,begin)+marker.length;
const hashes=vm.runInContext('('+main.slice(begin,end)+')',u.context);
Object.assign(u.context,{DEV_SWF_SOURCE:false,SWF_STATE:{},PACK_NAMES:u.opened.names(),SWF_SHA:hashes,SWF_PACK_KEY_B64:u.key.toString('base64'),
  _swfCache:{},_sha256:b=>crypto.createHash('sha256').update(b).digest('hex'),
  fs,path,Buffer,__dirname:u.root,require:n=>n==='./main/swf-pack'?mod:require(n)});
const result=vm.runInContext(u.functionSource(main,'checkSwfIntegrity')+';checkSwfIntegrity()',u.context);
assert.equal(result.status,'ok',JSON.stringify(result));
console.log('Runtime overlay verified for four Flash variants; original two-player SWF preserved.');
""", encoding='utf8')
    subprocess.run(['node', str(probe), str(args.reference_tools.resolve()), str(loader), str(package), str(main_check)], check=True)
    checks.append('Runtime pack reader returns all four co-op SWFs, correct hashes, and the unchanged two-player SWF')
    checks.append('Original game checkSwfIntegrity function passes with the updated hash expression and overlay; integrity checking remains active')

    # An unrelated edit made AFTER installation must survive uninstall too.
    later = test / 'later-main.js'; later.write_bytes(first_main + b'\n// Later launcher change.\n')
    staged = test / 'later.asar'
    repack(archive, staged, {'electron-main.js': later})
    shutil.copyfile(staged, archive)
    run(game, 'Uninstall')
    assert read(archive, 'electron-main.js') == main_source + b'\n// Later launcher change.\n'
    assert read(archive, 'main/swf-pack.js') == original_pack
    assert read(archive, 'package.json') == other_input.read_bytes()
    run(game, 'Uninstall')
    checks.append('Uninstall removes only overlay hooks, preserving modifications made before and after installation')

    loose = test / 'standalone Flash'; loose.mkdir()
    standalone = loose / 'rf.swf'; standalone.write_bytes(b'existing customized flash file')
    run(loose)
    assert standalone.read_bytes() == (package / 'flash/rf.swf').read_bytes()
    run(loose)
    run(loose, 'Uninstall')
    assert standalone.read_bytes() == b'existing customized flash file'
    run(loose, 'Uninstall')
    checks.append('Standalone rf.swf installation, repeated installation, and original-file restoration work without an Electron/Steam installation')

    damaged = test / 'damaged-package'; shutil.copytree(package, damaged)
    (damaged / 'flash/rf.swf').write_bytes(b'corrupt download')
    before = sha(archive)
    run(game, pkg=damaged, expected=1)
    assert sha(archive) == before
    checks.append('Keep release-file integrity checks: damaged Flash payload is rejected without changing the game')

    invalid = test / 'invalid archive'; (invalid / 'resources').mkdir(parents=True)
    invalid_file = invalid / 'resources/app.asar'; invalid_file.write_bytes(b'not an archive')
    run(invalid, expected=1)
    assert invalid_file.read_bytes() == b'not an archive'
    assert not list(invalid.rglob('*.tmp'))
    checks.append('Invalid archive structure fails before replacement, without a Steam/version whitelist')
    report = {'passed': len(checks), 'checks': checks, 'packageSha256': sha(ROOT / 'mod-release' / (VERSION + '.zip'))}
    (ROOT / 'mod-release/installer-test-results.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
