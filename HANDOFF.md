# Historical LE3 work log — started 2026-10-14

**For the 2026-10-20 Claude Code transfer, start with `CLAUDE-HANDOFF.md`.** This log's fixed-preset-only scope and earlier pending runtime requests are obsolete. The newest career observer source is uncompiled/uninstalled; see the transfer handoff before building native code.

**Read `CURRENT-STATUS.md` first.** It supersedes the pending test requests and provisional statements below. On2026-10-16 the owner confirmed the native delivery/reload test already succeeded; disk recovery found all20 persistent fields in Save61. Do not request a repeat. The new receive-only AP client passes24 tests/102 generation subtests and a real localhost AP test with a fake native endpoint. This document retains earlier chronological notes for reference, including obsolete pending instructions.

## User scope and decisions

- Build a PC Mass Effect 3 Legendary Edition Archipelago mod/world; maximize granular optional check coverage.
- Begin with feasibility; that overview is complete in `ME3-FEASIBILITY.md`.
- Investigate Galactic Readiness/war effort for additional checks.
- User confirmed: **maximum-content Shepard history first, configurable history later** (`DECISIONS.md` D1).
- User requested locating/understanding actual checks **and general functionality**, and authorized a bounded session of planning/code exploration while asleep. Initial research stayed in the workspace; the later live-path follow-up installed the reversible read-only test setup documented below.

## Actual current state

### Current task: 0.2.0 development delivery spike (2026-10-15)

User said to keep going. Implemented SDK-independent `tools/le3apbridge/Delivery.hpp` plus native host/DEV commands in Bridge.cpp, using ME2's indexed transaction pattern. Full identity/history digests are preserved as eight signed-bit-pattern integer words each. Current-save identity is checked on the game thread for every mutation (including retries after a save switch); gaps/wrong identity/foreign storage are refused. Only COUNTER and bounded CREDITS exist; no generic setters, mission gate or initialized Shepard history. Research mode is explicitly stored and reported; the normal AP client's ResearchBridge remains disabled.

Storage: sparse integer-map keys **0x4D336000..0x4D336017**, 24 keys. SDK SaveGame.PlotTableSaveRecord stores a TArray<FIntVariablePair> with 32-bit Index/Value, not a dense array. Full audit scanned 4,454 PCCs plus native executable, 68,271,184,651 decompressed export/raw bytes, zero errors. Forty-two raw matches were graphics/audio payloads: typed IntProperty/function/native/config/DB references zero. All 21 coalesced files/1,817 sections checked. `research/le3_delivery_storage_audit_summary.json` and review records retain evidence and limits (official supplied data only; computed IDs/third-party mods not proven). The dev build requires a matching audit. Runtime high-key serialization remains untested.

Both profiles compile; 35 native transaction assertions pass in each (duplicate/lost-reply retry, old-save replay, wrong seed/history, queued-save-switch rejection, cap consumption, missing pawn, malformed op, failed commit restoring cursor/balance). Build logs: `research/le3_delivery_build.log`, `le3_research_build_020.log`. Development SHA256 **0138523b56a27ab9a77c1ddc638ad34f8a2d47166fdedb0ac516f331bfe8b614** in `tools/le3apbridge/build-delivery/bin/Release/LE3APBridge.asi`; read-only0.2.0 SHA256 **29ca2f8d5b247e62e5e59dffa5f860f83816c00c3505597be0ed7d5ca1d59e9b** in normal build path. Write callbacks and parse gate reject mutations unless CMake LE3AP_DELIVERY_DEV is ON (default OFF). Native credits use type0 AdjustResource, notification=false, ignoreBudget=true; validate actual clamped delta, consume capped filler so intel cannot be blocked, restore credits/cursor on commit exception. No runtime credit effect yet claimed.

