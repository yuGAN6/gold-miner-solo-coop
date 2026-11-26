Gold Miner Single-Player Campaign Co-op v0.1.1

Extract the whole ZIP, close the game, and run Install.cmd.
Select a folder containing rf.swf, app.asar or resources\app.asar.
You can also drag that folder onto Install.cmd.
Start the game normally and select Single Player.

P1: arrow keys. P2: S to drop, W for dynamite, A/D for original Left/Right.
Money, goals, inventory and countdown are shared. Swing/retraction rules are unchanged.

No Steam App ID, build, game version, original-SWF hash or whole-ASAR hash whitelist.
Uses Windows PowerShell 5.1 and .NET; no Python, Java, Node.js or FFDec installation.
Resource structure must still be compatible. Mod payload/write integrity checks remain.

Loose Flash mode backs up and replaces existing rf.swf variants. Other modifications
inside the same SWF are replaced, not merged. Uninstall.cmd restores pre-install copies;
keep .goldminer-coop-backups and .goldminer-solo-coop-state.json.

Packaged mode changes only the named launcher/pack-reader entries of the CURRENT ASAR.
Four Flash files are loaded from resources/goldminer-solo-coop. swf.pack is untouched.
Unrelated archive entries and launcher changes are preserved. A full pre-install ASAR
snapshot is retained as app.asar.goldminer-coop-*.bak. Uninstall removes the marked
overlay hooks from the current archive and retains snapshots/assets for reuse.

If upgrading from v0.1.0, uninstall that old version first to start from official files.
Otherwise the old mod remains part of the pre-existing installation after v0.1.1 removal.
Game updates may remove hooks; reinstall when the resource interface remains compatible.

The Flash gameplay was tested in the actual game. The new installer was tested on
modified archive copies and loose Flash files, including runtime pack-reader checks.
A second physical PC, full campaign and new full desktop session are not validated.
Original save, achievement and leaderboard logic remains; no separate mod records.
This is an unofficial mod and requires an existing compatible game or Flash resources.

CMD's ExecutionPolicy Bypass applies only to its child process, not persistent settings.
The installer does not auto-elevate. Chinese instructions: 使用说明.txt.
