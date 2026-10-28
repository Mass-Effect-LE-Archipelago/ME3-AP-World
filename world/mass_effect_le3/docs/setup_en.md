# Mass Effect Legendary Edition 3 setup

## What you need

- Mass Effect Legendary Edition (PC), with at least one **finished** ME2 LE save where Shepard survived.
- [Archipelago](https://github.com/ArchipelagoMW/Archipelago/releases) 0.6.8 or newer.
- `Mass Effect AP Setup.exe` (from the release zip). ME3Tweaks Mod Manager is optional.

## Install

Close Mass Effect 3 and the Archipelago client, run `Mass Effect AP Setup.exe`, pick **Mass Effect 3**, then:

1. **Folders:** check the detected Mass Effect LE and Archipelago folders.
2. **Install:** installs the world into Archipelago, the bridge (`LE3APBridge.asi`) and the `DLC_MOD_ArchipelagoME3` mod
   into ME3, and an ASI loader if ME3 has none. Anything replaced is backed up; Uninstall restores it.
3. **Options:** set your options and slot name, then Save (or Save + Generate).

## Play

1. Open **Mass Effect LE3 Client** from the Archipelago launcher and connect to the room. On first connect it writes an
   ME2 career for this seed (the log names it) into your ME2 save folder.
2. Start Mass Effect 3, choose **New Career**, import that ME2 career and finish the character creator. The mod skips the
   prologue and starts you on the Normandy. The client links that career to your slot; it never touches careers started
   without the mod.
3. If the game is silent when the Normandy first loads, save and reload once (known issue).

Items arrive while you play. Mars is on the galaxy map from the start; Cronos Station and Earth open once you have
the required Crucible Intel. Missed checks on finished missions can be bought at the Normandy store terminal
("<mission> Salvage").