Installer gained explicit `--delivery-dev` selection; five isolated installer/rollback tests pass. Original test Save60 was copied and hash-verified into `build/test-save-backups/pre-delivery/Save_0060.pcsav`, receipt `research/le3_pre_delivery_save_backup.json`. User confirmed ME3 closed, then development ASI was installed with `install_research.py update --delivery-dev`; previous read-only0.1.2 archived automatically, loader unchanged, installed receipt updated. **Currently awaiting the user's reply to: launch ME3, load Save60 from the medkit/Cain test, leave Shepard idle.**

Next commands (escalation required for pipe):

1. `python tools/le3apbridge/delivery_probe.py inspect research/delivery_inspect_01.json` — verify version, unbound session, actual wallet/cap BEFORE writes.
2. `... bind-test-save research/delivery_bind_01.json` — binds only to default research-existing-save digest, NOT maximum-content history. If completed career or occupied fields, stop and investigate.
3. `... credits research/delivery_credit_01.json --index 0 --amount 1000` — applies once, retries the SAME index, verifies actual delta, cursor and unchanged pickup/GAW sources. If already capped, delta0 is correctly consumed but does not prove an increasing credit grant; report it accurately.
4. Ask user to create a NEW manual save, reload, inspect and retry index0. Verify binding/cursor/credits persist, inspect saved index/value pairs if needed. Then inspect the original pre-binding Save60 to test rollback/replay behavior, and explicitly reject wrong seed. Don't overwrite pristine Save60 or claim full AP playability.

`tools/le3apbridge/DELIVERY-PROTOCOL.md` defines exact commands/storage/limits. Probe seed identity uses the same SHA-256 canonical [seed,team,slot] payload as AP client_core; test history label is research_existing_save_v1_NOT_maximum_content. No AP server contact by the probe. Native ID/high-int storage/credits are pending live validation. Other broad work still remains maximum-content new-game initialization and real finale gating.

2026-10-15 ME2 reference update: user pointed out delivery work on their GitHub. Clean checkout `ME_Archipelago_Background` was fetched and fast-forwarded from98ca741 to **cab3dea3012acff9ae5609e805a1e1c2f770f1eb** (`claude/me2-ap-world`). New commits build the bridge with corrected resource enums, reject post-game binding, and document a live resource TXN/retry and save-persistence test. Review and LE3 adaptation map: `research/ME2-DELIVERY-PORT.md`. Local LE3 decompilation now confirms AdjustResource/GetResource and credit enum0 in `research/le3_delivery_api_scripts.jsonl`. Reuse ME2's indexed native transaction design; keep LE3's stronger identity/history contract, corrected SDK dispatch and separately audited state ranges. No native reward-writing build was installed in this review.

An experimental AP world and AP networking foundation now exist. The game-side history, identity, delivery and gate pieces are not implemented, so the integration is not playable end to end. Do not mark the overall goal complete.

The following now exist:

1. Feasibility, decisions, readable check catalog and functionality architecture (`ME3-FEASIBILITY.md`, `DECISIONS.md`, `CHECKS-CATALOG.md`, `FUNCTIONALITY.md`).
2. Reproducible offline catalog pipeline: `python tools/research/run_catalog.py`. Source backup/libraries are inputs only.
3. A **compiled and installed, runtime-unverified read-only LE3 ASI**: `tools/le3apbridge/build/bin/Release/LE3APBridge.asi`.
4. Research bridge source/build script and Python snapshot/diff helper in `tools/le3apbridge/`.
5. Focused offline tests: `python -m unittest tools.research.test_research -v`.
6. Source world `world/mass_effect_le3/`: append-only 527-source JSON ledger, shared detector data, category/DLC options, generation and client code, launcher component, setup docs and tests. Default pool 502; experimental weapon option adds 25. Optional/missable source families are filler-only; the 11 story predicates and 17 Mars objectives still need runtime confirmation.
7. Built `build/mass_effect_le3.apworld` plus development YAML and a real seed ZIP at `build/development_seed/AP_41961810824680882422.zip`. The source is synced into the local supplied AP checkout.

