# Integration functionality and implementation seams

Updated 2026-10-14. This distinguishes what exists from the remaining playable integration.

## Current working components

- Offline tools read LE3 packages, config, mounts, plot DB and English names into reproducible source catalogs.
- The LE3 research ASI compiles using LExASIs/LExSDKv2. It exposes a local read-only named pipe for map, plot, GAW and used-GUID data.
- The Python snapshot/diff helper batches reads and compares individual source GUIDs, asset IDs/strengths and selected plot values.
- Parsing and offline data checks pass. No game-facing operation has runtime evidence yet.
- An AP-registered experimental world selects 502 checks by default or 527 with weapon interactions, models a Crucible Intel finale requirement, and generates real seed ZIPs. Optional pickup/exploration sources remain filler-only pending availability audits.
- The AP client/core verifies source-manifest identity, models save-bound indexed delivery and translates GUID/GAW/plot observations to server locations. Its current native adapter deliberately refuses synchronization because the research ASI has no save identity or delivery operations.
- A real localhost AP server/client round-trip reports a source check, receives its credit item and applies it exactly once to an explicitly fake native bridge. This verifies networking, not ME3 gameplay.

## Intended play loop

1. Generate a seed using a versioned maximum-content Shepard history and selected check categories.
2. Start a new AP career. Initialize the resolved history before ME3 derives the starting journal, cast and war assets; bind the save to the generated slot.
3. The ASI observes saved native state and instruments additional source events. It remains active if the external AP client disconnects.
4. The AP client maps completed source identities to stable location IDs, reports new checks and reconciles the server's checked-location set on reconnect.
5. Received items are delivered on the game thread using an indexed, retry-safe transaction. The reward and received index must have proven compatible save semantics.
6. Mission access and finale availability combine required native story conditions with the slot's AP requirements.
7. The client reports victory only after observing the configured game goal. A generated world and fake client test are insufficient to prove a playable campaign.

The current ASI implements only the reads in step 3. Seed generation and an AP networking foundation now exist; native save binding, history, item transactions, gate enforcement and actual victory observation remain to implement/validate.

## Detectors

Use native persistent source identities where available:

| Action | Candidate detector | Evidence / remaining proof |
|---|---|---|
| Fixed supply/armor/mod/weapon interaction | Saved use GUID | Local script plus source GUIDs; prove save/reload and successful-use behavior per family |
| GAW recruitment or reinforcement | Presence of that GAW ID, including zero-strength modifiers | Local `UnlockGAWAsset` script stores each awarded ID; prove save serialization |
| Planet recovery | GAW ID plus source mapping | 76 named package/config-linked sources; trace conditionals and scan/probe timing |
| Intel use, quest delivery, story completion | Source-specific bool/int predicate | DB and sequence evidence; observe each accepted predicate |
| Event with no lasting native state | Mod-owned saved latch | Storage/collision/serialization work required |

`UnlockPlotStates` are output effects of an asset award, not conditions that make the award available. AP item grants must not satisfy a native pickup check by merely setting a shared ownership flag.

## New-game history

The LE3 SDK exposes `BioGlobalVariableTable.SetNewGamePlotStates`, `ApplyCanonPlots`, `DoME2PlotImport`, `CopyME2PlotData`, `MergeME1PlotRecord` and related history accessors. These are concrete starting points for tracing initialization order. Their presence does not establish the correct insertion point.

The accepted first-release design is one maximum-content preset. Trace a coherent set of survival/loyalty/past-choice values, apply it once during career creation, and validate the resulting journals, available characters, missions and initial assets. Preserve customization where it does not affect logic. Historical baseline assets/codex must not be mistaken for actions performed during this seed.

## Items and gates

The refreshed ME2 branch (`cab3dea`, `claude/me2-ap-world`) is the native delivery reference: a whitelisted indexed TXN compares the save cursor, applies one operation and advances the cursor on the game thread; retries skip already committed indices. Its live-test notes report a resource TXN/retry and save persistence. LE3's existing client core follows that contract; native implementation should adapt it rather than invent a second receipt mechanism. See `research/ME2-DELIVERY-PORT.md` for the exact port map and remaining LE3-specific validation. Local decompilation confirms LE3 AdjustResource/GetResource and credit type0; a credit grant must handle budget bypass and the credit cap explicitly.

Build delivery around LE3's actual inventory and reward methods. The decompiled treasure interaction calls `SFXInventoryManager.AwardResource`; the LE2 resource enum and grant semantics must not be assumed interchangeable. Weapon/armor/mod ownership, ranks and fixed pickups need distinct handling. Preserve a viable starting loadout and forced story equipment.

For initial access randomization, retain vanilla ordering and AND AP permissions with native mission visibility/usability. Inspect the winning map package and DLC overrides. Broad arbitrary mission-order randomization would require a separate scheduler and script-compatibility effort.

Any AP-owned save fields need a new collision audit. The ME2 bool block overlaps 900 LE3 DB entries. Select an unused range only after inspecting native/DLC references and supported mods, then test whether it serializes and survives old-save replay. A sidecar ledger requires save-specific identity and rollback handling; it cannot simply use one global JSON file for every career.

## Runtime validation sequence

First validate read-only snapshots on a disposable test career. Match a successful credit/medical interaction, armor/mod pickup and scan recovery to catalog identities; test full inventory, map transitions, helper disconnect and save/reload. Then test baseline history initialization. Only then add identity binding, one reward transaction and a small real AP campaign slice, expanding the check catalog without renumbering public IDs.

See `tools/le3apbridge/README.md` for commands. The read-only bridge is installed with verified backups. On 2026-10-15 the global plot singleton, map and GAW channels worked in gameplay; bounded Earth recordings captured mission-state transitions. The rooftop medkit and AA-gun Cain GUIDs matched source objects and the packaged AP detector, survived a new manual save/reload, and were found serialized in the new save. Other source families and persistence scenarios still need coverage before generalizing this evidence.
