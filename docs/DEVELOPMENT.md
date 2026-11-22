# Development and release builds

Release installation needs only Windows PowerShell and .NET. The steps below are for developers rebuilding the mod from a compatible game installation.

## Prerequisites

- A compatible original Steam installation: App ID `3777060`, build `26673644`.
- Python 3.9 or newer and Node.js. No npm dependencies are used by the helper scripts.
- JPEXS FFDec 26.5.0, extracted with its libraries to `mod-tools/vendor/ffdec/`, with `ffdec.jar` directly inside that folder.
- A Java runtime, tested with Temurin Java 21, extracted under `mod-tools/vendor/java/`. The builder finds `java.exe` recursively.

Obtain FFDec from its [official releases](https://github.com/jindrapetrik/jpexs-decompiler/releases/tag/version26.5.0). Its [CLI documentation](https://github.com/jindrapetrik/jpexs-decompiler/wiki/Commandline-arguments) describes the script and SWF XML import/export commands used here. Java runtimes are available from [Eclipse Adoptium](https://adoptium.net/).

Third-party binaries and original/decompiled game files are not committed. Keep them in the ignored directories described below.

## Prepare the local inputs

From the repository root:

```powershell
python mod-tools/prepare_development.py --game-dir 'D:\SteamLibrary\steamapps\common\Gold MinerClassic Edition'
```

This command checks the original archive hash, copies a compatible archive into the repository's ignored `resources/` directory, extracts local build inputs, reads the original SWF pack using its own bundled reader and exports ActionScript through FFDec. It does not change the selected game installation. An existing matching backup can supply the original archive when that installation already has this mod enabled.

The extracted launcher is read locally to recover the pack configuration. Do not commit `resources/`, `mod-work/`, decompiled files or generated full archives.

## Build and export

```powershell
python mod-tools/build_coop.py
node mod-tools/package-coop.cjs
python mod-tools/install_coop.py build
python mod-tools/export_portable.py
```

Outputs:

- `mod-work/coop-swf/`: the four modified single-player SWFs.
- `mod-work/app-coop.asar`: the verified full local build.
- `mod-release/GoldMiner-Solo-Coop-v0.1.0.zip`: the portable delta release.
- The accompanying `.zip.sha256`: release download checksum.

`install_coop.py build` creates an archive in the repository workspace; it does not install into the external Steam game folder. To install a build into a game, use the exported release's `Install.cmd` or `Manage-Mod.ps1 -GameDirectory`.

## Installer validation

```powershell
python mod-tools/test_portable.py
```

The test extracts the release ZIP, reconstructs the target archive in an isolated game-folder fixture, checks backup/restore, tests idempotent operations and verifies failure handling for incompatible/corrupt inputs. It also covers directory names with spaces and non-ASCII characters. Results are written to `mod-release/installer-test-results.json`.

Tests use Windows PowerShell 5.1, not just a newer `pwsh` installation. A game installation under the ignored workspace `resources/app.asar`, if present, is expected to be the tested modded archive and is checked for consistency.

## Repository map

| File | Purpose |
| --- | --- |
| `mod-tools/build_coop.py` | Collision/timer changes, symbol graph duplication and WASD mapping |
| `mod-tools/asar_tool.py` | ASAR extraction and repacking with integrity metadata |
| `mod-tools/unpack-flash.cjs` | Reads pack configuration from local original game code |
| `mod-tools/package-coop.cjs` | Rebuilds the SWF pack and updates four resource hashes |
| `mod-tools/export_portable.py` | Exports source-copy/literal-data patch operations |
| `mod-tools/portable/Manage-Mod.ps1` | Recipient-side installation and restore |

The public repository contains the mod tooling and installer source. Release assets contain the binary patch; full local game archives are not uploaded.