New validation: 15 world/client tests and 102 generation subtests passed, including a two-player fill. The archive itself imports JSON resources and generates from ZIP. A real AP localhost server round-trip with a **fake native bridge** reports one source location, receives its 1,000-credit item and applies it once; receipt `research/le3_local_multiworld_receipt.json`. Native behavior remains unverified.

Commands use the existing parent AP venv interpreter (`../vendor/Archipelago/.venv/Scripts/python.exe`) against this workspace's AP 0.6.9 source. System Python 3.14 is unsuitable for AP; use it only for standard-library research/build helpers. Run `tools/generate_development_seed.py` with the venv interpreter for real seed generation. `tools/test_packaged_world.py` validates archive import/resources. Full world/client tests and `tools/test_local_multiworld.py` require local socket access; Windows asyncio socketpair initialization hangs inside the restricted sandbox, so those tests were run with escalation. The stopped sandbox test session is terminal.

The user supplied the live installation: `C:\Steam\steamapps\common\Mass Effect Legendary Edition\Game\ME3`. On 2026-10-14 the read-only ASI and official-source LEBinkProxy were installed with the game closed. All installed hashes verified; `research/live_install_receipt.json` records them. Original DLL backup: `build/live-original/bink2w64.dll`; original also retained beside the proxy as `bink2w64_original.dll`. No saves or game packages were edited. **The game has not been launched or runtime-tested.** An asynchronous question asks the user to load a disposable test career and leave Shepard idle.

Install/inspect/restore helper: `python tools/le3apbridge/install_research.py inspect|install|restore`. Live writes require escalation. Restore refuses changed files. Three isolated installer tests passed, including failed-copy rollback. Official loader source is an unmodified checkout at `tools/vendor/LEBinkProxy`, commit `1c435d8df0367642d9fc8572b67b6ae92295967e`, version 2.0.0.11 / SPI 3. Build with `tools/le3apbridge/build_loader.py`; this build requires escalation because sandboxed compiler IPC fails with misleading LNK1101. All 75 Bink-prefixed original exports are forwarded by the proxy. The installed ASI's MSVC runtime dependencies exist on this machine.

Next runtime command once the user confirms gameplay is loaded: `python tools/le3apbridge/probe.py snapshot research/live_baseline_01.json --catalog-plots`. This includes all current location plot predicates and ending candidate 22426 as well as the normal GAW/GUID inventories. It never sends AP checks. Inspect `Binaries/Win64/bink2w64_proxy.log` and ASI logger output if the pipe fails. A baseline alone does not prove individual check transitions; take before/after observations around single actions and then save/reload.

End-of-batch validation: catalog pipeline succeeded with the unchanged reward scan reused; five focused tests passed; native bridge build succeeded. ASI SHA-256: `549cc50e611231f0c66504f859c903b69495cb85d3774b574bf4b5b50a187a44`. Build and catalog logs are retained under `research/`. These checks do not establish in-game behavior.

## Important verified static findings

### 2026-10-15 live test and repair

**Latest persistence result: passed for both witnessed pickups.** User created a NEW manual save and reported reloading it. `research/live_earth_reloaded_01.json` retains both GUIDs; selected bool/int/GAW values and GUID set are identical to `live_earth_after_pickups_01.json`. Packaged-detector replay now asserts the same two locations remain observed after reload and passes. It contacts no server.

Read-only disk evidence: latest manual `Save_0060.pcsav` contains both exact little-endian GUIDs at offsets50252 and50268, consecutive with a preceding uint32 count2. The earlier chapter save and pre-test manual Save_0055 contain neither GUID. Method, hashes and offsets are in `research/le3_pickup_save_bytes.json`; this is a targeted byte inspection, not a complete save-format parse. No save file was modified by tools or copied into the mod. Evidence `le3_live_check_evidence.json` and install receipt updated. A fresh-process reload and a separate-map persistence test were not performed; same-process manual save/reload plus disk serialization were verified.

