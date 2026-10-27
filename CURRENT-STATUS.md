# ME3 development status — 2026-10-16

Update 2026-10-20 (Claude Code): `build.py --career-trace` builds the observer cleanly into `build-career` (/W4 /WX); 19 CareerTraceTests and 35 DeliveryTests pass. Pinned ASI SHA256 `5a645f7a3e623e1c3c45988043dadc13e2fe04eded1ab8fab75f23073dffce81`, copied to `build/live-original/`. `install_research.py --profile career-trace` and `career_trace_probe.py` (offline tests in `test_career_trace.py`; 12 Python tests pass with the installer tests) now exist. It is **not installed**: the live `bink2w64.dll` and `bink2w64_original.dll` were replaced on 2026-10-18 (ME3Tweaks LEBinkProxy 2.0.0.14) and a new `lemp.asi` appeared, so the receipt no longer matches and the installer correctly refuses updates until the owner approves a re-baseline. Mission gate source evidence: `research/le3_mission_gate.md`. Git: this folder has no repository of its own; it is an untracked 44 GB directory inside the APWorldMaker repo, so nothing here is committed yet.

## Where things stand — 2026-10-26 (paused for the night)

- History: D3 adopted. Seed history goes in through a generated ME2 import save (`tools/me2save`, `world/mass_effect_le3/history_save.py`). Import tests 01 and 02 passed live (40/40 flags). Player-record origin/notoriety bytes were added after test 02 and still need one live import.
- Earth skip: `tools/le3mod` 0.0.1 (C#, LegendaryExplorerCore) rewires BioP_Char so imported careers fire Virmire-survivor + James squad transitions and load BioP_Nor. It was installed by plain folder copy into `BioGame/DLC/DLC_MOD_ArchipelagoME3` (receipt `research/le3mod_install_receipt.json`). **Not yet run in game**: next step is the owner importing a career and reporting (start OK? landed on Normandy? weapons? galaxy map?).
- Mars: not landable in vanilla (Sol BioPlanet_3, no MapName). Planned le3mod step: give it `BioP_ProMar` plus an AP landing conditional in the galaxy map package. Map hand-offs are config (`SFXSeqAct_LeaveMission.LeaveMissionArray`): ProEar->ProMar->CitHub->Nor.
- Gate fix: Cronos Station is `BioP_Cat004` (End001 is Earth). Bridge source gates both; not rebuilt/installed. The live ASI is still the read-only career-trace build.
- D4: one C# setup app (owner chose C#) will install mod+bridge, write YAML, write the ME2 save, and launch the game; not started.
- The 37 GB `ME3LE Backup` folder is missing (owner not yet asked back); tools fall back to the installed game, which has `DLC_MOD_LEMultiplayer`.

## Owner to-do list (le3mod / setup app)

- Skip the mass relay jump cutscene when traveling between clusters (owner request 2026-10-27).
- D5: start with the Predator only; other guns as checks; any planet first.
- Mars (and other fixed-squad missions): force the story squad and skip squad selection + armory (BioP_ProMar has a 'Need Hench GUI' sequence variable to research).
- Skip non-interactive cutscenes with no dialogue choices (e.g. Normandy/shuttle approach before Mars).
- Companions as items: selectability via the Is_Selectable transitions (49-54, 252/253 Tali, 66/67 James).
- Mars: verified live 2026-10-27 (0.0.4) - lands, full opening plays, Mars gives Predator + Katana, loads with Kaidan + James (Liara picked = load hang). 0.0.5 staged: Liara not selectable before Mars (transition 49).
- Weapons: Normandy start has none; harmless if Mars is first, but Menae etc. are offered before Mars. Either gate pre-Mars missions (AP logic) or grant Earth's Avenger/Predator.
- Isolate the audio pop/boom on focus (suspect the re-saved galaxy map packages).

## User direction

Build a Mass Effect 3 Legendary Edition Archipelago mod/world, prioritizing the largest practical catalog of granular optional checks. Updated2026-10-16: include a seed-creation history selector for major decisions, romance and related inherited story. Maximum-content remains a preset; custom history is now part of the intended release scope. See `HISTORY-SELECTOR.md` and revised decisionD1. Continue autonomously within this project. The owner explicitly confirmed the delivery bridge/reload test succeeded before the interruption: **do not repeat it just because the last receipt was not written**.

## Verified and implemented

- Source world: `world/mass_effect_le3`;527 stable source IDs,502 selected by default. Optional/missable source families excluded from progression placement. The story/Mars predicates still need availability/lifetime review.
- Native bridge 0.2.0 delivery-development profile is installed, pinned SHA256 `0138523b56a27ab9a77c1ddc638ad34f8a2d47166fdedb0ac516f331bfe8b614`. Normal builds keep writes disabled. No bridge replacement was needed for the latest client changes.
- Live reads: authoritative plot table is a class-default singleton; wrappers were corrected to avoid SDK function-flag corruption. Map, bool/int, GAW (including zero-strength modifiers) and used GUID reads work.
- Earth rooftop medkit and AA-gun Cain produced exact source GUIDs, matched the packaged detector, and survived manual save/reload with GUID bytes present on disk.
- Native research binding stores full seed/team/slot and research-history SHA256 digests plus cursor in audited sparse integer keys 0x4D336000..0x4D336017. Official backup audit:4,454 PCCs, executable and 21 configs; no meaningful collisions. Third-party mods/computed references remain outside the audit.
- Live native item 0: credits 21->1,021, cursor 0->1. Same-index retry granted nothing. Wrong seed/history and out-of-order index rejected with unchanged state.
- Owner confirmed delivery save/reload succeeded. Disk recovery found all 20 expected nonzero schema/mode/digest/cursor pairs in Save 61; Save 60 and older saves have none. This is targeted byte evidence, not a full save parser. Post-reload tool inspection itself was blocked by automatic approval review's usage-limit error and never produced its receipt.
- New AP `--delivery-test` mode receives items through the tested native protocol and deliberately sends no location/goal packets. `--bind-research-save` is explicit opt-in for a fresh disposable research save. Another seed's save is never rebound. Research mode does not claim the maximum-content history or unlock missions.
- History readback implementation: `world/mass_effect_le3/history.py` reproduces 11 vanilla major-plot readers using 33 bools and nine ints, with ambiguity/missing-read diagnostics. Source verifier cross-checks ordered native references against config aliases and database paths, romance recognition thresholds, and both complete Virmire setter branches. `tools/le3apbridge/history_probe.py` can collect a read-only snapshot or decode an existing complete snapshot. This does not initialize history or expose selectable AP options; current plot state cannot reconstruct every imported-history fact after later ME3 events.
- New binary state-event extractor and Genesis bundle catalog: 48 retained vanilla transitions / 437 elements, including 41 substate operations with parent/sibling metadata; 16 annotated choice mappings. Both Genesis Virmire branches independently match the new-character setter. The base game map also exposes 4,159 transitions for further check/bundle research. See `research/le3_genesis_transition_catalog.json` and `research/le3_history_initialization.md`. These bundles are not runtime-verified or exposed as production history options. Genesis reset 5915 clears broad ME2 state as well as ME1; several ME2 romance bundles also alter survival/loyalty, so blindly composing them would rewrite unrelated requested history.
- Offline profile compiler: `history_profile.py` resolves a 51-fact draft schema and structural dependencies, retains past romance/loyalty after later death, and parses complete saved profiles without default-filling. `history_bundles.json` supplies seven mapped decision families; default preview explicitly reports 44 unmapped facts and cannot execute. `tools/preview_history.py` produces a complete profile/digest/partial native plan without game/server contact. Story legality beyond structural dependencies, native initialization and check filtering remain unfinished; see `HISTORY-SELECTOR.md`.

## Validation and evidence

- 41 world/client/history tests and 132 subtests pass on local AP0.6.9: `research/le3_history_profile_tests.log`. One test additionally compares all 256 mapped ME1/Collector Base combinations with the native-reader model; this does not validate full vanilla story legality. Source mapping receipt: `research/le3_history_mapping_validation.json`. The packaged archive loads its history recipe resource, still registers 527 IDs, fills 502 selected locations and reaches its modeled goal.
- 35 native transaction assertions pass for both ASI build profiles; five installer/rollback/profile tests pass.
- Real localhost AP receive-only round-trip with a fake native endpoint: `research/le3_delivery_only_multiworld_receipt.json`. Two received items, cursor2, credits1000, zero location checks or goal reports. This is not a logged real-AP-to-real-game end-to-end run.
- Live delivery/rejection: `research/delivery_credit_01.json`, `delivery_bind_01.json`, `delivery_rejection_01.json`.
- Recovered persistence: `research/delivery_persistence_recovered_01.json`; owner report and tool/disk evidence remain distinguished.
- Pristine input Save 60 backup: `build/test-save-backups/pre-delivery/Save_0060.pcsav`, hash/source recorded in `research/le3_pre_delivery_save_backup.json`. Do not overwrite it.
- Package: `build/mass_effect_le3.apworld`; generated development seed ZIP remains in `build/development_seed`. Manifest IDs/hash are unchanged by the delivery-client work; archive hash changes with source/docs.

## Next substantive work

1. Complete native/availability mappings and story-compatibility rules for the draft selectable-history schema, then implement profile-driven new-career initialization before derived ME3 state is created. The offline 51-fact resolver/compiler and seven mapped families are implemented; 44 default facts remain unmapped. `research/le3_history_initialization.md` records the candidate hook, import-preview hazard and native transition executor. Verify map availability and side effects, and map independent romance/survival/loyalty facts without adopting coupled Genesis shortcuts. Maximum-content is a preset, not the only supported direction. Do not relabel an existing research save as initialized history.
2. Implement and verify an actual Cerberus-HQ/Earth entry gate. Current generation models intel gating, but the game does not enforce it. A plot bool without a mission-access consumer is not a gate.
3. Integrate the production native contract into the normal AP client once those prerequisites exist. The default normal synchronization remains blocked; the explicit delivery-test mode is limited to receiving credits/counters.
4. Broaden runtime/source audits: scan recovery, armor/mod/credit sources, expired checks, old-save replay and full campaign history assumptions. The initial source ledger remains experimental.

No gameplay test request is currently pending. A failed read-only pipe check on resume merely found the game unavailable; the owner corrected that the earlier test was already successful. No new game writes or server connection occurred during persistence recovery.

## Reproducible commands

Use parent AP venv `../vendor/Archipelago/.venv/Scripts/python.exe`; system Python3.14 is for stdlib tooling only. `python tools/build_apworld.py --sync` refreshes the package/local AP copy. Focus AP tests with AP_TEST_WORLDS=mass_effect_le3 and SKIP_REQUIREMENTS_UPDATE=1, then run pytest on `Archipelago-main/worlds/mass_effect_le3/test`.

Windows sandbox blocks compiler/asyncio IPC and access to the live game pipe; use reviewed escalation for native builds, async AP tests and real pipe/game writes. Native builds: `python tools/le3apbridge/build.py` or explicit `--delivery-dev`. Installation/restore: `install_research.py inspect|update|restore` (writer update additionally requires `--delivery-dev`), game must be closed. No need to reinstall the current bridge for Python client work.

ME2 reference checkout: clean `ME_Archipelago_Background`, branch claude/me2-ap-world, commit cab3dea3012acff9ae5609e805a1e1c2f770f1eb. Port analysis: `research/ME2-DELIVERY-PORT.md`. Prior chronological work and obsolete pending requests are retained in `HANDOFF.md`; this file is the authoritative current status.
