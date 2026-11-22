"""Exercise the released installer against isolated archive copies, never the game."""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import zipfile
from export_portable import ROOT, VERSION, sha

TEST = ROOT / 'mod-work/portable-installer-test'
GAME = TEST / '游戏副本 with spaces'
PACKAGE = TEST / '解压后的安装包'


def run(package, mode, game, expected):
    args = ['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
            '-File', str(package / 'Manage-Mod.ps1'), '-Mode', mode,
            '-GameDirectory', str(game), '-NonInteractive']
    completed = subprocess.run(args, capture_output=True, timeout=120)
    output = completed.stdout.decode('utf8', errors='replace') + completed.stderr.decode('utf8', errors='replace')
    if completed.returncode != expected:
        raise AssertionError((args, completed.returncode, output))
    return output


def run_discovery(package, working_directory):
    args = ['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
            '-File', str(package / 'Manage-Mod.ps1'), '-Mode', 'Install',
            '-GameDirectory', '', '-NonInteractive']
    completed = subprocess.run(args, cwd=working_directory, capture_output=True, timeout=120)
    if completed.returncode:
        raise AssertionError(completed.stdout.decode('utf8', errors='replace') + completed.stderr.decode('utf8', errors='replace'))


def main():
    TEST.mkdir(parents=True, exist_ok=True)
    # Test exactly the files recipients will get by extracting the final ZIP.
    PACKAGE.mkdir(exist_ok=True)
    with zipfile.ZipFile(ROOT / 'mod-release' / (VERSION + '.zip')) as z:
        for entry in z.infolist():
            dest = PACKAGE / pathlib.PurePosixPath(entry.filename).name
            dest.write_bytes(z.read(entry))
    manifest = json.loads((PACKAGE / 'manifest.json').read_text())
    GAME.mkdir(exist_ok=True)
    (GAME / 'GoldMiner.exe').write_bytes(b'test marker - never executable')
    resources = GAME / 'resources'
    resources.mkdir(exist_ok=True)
    archive = resources / 'app.asar'
    source = ROOT / 'resources/app.asar.pre-coop-mod'
    if not archive.exists():
        shutil.copy2(source, archive)
    assert sha(archive) == manifest['source']['sha256']
    checks = []
    run(PACKAGE, 'Install', GAME, 0)
    assert sha(archive) == manifest['target']['sha256']
    backup = resources / 'app.asar.goldminer-coop-original'
    assert sha(backup) == manifest['source']['sha256']
    checks.append('Fresh install reconstructs exact target, preserves exact original backup')
    run(PACKAGE, 'Install', GAME, 0)
    assert sha(archive) == manifest['target']['sha256']
    checks.append('Repeated installation is idempotent')
    run(PACKAGE, 'Uninstall', GAME, 0)
    assert sha(archive) == manifest['source']['sha256']
    run(PACKAGE, 'Uninstall', GAME, 0)
    assert sha(archive) == manifest['source']['sha256']
    checks.append('Uninstall and repeated uninstall restore exact original')

    mismatch = TEST / 'mismatched-game'
    (mismatch / 'resources').mkdir(parents=True, exist_ok=True)
    (mismatch / 'GoldMiner.exe').write_bytes(b'test marker')
    wrongarchive = mismatch / 'resources/app.asar'
    wrongarchive.write_bytes(b'different game build or another mod')
    before = sha(wrongarchive)
    run(PACKAGE, 'Install', mismatch, 1)
    run(PACKAGE, 'Uninstall', mismatch, 1)
    assert sha(wrongarchive) == before
    assert not (mismatch / 'resources/app.asar.goldminer-coop-original').exists()
    checks.append('Wrong versions and other mods are refused without modification')

    corrupt = TEST / 'damaged-package'
    corrupt.mkdir(exist_ok=True)
    for p in PACKAGE.iterdir():
        shutil.copy2(p, corrupt / p.name)
    (corrupt / 'payload.gz').write_bytes(b'damaged download')
    run(corrupt, 'Install', GAME, 1)
    assert sha(archive) == manifest['source']['sha256']
    checks.append('Damaged payload is refused and original is unchanged')

    # Also exercise failure after staging starts: keep payload hash valid, corrupt
    # expected target hash. Temp output must be removed, with no live replacement.
    badmanifest = dict(manifest)
    badmanifest['target'] = dict(manifest['target'], sha256='0' * 64)
    (corrupt / 'manifest.json').write_text(json.dumps(badmanifest), encoding='utf8')
    shutil.copy2(PACKAGE / 'payload.gz', corrupt / 'payload.gz')
    run(corrupt, 'Install', GAME, 1)
    assert sha(archive) == manifest['source']['sha256']
    assert not list(resources.glob('app.asar.coop-*.tmp'))
    checks.append('Failed final validation removes staged output and preserves original')

    run_discovery(PACKAGE, GAME)
    assert sha(archive) == manifest['target']['sha256']
    checks.append('Empty CMD directory argument and automatic current-folder discovery work')
    held_backup = backup.with_suffix('.held-test-backup')
    assert backup.resolve().is_relative_to(TEST.resolve())
    backup.rename(held_backup)
    try:
        run(PACKAGE, 'Uninstall', GAME, 1)
        assert sha(archive) == manifest['target']['sha256']
    finally:
        held_backup.rename(backup)
    run(PACKAGE, 'Uninstall', GAME, 0)
    assert sha(archive) == manifest['source']['sha256']
    checks.append('Missing backup prevents uninstall without altering the installed mod')

    installed = ROOT / 'resources/app.asar'
    if installed.exists():
        assert sha(installed) == manifest['target']['sha256']
        checks.append('User installed game remains unchanged throughout tests')
    report = {'passed': len(checks), 'checks': checks, 'packageSha256': sha(ROOT / 'mod-release' / (VERSION + '.zip'))}
    (ROOT / 'mod-release/installer-test-results.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