Second bounded recorder completed normally: nine changed states, zero read errors (`live_earth_session_02/completed.json`). No recording remains active. User was told no more gameplay testing is needed for now. Next substantive development remains save-bound native seed/slot identity, indexed delivery, finale gate and coherent maximum-content new-game history; the read-only bridge deliberately implements none of those yet. Do not claim the overall randomizer complete or playable.

**Latest pickup result:** user reported “cain and med kit grabbed.” `live_earth_session_02/state_0008.json` first adds medkit GUID `942894881:1233733615:171160246:1774900978`, matching `BioD_End001_230Rooftop.pcc` export8613 `SFXMedkit_0.TreasureModule0`, AP ID1295192584. State0009 adds Cain GUID `-596417730:1180263863:1152395409:-954766686`, matching `BioD_End001_200AAGun.pcc` export3165 `SFXWeaponNode_0.WeaponUseModule0`, AP ID1295192353; bool19749 Cain_Recovered also goes0->1 and int10372 goes2->3. Full post-pickup snapshot: `research/live_earth_after_pickups_01.json`. Evidence: `research/le3_live_check_evidence.json`.

`../vendor/Archipelago/.venv/Scripts/python.exe tools/replay_live_pickups.py` replays actual before/after snapshots through the **packaged** AP detector. Passed: exactly those two new location IDs, no disappearing selected predicates. Receipt: `research/le3_live_detector_replay.json`. No AP server contacted, no rewards delivered. This validates native observation -> source ledger -> AP detector mapping, not a playable integration.

User was asked to create a NEW manual test save when allowed, reload it, and stand idle; options include saving disabled or testing later. **Await that reply; capture `research/live_earth_reloaded_01.json --catalog-plots` and compare both GUIDs.** Do not claim persistence until tested. A second bounded 300-second recording is/was running under exec session93288 at `research/live_earth_session_02`; inspect its `completed.json` or poll that session before deciding whether it still runs. First session completed ten changed states/zero read errors; its named analysis is now complete.

**Latest result: 0.1.2 full baseline succeeded.** `research/live_baseline_01.json` contains 21 bools, eight ints, 69 GAW IDs (23 zero-strength) and zero used GUIDs. `PLOTINFO` confirms `Default__BioGlobalVariableTable`, default=1, 786 bool words. All three native function flags equal 132096 (0x20400) before/after. The cause of continued 0.1.1 rejection was the generic default-object filter; this is now confirmed. `research/live_baseline_01_analysis.json` maps baseline presence to 17 bool, eight int and one GAW location candidates; these are observations, not AP reports or transition validation.

The user's available save is at the final Earth mission, so testing adapted to Earth entry. User started that mission and confirmed controllable Shepard on Earth. Bounded read-only recorder `tools/le3apbridge/watch_research.py` records all manifest predicates plus 215 End_Game bools/five ints, with GUID/GAW inventories, changed snapshots and deltas. Session `research/live_earth_session_01` captured Normandy -> `Biop_End001`, journal bool22737 0->1, opening combat19738, autosave19739, saving-disabled22209, current-objective int10372 0->1, shuttle liftoff19734 and enemies-retreat19765. `research/live_earth_transition_analysis.json` is an interim named interpretation; regenerate it from the final session deltas before treating it as complete. User was asked to report a Cain pickup or an interactable supply/medical cache. No pickup GUID has been observed yet. Do not require finishing the entire mission for the test.

New source decompilations: `research/le3_weapon_use_scripts.jsonl` and `research/le3_base_use_scripts.jsonl`. Weapon OnUsed calls Super.OnUsed -> SavedUse.Used **before** weapon-specific grant validation. Heavy weapon paths spawn/give and return early, but the inherited saved-use marking already occurred. Thus a GUID on the weapon path means interaction/marking, not proof the inventory grant succeeded; retain the experimental weapon-option caveat. Treasure differs: it records Used only after successful AwardResource.

