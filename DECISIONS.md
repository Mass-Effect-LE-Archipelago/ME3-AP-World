# Project decisions

## D1 — Seed creation includes selectable Shepard history

Updated by the user on 2026-10-16: include a history selector for major decisions, romances and related background so the randomized campaign retains the player's Mass Effect story. This supersedes the 2026-10-14 fixed-preset-first decision.

Retain maximum-content as a convenient preset, alongside explicitly selected custom history. Resolve the complete inherited history before generating the location pool or placing progression. Store that resolved profile in slot data and bind it to the career. Apply it during AP career creation before dependent ME3 state initializes. Retain character customization where it does not affect story/romance eligibility.

The selector must validate mutually exclusive outcomes, survivor/loyalty/romance dependencies, and resulting check availability. Exclude genuinely unavailable checks rather than overriding the player's chosen past. Expose options only when their native initialization and affected-source rules are mapped. ME3 decisions during gameplay remain player choices; timed/mutually exclusive current-game checks require separate rules. See `HISTORY-SELECTOR.md` for the design and implementation order.

## D2 — Granular check coverage is the primary catalog objective

User priority: “the most checks it can have” and minute options for check families. Catalog individual recoveries, rewards and reinforcement sources rather than stopping at mission completions. Optional finite milestones can supplement distinct interactions. Definitions and raw flags are research evidence, not approved checks.

The user suggested Galactic Readiness as an additional check source. Investigate GAW assets, modifiers, discoveries, intel and military-strength milestones separately.

## D3 — Apply seed history through a generated ME2 import save (adopted 2026-10-24; import proven live)

The owner proposed shipping a generated ME2 LE end-game save in the seed ZIP instead of writing history at ME3 career creation. Reason: the 2026-10-24 live trace (`research/career_trace_01*.json`) showed fresh non-import careers get their Virmire state from the Genesis comic after `FinalCommit`, so the planned post-`SetPlotChoices` seam is not the last writer. Importing runs ME3's own `CopyAndUpdateME2ImportData`/`SetNewGamePlotStates` path, skips Genesis and needs no native ME3 story writes. Pending feasibility: write a valid ME2 LE save (format/checksum), confirm ME3 imports an edited save, then map the history schema to ME2 plot state. Needs an owner-supplied post-Collector-Base ME2 save as a template; the original is never modified.

Extension proposed by the owner the same day: a standalone desktop "options creator" (like FF12Rando's generator) writes the player YAML **and** the matching ME2 import save from one fully resolved history profile, asks for the Mass Effect LE folders, and places the save in a new ME2 career folder (never overwriting existing saves). The YAML stays hand-editable and generation still validates it; the client verifies the imported career's history digest before binding. Build order: save write/import proof first, then the app.

## D4 — One standalone setup app replaces Mod Manager for players (owner, 2026-10-26)

A single external .exe does everything a player needs: (a) builds and installs the game-side mod and bridge into ME3 (built from the player's own game files, so no game data is shipped), (b) writes the player YAML (and can run a local generation), (c) writes the matching ME2 import save into a new career folder, and (d) launches the game. ME3Tweaks Mod Manager is not required; the app reimplements only what we need (DLC folder copy, TOC handling, ASI loader/bridge with hash-verified install/restore). Open implementation choice: stack and how the Python world and the app share the history mapping.

## D5 — Open mission order with a Predator start (owner direction, 2026-10-27)

Any galaxy-map mission may come first: the career starts with only the M3 Predator, and other weapons become checks/items. Companions are planned as items (selectability), but missions with a story-fixed squad (Mars: Virmire survivor + James) force that squad and should skip the squad/armory screens. Non-interactive cutscenes without dialogue choices (relay jumps, pre-Mars approach) are to be skipped where it is safe. Implementation pending research; see CURRENT-STATUS to-do.

## D6 — Codex pages as checks (owner direction, 2026-10-28)

Option `codex_checks` (default on): 66 checks, one per codex page title that a vanilla conversation or Kismet plot
transition grants after the start. Codex page ids are their plot bools (BioCodexMap); setters come from
`le3mod boolsetters` over every runtime-winning package including the `_LOC_INT` conversation packages
(research/le3_codex_setters.tsv). Variants of one title are one `bool_any` check; pages only the skipped Earth prologue
grants are left out. Region: the Normandy or Citadel hub if a setter lives there, else the mission. Codex checks never
hold progression (some come from optional conversations). Pages that a new career already has would be free checks;
confirm with a live read at the first Normandy load.

## D7 — Missed-checks salvage at the Normandy store (owner direction, 2026-10-28)

Options `salvage` (default on) and `salvage_price` (free/500/1000 default/2500/5000 credits per check). Each mission
that can't be replayed (`data.SALVAGE_MISSIONS`, 25) gets "<mission> Salvage" rows in the Normandy store terminal
(BioD_Nor_500, one TYPE_QUEST row per price tier). A row shows while its tier bool and the mission's available bool
are set and its bought bool is clear; buying charges the price and sets the bought bool. The client publishes
availability (mission visited = any of its checks done, and checks left) and takes purchases with bridge 0.2.3
`DEV_SALVAGE`, sending the lowest open location of that mission. Plot bools 26000-26084 (bought 26000+k,
available 26040+k, tier 26080+t); conditionals cannot read the sparse int keys (LEC compiler limit 250000).
Untested in game: nested-category store rendering a top-level quest row, and the store's markup on Normandy prices.
