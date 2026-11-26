# Gold Miner Single-Player Campaign Co-op

Play the original **Gold Miner: Classic Edition** single-player levels with two local players. This unofficial Flash mod adds a second independently controlled miner to the existing single-player campaign.

[Download the latest release](https://github.com/yuGAN6/gold-miner-solo-coop/releases/latest) · [中文说明](README.zh-CN.md) · [Development guide](docs/DEVELOPMENT.md)

![Two miners playing a single-player level](docs/images/preview.png)

## Features

- Independent miners, claws and collection animations.
- Arrow keys for the left player; WASD for the right player.
- Shared money, objectives, inventory and countdown.
- Existing single-player level layouts and progression.
- Install to loose Flash files or add a named-resource overlay to an Electron ASAR.

The original separate two-player mode is unchanged. This mod is for playing the **single-player levels together**.

## Requirements

| Item | Requirement |
| --- | --- |
| Installer platform | Windows, with built-in Windows PowerShell 5.1 and .NET |
| Loose Flash installation | A folder containing `rf.swf`; localized variants are replaced when present |
| Packaged installation | `app.asar` or `resources/app.asar` with the expected launcher and SWF pack reader |
| Steam identification | No App ID, build number or displayed-version check |
| Original file hashes | No whole-archive or original-SWF hash whitelist |

Python, Java, Node.js and FFDec are **not needed to install a release**. The packaged overlay runs inside the game's existing Electron runtime.

The installer checks resource structure and mod-file integrity. Removing version restrictions does not make unrelated Flash games or incompatible launcher structures compatible. Existing changes inside an `rf.swf` that is replaced are not merged into the supplied co-op SWF.

## Install

1. Download `GoldMiner-Solo-Coop-v0.1.1.zip` from [Releases](https://github.com/yuGAN6/gold-miner-solo-coop/releases).
2. Extract the entire ZIP and close the game.
3. Double-click `Install.cmd`. Select the folder containing `rf.swf`, `app.asar` or `resources/app.asar`. You can also drag that folder onto `Install.cmd`; a package placed in/under the game directory can discover it automatically.
4. Start your game normally and select **Single Player**. Steam installations can still launch through Steam.

Download the release ZIP rather than GitHub's automatically generated **Source code** ZIP: the source archive does not contain the Flash payload. Mod-file hashes and written-resource checks remain enabled to detect corrupt downloads or writes.

## Controls

| Action | Left player | Right player |
| --- | --- | --- |
| Drop claw | Down | S |
| Use dynamite while retrieving, when available | Up | W |
| Original Left action | Left | A |
| Original Right action | Right | D |

Miners retain the original automatic swing. In classic gameplay, A uses a freeze box when available and D usually has no action. Modes with manual retraction retain their original Left/Right mechanics through A/D.

## Uninstall and updates

Close the game and run `Uninstall.cmd` against the same folder.

For packaged installs, uninstall removes this mod's launcher/hash overlay hooks from the **current** ASAR, retaining unrelated changes made before or after installation. The original `swf.pack` is never rewritten. A full pre-install ASAR snapshot is retained beside the archive as `app.asar.goldminer-coop-*.bak`; overlay assets and install state remain in `goldminer-solo-coop/` for reuse.

For loose Flash installs, uninstall restores the pre-install SWF copies. Keep `.goldminer-coop-backups/` and `.goldminer-solo-coop-state.json`. Restoration replaces the targeted SWFs, including any later edits to those same files.

Game updates can remove overlay hooks or replace Flash files. You can reinstall without a Steam-build or full-file hash gate, provided the resource structure is still supported. When migrating from v0.1.0, uninstall that old version first if you want the new version's uninstall to return to the official files rather than retain the old mod.

## How the patch works

The release ships four ready-built co-op `rf.swf` variants and a structure-aware installer. It no longer uses a fixed-offset whole-ASAR binary delta.

In loose mode, existing target SWFs are backed up and replaced. In packaged mode, the installer rebuilds the **current** ASAR by named entries, adds a marked overlay to `main/swf-pack.js`, and wraps the current `SWF_SHA_BAKED` expression with the four replacement hashes. Unrelated entries and launcher edits are preserved. The game's own Flash integrity check remains active with the updated hashes; ASAR metadata is recalculated for changed entries.

The Flash mod duplicates miner, claw, button and collection-animation symbols. Player 2 has independent instances and WASD events. Collision and countdown settlement checks account for both players. Original embedded keys remain in the recipient's game and are not included in the release.

## Validation and limitations

- The Flash gameplay has been play-tested in the actual game, including independent control and shared scoring.
- The v0.1.1 installer is tested on modified ASAR fixtures without Steam files or an EXE, and on standalone/customized `rf.swf` files.
- Tests cover repeat installation, snapshot backups, preservation of unrelated changes, uninstall, damaged payload rejection and malformed-archive handling.
- The actual game pack reader was tested with the overlay: all four modded Flash resources and their hashes match, while the original two-player SWF remains unchanged.
- A full campaign playthrough, every special item/late-game obstacle combination and a second physical computer have not been validated; the new overlay installer has been validated through isolated/runtime tests, not a new full desktop gameplay session.
- Original save, achievement and leaderboard integration remains in place; there is no separate mod record system.
- Loose SWF replacements do not merge other Flash modifications. Packaged installation preserves unrelated archive entries but requires the named launcher/pack-reader interface.

This is an unofficial project, not affiliated with or endorsed by the original game's developers or publisher. Original game code and assets remain the property of their respective owners.

## Development

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for preparing local inputs, building SWFs and exporting/testing the installer. Decompiled game files, full archives and third-party tool binaries are excluded from this repository.