User was asked asynchronously to collect exactly one fixed cache, armor/mod pickup or scan/probe recovery, then stand idle and describe what/where. Await that reply and take `research/live_after_action_01.json --catalog-plots`, then diff against the baseline. Save/reload persistence and GUID transitions remain unverified. Two Mars objective predicates (19972 Access Security, 20218 Attack Sniper) and Earth escape 18075 are false in this later-game baseline; investigate their lifetime/branching and the test save's history before calling those sources guaranteed. Do not treat a source label or positive mission int alone as completion-transition proof.

User loaded a test career. Sandbox access to the pipe failed with WinError 5; read-only probe commands work with escalation. Initial `--catalog-plots` snapshot failed with `ERR noplots`, but handshake/version, map `BioP_Nor`, GAW (69 entries, retaining zero-strength IDs) and USES (0 entries) responded. The inventory-only baseline is `research/live_inventory_baseline_01.json`. This does not validate any individual pickup transition or persistence.

Root cause found in generated SDK native wrappers: `FunctionFlags |= ~0x400` sets all other flags, and the subsequent OR leaves them set. The failed GetGlobalVariables call therefore altered in-memory function flags. User was asked to exit without saving and confirmed closed. Bridge 0.1.1 dispatches GetGlobalVariables/GetBool/GetInt directly through the original ProcessEvent trampoline using zero-initialized ABI-compatible parameter structs; no function flags are changed. Vendor source remains untouched.

Correction after the next live attempt: 0.1.1 was confirmed running (`VER`) on `BioP_Nor`, but still returned `ERR noplots`. The wrapper bug is real, but was not established as the cause of table rejection. Version 0.1.2 narrows the table check to non-null, non-destroyed, correct type; the authoritative accessor may return a class-default singleton, so the generic actor-instance `Live()` filter is inappropriate here. New `PLOTINFO` returns object name/default status/flags/bool-word count and the three native function flags. Null/destroyed/type failures now have separate error messages. The snapshot helper records version and before/after PLOTINFO when supported.

User closed the game again, then 0.1.2 SHA-256 `20b6c351d742920d94660a1531e64944eb31f04828fded025a3f8db85b676efa` was installed and the receipt updated. **Currently awaiting the user's relaunch reply for 0.1.2.** This supersedes the 0.1.1 pending status below. Do not claim plot reads or class-default status verified until the retest succeeds.

The rebuilt 0.1.1 binary SHA-256 is `56878ec42fc0a0bf07af31e007271bb6717fbc40c56edde62662df115c95e1fe`; installed with the game's process closed and a backup of the old ASI retained in `build/live-original/`. Receipt updated; original loader/game-DLL hashes unchanged. Four installer tests pass including update then restore. Native build needed escalation; sandbox MSBuild stalled and its three precisely identified build processes were stopped before a successful escalated rebuild. **Awaiting the user's fresh-process relaunch reply for the plot-read retest.** Do not claim the fix runtime-verified yet. Next command remains `python tools/le3apbridge/probe.py snapshot research/live_baseline_01.json --catalog-plots` with escalation.

- 268 distinct GAW config IDs; 96 are modifiers with 106 target edges. Twenty-nine edges are negative consequences. Normalize enum case: two military definitions spell the enum differently.
- `UnlockPlotStates` are bools **set by** an asset award, not prerequisites. Local decompilation proves that distinction.
- `UnlockGAWAsset` stores modifier IDs in the unlocked array before updating recipient strength. Zero-strength entries must be retained by detection.
- The highest-mounted local official galaxy-map package is in `DLC_METR_Patch01`, priority 4000. It contains 76 named/config-linked recovery candidates and one unnamed placeholder under always-false usability. Never sum the five map versions together.
- `PlanetLandCondition=False` is not a reason to exclude a scan/probe recovery. Visibility/usability and landing are separate concerns.
- The reward-class scan read 3,229 non-localized packages with zero errors. After local mount resolution: 1,457 matching objects, including 442 selected use modules. Of those, 423 have distinct valid world-instance saved-use GUIDs. Nineteen missing-GUID matches are prefab/template paths needing further investigation.
- Selected mounted use modules: 320 treasure (301 explicit valid GUIDs), 70 mod, 27 armor, 23 weapon and two bonus-weapon. Heavy/special weapons still need eligibility review.
- 229 GAW award nodes and 632 mission-XP nodes are source candidates, not independent checks by count. Enemy-equipping `GiveWeapon` nodes are not player pickups.
- `SFXModule_SavedUse` uses `SFXEngine.UseModuleList`; `SFXSaveGame` declares `UseModuleRecords`. Treasure `OnUsed` marks completion only after `AwardResource` succeeds. Runtime persistence still needs testing.
- ME2 AP bool range 21000–21999 overlaps 900 LE3 plot DB entries.

