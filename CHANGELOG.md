# Changelog

## 0.1.1

- Remove Steam App ID, build/version metadata and exact-original archive hash restrictions.
- Replace fixed-offset archive deltas with named-entry Flash overlays that preserve unrelated archive and launcher changes.
- Support standalone `rf.swf` folders without a Steam installation or an EXE.
- Keep mod-file, written-resource and backup integrity checks; retain the game's own updated SWF checks.
- Uninstall overlay hooks from the current archive instead of overwriting later unrelated changes with an old whole-archive snapshot.
- Keep English and Chinese documentation aligned with the new installation behavior.

## 0.1.0

- Add a second independently controlled miner to single-player levels.
- Map player 2 controls to WASD while preserving original mode-specific actions.
- Keep collection animations independent and share money, inventory, goals and time.
- Add collision ownership and two-player collection settlement checks.
- Patch the base and three localized single-player SWF variants.
- Provide a Windows installer with exact-build validation, original-file backup and restore.
- Publish English-first documentation with Chinese installation instructions.

Initial release targets Steam build `26673644` only.
