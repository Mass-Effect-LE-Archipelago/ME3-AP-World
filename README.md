<div align="center">

# Mass Effect 3 Legendary Edition &middot; Archipelago

**Unite the galaxy and build the Crucible, with your weapons, missions and war intel scattered across an
[Archipelago](https://archipelago.gg) multiworld.**

[![Latest release](https://img.shields.io/github/v/release/Mass-Effect-LE-Archipelago/ME3-AP-World?label=release)](https://github.com/Mass-Effect-LE-Archipelago/ME3-AP-World/releases/latest)
[![Launcher](https://img.shields.io/github/v/release/Mass-Effect-LE-Archipelago/ME-Archipelago-Launcher?label=launcher)](https://github.com/Mass-Effect-LE-Archipelago/ME-Archipelago-Launcher/releases/latest)
![Archipelago](https://img.shields.io/badge/Archipelago-0.6.8%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20(PC)-lightgrey)

</div>

> [!WARNING]
> This is a **beta**. Expect rough edges, and please report what you find. It is an unofficial fan project, not
> affiliated with or endorsed by BioWare or Electronic Arts, and it contains no game assets. You need your own PC copy
> of Mass Effect Legendary Edition.

## Contents

- [Overview](#overview)
- [Setup guide](#setup-guide)
- [Options](#options)
- [Repository layout](#repository-layout)
- [Development](#development)
- [Part of the trilogy](#part-of-the-trilogy)
- [AI Disclosure](#ai-disclosure)

## Overview

### What gets randomized

- **Weapons.** You start with only the M-3 Predator. Every other loadout weapon is an item somewhere in the multiworld.
- **Missions.** Side missions (Grissom Academy, the Monastery, Jacob's scientists, the Attican Traverse, the N7
  missions, Eden Prime and Omega) open on the galaxy map when their **Mission Access** item arrives, in any order. The
  Krogan arc (Palaven, Sur'Kesh, Tuchanka) and the Geth arc (Dreadnought, Rannoch) need **Story Arc** items and keep
  their story order.
- **Crucible Intel**, which opens the endgame, plus credits.

### What counts as a check

| Family | Examples | Default |
| --- | --- | --- |
| Objectives | Mission objective steps and story milestones | On |
| Credit and supply caches | Credit caches, supply and medical stations | On |
| Armor and weapon mods | Armor pieces and weapon mods placed in missions | On |
| Exploration | The 76 named galaxy-map recoveries | On |
| Codex | Codex pages unlocked after the start (never progression) | On |
| War assets | "War Asset 1" through "War Asset N", one step per war asset or upgrade you gain | 80 |
| Weapon pickups | Placed weapons, including heavy and special weapons | Off |
| DLC | From Ashes, Leviathan, Omega, Citadel | All enabled |

### Goal

Collect the required **Crucible Intel**. Cronos Station (Cerberus Headquarters) and Earth stay locked on the galaxy map
until you have it. Then finish the game.

### How it plays

- **Earth is skipped.** You import an ME2 career, and the mod starts you on the Normandy with Mars on the galaxy map.
- **Your history comes with the seed.** Shepard's ME1 and ME2 history is a fixed "maximum content" history. The client
  writes it as an ME2 career for you to import, so no particular save of your own is needed beyond one finished ME2 LE
  game to use as a template.
- **Peace on Rannoch is always possible.** The mod always offers, and always succeeds with, the peace option.
- **Missed something?** Once you've been on a mission that can't be replayed, the Normandy's store terminal sells
  "&lt;mission&gt; Salvage". Each purchase sends one check you left behind there.
- **Your normal saves are safe.** The client only links careers started with the mod.

## Setup guide

The [**Mass Effect Archipelago Launcher**](https://github.com/Mass-Effect-LE-Archipelago/ME-Archipelago-Launcher/releases/latest)
is the recommended way to install, update and play. It downloads this project's newest release, verifies it, installs
it with backups, writes your player options and starts the game with its client.

### Requirements

- Mass Effect Legendary Edition (PC), with Mass Effect 3 installed.
- At least one **finished** Mass Effect 2 LE save in which Shepard survived. The client uses it as the template for
  your seed's import career. (Copying any finished ME2 LE save into your ME2 save folder works too.)
- [Archipelago](https://github.com/ArchipelagoMW/Archipelago/releases) 0.6.8 or newer.
- Nothing else. ME3Tweaks Mod Manager is **not** required for ME3: the launcher adds its own ASI loader when no other
  loader is present.

### 1. Install with the launcher

1. Close Mass Effect 3 and any open Archipelago client.
2. Download `Mass-Effect-Archipelago-Launcher.exe` from the
   [launcher's latest release](https://github.com/Mass-Effect-LE-Archipelago/ME-Archipelago-Launcher/releases/latest)
   and run it. It is self-contained, so there is nothing else to install.
3. Pick **Mass Effect 3** in the campaign list on the left.
4. Open **Folders** and check that your Legendary Edition and Archipelago folders were detected. Browse to correct
   them if needed.
5. Open **Deploy** and click **Deploy**. The launcher downloads the newest ME3 release, checks it against its SHA-256,
   and installs:
   - `mass_effect_le3.apworld` into Archipelago's `custom_worlds` folder,
   - the game bridge `LE3APBridge.asi` into `Game\ME3\Binaries\Win64\ASI`,
   - the `DLC_MOD_ArchipelagoME3` game mod, and
   - the AP ASI Loader (`bink2w64.dll`), only if no other loader is installed.

   Anything replaced is backed up. **Uninstall** puts every file back. When a newer release is published, the button
   reads **Update**.

### 2. Create your player options

1. Open **Options** in the launcher.
2. Pick a preset (**Story Focus**, **Completionist** or **Everything**) or set each option yourself. Hover any option
   to read what it does.
3. Enter your slot name and click **Save to Players**. This writes your YAML into Archipelago's `Players` folder.

### 3. Generate and host the seed

Whoever hosts the multiworld collects everyone's YAMLs and runs Archipelago's **Generate** with this world in
`custom_worlds`. To host online, upload the resulting `AP_*.zip` at [archipelago.gg/uploads](https://archipelago.gg/uploads)
and create a room. Everyone then connects to the address the room shows (for example `archipelago.gg:12345`).

### 4. Play

1. In the launcher, click **Launch** with the client box ticked. This starts Mass Effect 3 and the
   **Mass Effect LE3 Client**. (You can also open the client from Archipelago's own launcher.)
2. In the client, connect to the room with your slot name. On first connect it writes your seed's ME2 career into your
   ME2 save folder and names it in the log.
3. In Mass Effect 3, choose **New Career**, import that ME2 career and finish the character creator. The mod skips the
   prologue and starts you on the Normandy. The client links the career to your slot.
4. Play. Items arrive while you play, and Mars is open on the galaxy map from the start.

### Troubleshooting

- **No audio when the Normandy first loads.** This is a known issue with new careers. Save and reload once.
- **The client says it could not write the ME2 import save.** It needs a finished ME2 LE save to use as a template.
  Finish ME2 LE once, or copy a finished ME2 LE save into your ME2 save folder, then reconnect.
- **I use ME3Tweaks Mod Manager for other mods.** That's fine. Mod Manager may replace the AP ASI Loader with its own;
  its loader also loads the bridge. Mod Manager users can also install the `ArchipelagoME3` folder from the release
  payload through Mod Manager directly.
- **Logs.** The launcher keeps downloads in `%LOCALAPPDATA%\MassEffectAPSetup\downloads` and install records and
  backups in `%LOCALAPPDATA%\MassEffectAPSetup\ME3`.

## Options

| Option | What it does | Default |
| --- | --- | --- |
| `crucible_intel_total` | Crucible Intel items in the pool (1-24) | 16 |
| `crucible_intel_required` | Crucible Intel needed before the final assault (1-24) | 12 |
| `objective_checks` | Mission objective steps are checks | On |
| `credit_checks` | Credit caches are checks | On |
| `supply_checks` | Supply and medical stations are checks | On |
| `armor_checks` | Placed armor pieces are checks | On |
| `mod_checks` | Placed weapon mods are checks | On |
| `weapon_checks` | Placed weapons, including heavy and special weapons, are checks (experimental) | Off |
| `exploration_checks` | The 76 named galaxy-map recoveries are checks | On |
| `codex_checks` | Codex pages are checks (never progression) | On |
| `war_asset_checks` | Number of progressive "War Asset" checks (0-150, 0 turns them off) | 80 |
| `weapon_items` | Start with only the Predator; every other loadout weapon is an item | On |
| `mission_access` | Side missions and the Krogan and Geth arcs open through items | On |
| `salvage` / `salvage_price` | Buy back missed checks at the store terminal, and their price per check | On / 1000 |
| `enabled_dlc` | Which DLC campaigns add checks | All |

## Repository layout

| Path | Contents |
| --- | --- |
| [`world/mass_effect_le3`](world/mass_effect_le3) | The Archipelago world (items, locations, logic, options), the Mass Effect LE3 Client and the history/import-save writer |
| [`tools/le3apbridge`](tools/le3apbridge) | Game bridge (ASI plugin) that the client talks to ([delivery protocol](tools/le3apbridge/DELIVERY-PROTOCOL.md)) |
| [`tools/le3mod`](tools/le3mod) | Builder for the `DLC_MOD_ArchipelagoME3` game mod (Earth skip, galaxy-map gates, Rannoch peace) |
| [`tools/me2save`](tools/me2save) | ME2 save reader and writer used for the import career |
| [`tools/research`](tools/research) and [`research`](research) | Read-only discovery tooling and the evidence it produced |

Design notes: [check catalog](CHECKS-CATALOG.md), [functionality](FUNCTIONALITY.md), [decisions](DECISIONS.md),
[history selector](HISTORY-SELECTOR.md), [feasibility](ME3-FEASIBILITY.md) and [current status](CURRENT-STATUS.md).
Contributors working with Claude Code should start from [CLAUDE-HANDOFF.md](CLAUDE-HANDOFF.md).

## Development

Build the `.apworld` with:

```sh
python tools/build_apworld.py --sync
```

This writes `build/mass_effect_le3.apworld`. Tests live in `world/mass_effect_le3/test` and run inside an
Archipelago 0.6.8 or newer checkout with the world linked into `worlds/`, the same way as the
[ME2 world](https://github.com/Mass-Effect-LE-Archipelago/ME2-APWorld#development).

Bug reports and feedback are welcome in [Issues](https://github.com/Mass-Effect-LE-Archipelago/ME3-AP-World/issues).

## Part of the trilogy

| Game | Project |
| --- | --- |
| Mass Effect 1 | [ME1-APWorld](https://github.com/Mass-Effect-LE-Archipelago/ME1-APWorld) |
| Mass Effect 2 | [ME2-APWorld](https://github.com/Mass-Effect-LE-Archipelago/ME2-APWorld) |
| Mass Effect 3 | **ME3-AP-World** (this project) |
| Launcher | [ME-Archipelago-Launcher](https://github.com/Mass-Effect-LE-Archipelago/ME-Archipelago-Launcher) |

## AI Disclosure
AI was used to aid in the research and development of this multiworld.