## Tooling and build

LExASIs dependency: `tools/vendor/LExASIs`, commit `aaad03ab6e5112e27ff5528f7b08c3bcf3870c31`; SDK submodule `3885be14113816ff1d2a0d941aa96bba6df9dc58`.

Build: `python tools/le3apbridge/build.py`. Visual Studio 2026 C++/Windows SDK are present. Initial CMake detection failed because the host passed both PATH and Path; the build helper normalizes the child environment and succeeds. It disables upstream automatic game-copy hooks.

Pipe: `\\.\pipe\LE3APBridge`. Protocol: HELLO/PING/VER/CAPS, GETB/GETBS/GETI/GETIS, MAP, GAW, paged USES. Game reads drain at BioHUD.PostRender, so no HUD callback means timeout. The ASI has no setters or reward operations. It compiles against the real LE3 SDK; this is not runtime proof.

ME2 reference checkout remains unmodified at `ME_Archipelago_Background`, branch `claude/me2-ap-world`, commit `98ca74111b5ee2a32bc6b4384c430fa9dd47613c`. Its bridge is uncompiled/unrun according to its own README; treat it as a design reference.

## Next useful work

1. Review `CHECKS-CATALOG.md` and generated source tables; extend discovery to other saved-use subclasses, normal weapon/scripted reward paths, journal/assignment states, shops and DLC activities.
2. Trace plot/conditionals and sequence flow into availability rules. Split retrieval/delivery/use only where they are distinct player actions. Map objective-XP nodes to actual meaningful milestones.
3. When the owner returns, use a disposable LE3 test career to validate the read-only bridge and saved-GUID/GAW observations, following the bridge README. Do not claim source checks verified before this.
4. Trace the new-game initialization methods named in `FUNCTIONALITY.md`, then implement a coherent maximum-content preset before derived game state initializes.
5. Complete the native contract used by `client_core.py`: full seed/slot identity, matching history digest, indexed credits/counter delivery, and a finale gate. The current `ResearchBridge` adapter refuses to send checks or rewards without those features; replace it only when the actual native contract exists.
6. Validate mission-order integer predicates and the named Mars objective bools, trace actual final-decision bool 22426, and broaden safe progression placement only after availability evidence. Generation rules preserve eventual vanilla access and add an AP gate to Cerberus HQ/Earth Finale; the game does not enforce that gate yet.

Additional static evidence: `research/le3_history_config.jsonl` shows native ME1/ME2 canon plot arrays. `SetNewGamePlotStates`, `ApplyCanonPlots` and ME2 import/fixup are native methods, so a safe initialization hook must account for native paths. `research/le3_campaign_scripts.jsonl` confirms GAW save/load copies the unlocked ID/strength records. `research/le3_leave_mission.jsonl` records the generic leave-mission flow; it increments mission count but does not alone prove every mission-order integer predicate.

Evidence status is intentional: `DB_ONLY`, `CONFIG_ONLY`, `PACKAGE_AND_CONFIG`, saved-GUID candidates and sequence candidates all precede runtime validation. Raw counts must not be advertised as a final check count.
