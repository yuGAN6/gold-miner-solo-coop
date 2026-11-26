# Development and release builds

Release installation uses Windows PowerShell 5.1 and .NET only. A packaged game's own Electron runtime executes the installed overlay; no separate Node.js installation is required by recipients.

## Developer prerequisites

- Local Gold Miner Flash/game resources in the layout expected by the build tools.
- Python 3.9 or newer and Node.js (no npm dependencies).
- JPEXS FFDec 26.5.0 and its libraries under `mod-tools/vendor/ffdec/`, with `ffdec.jar` directly in that folder.
- Java, tested with Temurin 21, extracted under `mod-tools/vendor/java/`; the builder finds `java.exe` recursively.

Obtain FFDec from its [official releases](https://github.com/jindrapetrik/jpexs-decompiler/releases/tag/version26.5.0); see its [CLI documentation](https://github.com/jindrapetrik/jpexs-decompiler/wiki/Commandline-arguments). Java runtimes are available from [Eclipse Adoptium](https://adoptium.net/).

Third-party tools and original/decompiled game files are not committed. Build-time extractors and symbol IDs target the currently analyzed Flash structure; removing installer build gates does not automatically adapt the Flash transformation to unrelated SWF structures.

## Prepare and build Flash files

```powershell
python mod-tools/prepare_development.py --game-dir 'D:\Games\Gold MinerClassic Edition'
python mod-tools/build_coop.py
```

The preparation helper reads an available original archive/backup into ignored local build directories, extracts the SWF pack using the game's local reader/configuration and exports scripts through FFDec. It does not compare a known Steam build or source-archive hash. An existing different local build input is left intact; use a clean workspace when changing inputs. The helper does not modify the selected installation.

If Flash files/scripts are already extracted, prepare the expected `mod-work/swf/` and `mod-work/rf-scripts/` layout directly. The builder produces four modified files under `mod-work/coop-swf/`.

## Export the release

```powershell
python mod-tools/export_portable.py
# Or select an existing directory containing the four built Flash variants:
python mod-tools/export_portable.py --flash-dir 'D:\Builds\coop-swf'
```

This produces `mod-release/GoldMiner-Solo-Coop-v0.1.1.zip` and its `.zip.sha256` checksum. A full modified ASAR is no longer an export input. The manifest describes the Flash files and package-integrity hashes; it has no Steam App ID/build, original archive hash, fixed byte offsets or expected whole-archive output hash.

## Runtime installation

- `ArchiveTools.cs` reads the current ASAR header and replaces named entries, preserving all other packed/unpacked/link metadata. It updates integrity metadata for the changed entries.
- `Manage-Mod.ps1` handles selection, backups, loose Flash replacement, marked launcher edits and uninstall. `ArchiveTools.cs` is compiled by Windows' built-in .NET tooling through `Add-Type`.
- `flash-loader.cjs` wraps the existing pack reader to serve four external co-op SWFs; `swf.pack` and embedded keys remain in the game.
- The current `SWF_SHA_BAKED` expression is wrapped with replacement hashes; unrelated entries in the hash table remain intact. Uninstall unwraps it and removes the marked loader from the current source, retaining other edits.
- Loose installs back up and replace existing named SWFs. These replacements do not merge other changes inside a SWF.

The legacy `package-coop.cjs` and `install_coop.py` remain as local full-archive build utilities. They are not used by the v0.1.1 recipient installer or exporter.

## Validate

```powershell
python mod-tools/test_portable.py
# Optional explicit local inputs:
python mod-tools/test_portable.py --archive 'D:\Inputs\original.asar' --reference-tools 'D:\Reference\mod-tools'
```

Tests extract the actual release ZIP and use Windows PowerShell 5.1. They deliberately change archive/launcher content before installation and add another edit after installation. Checks verify that installation/uninstall preserve unrelated changes, that the game's original integrity function passes with the overlay, that loose Flash files can be restored, and that corrupt package data or invalid archive structures fail without replacing the live input.

The reference-tools directory supplies `unpack-flash.cjs` and its prepared local original inputs for the runtime pack-reader test. Results are written to `mod-release/installer-test-results.json`. Fixtures contain local original data and stay in ignored `mod-work/` directories. Do not commit them.
