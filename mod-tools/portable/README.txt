Gold Miner Single-Player Campaign Co-op Mod v0.1.0

Play the original single-player levels with two local players. Each player has
an independent miner and claw; money, objectives, inventory and time are shared.

REQUIREMENTS
  Windows Steam edition, App ID 3777060, game version 2.0.0, build 26673644.
  The original resources/app.asar must match this SHA-256:
  751653bc50d01951a450a3cc24a1a7b7682e96033a38218c5adc9cb5f2225727
  Windows PowerShell 5.1 and .NET are built-in Windows components.
  No Python, Java, Node.js or Flash decompiler is required for installation.

INSTALL
  1. Extract the entire release ZIP. Do not run it inside the ZIP viewer.
  2. Close Gold Miner.
  3. Double-click Install.cmd. Select the folder containing GoldMiner.exe if asked.
     You can also drag that folder onto Install.cmd.
  4. Launch the game normally from Steam and select Single Player.
  Unsupported builds or existing modifications are rejected before replacement.
  The installer creates and verifies a complete original-archive backup.

CONTROLS
  Left player: original arrow keys.
  Right player: S = drop claw, W = dynamite; A/D = original Left/Right actions.
  In classic gameplay A uses a freeze box when available, and D usually does nothing.
  Modes with manual retraction retain their original Left/Right mechanics.
  Miners keep the original automatic swing; WASD does not freely move the miner.

UNINSTALL
  Close the game, run Uninstall.cmd and select the same game folder.
  Keep resources/app.asar.goldminer-coop-original: it is the verified original backup.
  If Steam has updated the game, the uninstaller refuses to overwrite the newer build.
  Steam Verify integrity of game files can restore the current official version.

NOTES
  This unofficial delta patch requires an existing compatible game installation.
  Steam updates or file verification can remove the mod. A new build needs a new patch.
  Other mods that change app.asar are not automatically merged.
  Save, achievement and leaderboard logic remains the original game's integration.
  Local play and isolated installer checks passed; a complete campaign playthrough,
  every late-game item/obstacle combination and a second physical PC are not validated.
  CMD uses ExecutionPolicy Bypass only for its child process; it does not change the
  machine's persistent execution policy. The installer does not auto-elevate.

Chinese instructions: see 使用说明.txt in this folder.
