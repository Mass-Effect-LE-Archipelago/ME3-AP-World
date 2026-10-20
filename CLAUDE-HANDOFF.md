# Claude Code handoff — 2026-10-20

## Objective and user decisions

Build a working **Mass Effect 3 Legendary Edition Archipelago mod/world**, including game bridge, AP client, seed logic and installation/testing workflow. Feasibility is complete; continue implementation.

The user prioritizes the largest practical set of **granular, configurable checks**: individual pickups, recoveries, objectives and other finite actions, not just mission completion. They suggested Galactic Readiness/war effort as another source; distinguish assets, modifiers, discoveries, intel and strength/readiness milestones rather than conflating them.

The latest history decision supersedes the original fixed-preset-only plan: provide a **seed-creation history selector** for major ME1/ME2 decisions, romances, survivors, loyalty and background. Maximum-content remains a preset. Resolve history before location selection/item placement, initialize the same history in a new AP career, and bind its full digest to that save. History may reduce available checks; do not secretly replace the player's chosen story. Keep current ME3 decisions playable. Preserve customization where it does not conflict with story eligibility.

The user wants autonomous implementation within project scope and check-ins when guidance or gameplay participation is needed. No gameplay request is currently pending. This handoff is not a claim that development is finished.

## Start here

Workspace: `C:\Users\unowi\Documents\APWorldMaker\ME3 LE Randomizer` (PowerShell, Windows).

1. Read this document, `CURRENT-STATUS.md`, `DECISIONS.md`, `HISTORY-SELECTOR.md` and `research/le3_history_initialization.md`.
2. Review the **unfinished observer source** listed below. Compile/fix it before installing or asking the user to perform a new-career test.
3. Continue the full history/native/gating implementation and check-availability work. Do not spend another session merely restating the feasibility overview.

`HANDOFF.md` is the older chronological log. It contains obsolete pending test requests, old test counts, a superseded fixed-history decision and statements written before delivery/reload succeeded. Prefer the current code and named evidence receipts over those passages. Some other early READMEs also retain historical status paragraphs.

## Actual readiness

**Not yet a playable randomized campaign.** The world can generate/fill seeds, native reads and a restricted native item-delivery spike work, and history tooling exists. These remaining blockers are substantive:

- No applied, verified full Shepard history at AP career creation.
- No actual game-side Cerberus HQ/Earth entry gate; only AP logic currently models it.
- No production native contract wired into the normal AP client. The default client intentionally refuses normal campaign synchronization.
- History-dependent source availability, missability/deadlines, vanilla reward replacement and broader item behavior still need implementation/review.
- Full real AP server → real client → real game → check/item/goal round trip has not been demonstrated. Network integration tests currently use a fake native endpoint.

Do not remove readiness guards just to make the client connect or use a fake-host success as proof of those missing features.

## Important interruption: new observer code is not built

The last implementation step added:

- `tools/le3apbridge/CareerTrace.hpp`: bounded 128-record buffer, stable record enums, pagination/parser.
- `tools/le3apbridge/CareerObserver.hpp`: proposed ProcessEvent/ProcessInternal/CallFunction observations of career initialization; records four Virmire plot reads and entry/exit metadata.
- `tools/le3apbridge/tests/CareerTraceTests.cpp`: new native buffer/protocol tests, not run yet.
- Conditional observer integration in `Bridge.cpp`.
- `LE3AP_CAREER_TRACE` in `CMakeLists.txt`; mutually exclusive with development delivery writes.
- `build.py --career-trace`, targeting a separate `build-career` directory. The helper now also builds/runs `CareerTraceTests` for every profile.

**These edits have not been compiled, installed or runtime-tested.** There is no `build-career` directory at handoff. The last 35 native assertions/five installer tests describe earlier source, not these edits. The existing installed/built 0.2.0 binaries remain unchanged and hash-verified.

Intended first build:

```powershell
python tools/le3apbridge/build.py --career-trace
```

Review first: SDK signatures/types and include placement; target discovery; callback duplication/nesting across dispatch routes; observer fail-open exception handling so it always preserves the game's original call; safe game-thread plot reads; and unchanged native function flags. This is investigative code, not an initialized-history executor.

The new metadata-only `CAREER_TRACE <after-sequence> <limit>` response is designed to be available without HUD dispatch, including menus. `limit` is 1–64. Records retain invocation IDs, route, phase, thread, commit depth, data origin, table kind and four-bit validity/value masks for indices `[13827,13828,13940,13939]`. The ring is non-consuming and may discard old entries; oldest/latest sequence numbers expose gaps. A dedicated Python parser/probe and trace-order validation have **not** been written. Seeing the same function through multiple routes must not later cause duplicate initialization.

`install_research.py` currently supports only the old research/delivery profiles and pinned hashes. It does **not** support installing the new career-trace profile. Add explicit profile selection, new verified hash and rollback tests if this build is to be installed. Do not rename a new binary to bypass the old hash checks. Avoid rebuilding/replacing the tested delivery binary merely to stage the observer.

## Source map

| Path | Role |
|---|---|
| `world/mass_effect_le3/` | Authoritative AP world/client/history source |
| `Archipelago-main/` | Local AP 0.6.9 source; synced world here is a generated working copy |
| `tools/build_apworld.py` | Reproducible packaging; `--sync` copies authoritative world into local AP |
| `tools/le3apbridge/` | C++ ASI, build/install helpers, read/delivery probes |
| `tools/research/Le3Probe/` | .NET read-only LegendaryExplorer package/config/script/binary extractor |
| `research/` | Raw inventories, source evidence, test logs, live receipts and history catalogs |
| `ME3LE Backup/` | Supplied vanilla game/DLC input; do not modify |
| `ME_Archipelago_Background/` | Separate ME2 reference Git checkout |
| `other randomizers/masseffect1/` | Supplied completed ME1 reference work (world, extraction, research/build files) |
| `build/` | AP archive, dev seed, offline previews, installation backups, protected test save backup |

ME2 reference: `https://github.com/Unowa001/ME2-LE-Archipelago.git`, branch `claude/me2-ap-world`. Last recorded checkout commit: `cab3dea3012acff9ae5609e805a1e1c2f770f1eb`. The user explicitly pointed to its item-sending implementation. See `research/ME2-DELIVERY-PORT.md`; verify current repo state before fetching/updating. Do not alter that reference as part of ME3 implementation.

Git caveat: on 2026-10-20, even `git -C 'C:/Users/unowi/Documents/APWorldMaker/ME3 LE Randomizer' status --short` failed with `fatal: cannot change to 'C:/Users/unowi/Documents/APWorldMaker'`. The current top-level branch/dirty state is therefore **unverified**. Investigate repository/worktree configuration and inherited Git settings before committing; no clean-checkout or commit claim is made here. Do not reset or clone over existing work.

## Builds, tests and artifacts

The existing AP virtual environment is **outside this project directory**:

`C:\Users\unowi\Documents\APWorldMaker\vendor\Archipelago\.venv\Scripts\python.exe`

It is Python 3.12.10 for local AP 0.6.9. System Python 3.14 is suitable for stdlib helpers, not a substitute for the AP environment. Copying only this project folder to another machine does not copy that venv or installed Windows toolchains.

```powershell
python tools/build_apworld.py --sync
$env:AP_TEST_WORLDS = 'mass_effect_le3'
$env:SKIP_REQUIREMENTS_UPDATE = '1'
& '../vendor/Archipelago/.venv/Scripts/python.exe' -m pytest Archipelago-main/worlds/mass_effect_le3/test -q --disable-warnings
& '../vendor/Archipelago/.venv/Scripts/python.exe' tools/test_packaged_world.py

python tools/verify_history_mapping.py
python tools/research/build_history_catalog.py --sync-world
# These refuse to overwrite an existing output; choose NEW filenames:
python tools/preview_history.py build/new-history-preview.json
python tools/preview_history.py build/new-custom-preview.json --input research/history-custom-example.json
```

Latest recorded AP run: **41 tests +132 subtests pass** (`research/le3_history_profile_tests.log`). One test additionally iterates all **256 mapped ME1/Collector Base combinations** against the native-reader model. That is not proof of full story legality or native initialization. Packaged-world smoke test loads the history resource from the ZIP, registers 527 source IDs, fills 502 selected checks and reaches its **modeled** goal.

Native tools: Visual Studio 2026 Community C++/Windows SDK, bundled CMake path resolved by `build.py`; .NET 10 for `Le3Probe` using the supplied LegendaryExplorerCore DLL. Its last build (the state-event extractor, before observer edits) completed with zero warnings/errors.

```powershell
dotnet build tools/research/Le3Probe/Le3Probe.csproj --no-restore --verbosity quiet
python tools/le3apbridge/build.py                 # default writes OFF
python tools/le3apbridge/build.py --delivery-dev  # explicit research writes
python -m unittest tools.le3apbridge.test_install -v
```

The last two native build profiles previously passed 35 transaction assertions each; five installer/profile/rollback tests passed. Rerun relevant native checks after addressing the unfinished observer edits. Codex's former sandbox blocked compiler/asyncio IPC and live pipe access; reviewed execution outside that sandbox fixed it. Treat that as environment history, not a game-code failure or a requirement to weaken checks in another agent environment.

Artifacts verified by reading hashes on 2026-10-20:

| Artifact | SHA-256 |
|---|---|
| `build/mass_effect_le3.apworld` | `fa44d879e24488622ac33f59d56ef1f221bbe01d319256ffd4e17746b4159dc6` |
| Existing delivery ASI, workspace **and live installation** | `0138523b56a27ab9a77c1ddc638ad34f8a2d47166fdedb0ac516f331bfe8b614` |
| Existing read-only 0.2.0 ASI | `29ca2f8d5b247e62e5e59dffa5f860f83816c00c3505597be0ed7d5ca1d59e9b` |

Dev seed: `build/development_seed/AP_41961810824680882422.zip`; YAML: `Mass Effect Legendary Edition 3 - Development.yaml`. These remain experimental artifacts, not a release. The seed predates the draft history compiler; generation still uses the placeholder history.

## World and check implementation

`locations.json` holds append-only stable IDs: **527 sources** =423 saved-use GUID candidates, 76 exploration recoveries, 11 story predicates and 17 Mars objective predicates. Default options select 502; experimental weapon checks add 25. Preserve IDs/names when refining availability/detection; `tools/build_me3_manifest.py` protects the ledger.

Source inventories and their limits are in `CHECKS-CATALOG.md`, `research/le3_saved_pickup_sources.csv`, `le3_exploration_sources.csv`, `le3_objective_reward_sources.csv`, `le3_gaw_*`, and `le3_plot_inventory.csv`. The plot database has 15,978 bools, 1,696 ints and 80 floats; database labels alone do not establish a distinct persistent check.

`world.py` currently filters by category/DLC, not selected history. Vanilla missions are modeled as eventually reachable; AP Crucible Intel gates the Cerberus HQ/Earth regions only in generation. Optional/missable source families are filler-only (`EXCLUDED` from progression), and safe-slot capacity clamps intel counts. Item pool: Crucible Intel counters and Credits (1000). Goal bool 22426 is a final-decision candidate, not transition-verified end-to-end.

Only the Earth rooftop medkit and AA-gun Cain currently have exact witnessed pickup transitions plus reload evidence. Do not extrapolate those two tests to every cache, full-inventory interaction, armor/mod unlock, map recovery or timed quest. GAW includes zero-strength modifier entries; membership and positive strength are different facts. Expand granular optional checks while reviewing distinct actions, expiration, history branches and persistence; don't inflate the count with duplicate aliases or repeatable farming.

## Client/native contract and critical engine findings

`client_core.py` models save-bound identity, indexed delivery, source detection and finale gating. `client.py --delivery-test` uses `delivery_client.py` for an explicit **receive-only** AP development mode. It sends no checks/goals, reads no source predicates, does not initialize history and opens no mission gates. `--bind-research-save` is explicit and will not rebind an existing foreign identity.

Native pipe: `\\.\pipe\LE3APBridge`, local message mode. Compatibility handshake: `HELLO 1` → `1 LE3 readonly`, even for the development delivery profile. `CAPS` identifies actual features. Read commands: `GETB/GETBS`, `GETI/GETIS`, `MAP`, `GAW`, `USES`, `PLOTINFO`. Game-facing requests drain at `SFXGame.BioHUD.PostRender`, timeout after five seconds when unavailable. Keep game reads/writes on the appropriate game thread.

Two important fixes already established:

1. Generated SDK native wrappers use `FunctionFlags |= ~0x400`, corrupting unrelated flags. The bridge bypasses these wrappers with the original ProcessEvent trampoline and zero-initialized ABI-correct parameter structs. **Do not reintroduce wrapper calls or mutate flags.**
2. The authoritative plot table returned by `BioWorldInfo.GetGlobalVariables` is the **class-default singleton** `Default__BioGlobalVariableTable`. Generic actor-instance filtering incorrectly rejects it. Check type/liveness, permit the CDO for this service; don't assume every CDO is invalid.

Development commands: `DEV_SESSION`, `DEV_WALLET`, `DEV_BIND ... RESEARCH_ONLY`, `DEV_TXN <identity> <history> <index> CREDITS <amount>` or `COUNTER`. Exact wire/storage contract: `tools/le3apbridge/DELIVERY-PROTOCOL.md` and `Delivery.hpp`.

Owned save state is a **sparse integer map**, keys `0x4D336000..0x4D336017` (24 slots), not a dense bool array. Marker/schema/cursor/mode plus all eight 32-bit words of each SHA-256 digest; reserved fields zero. Full seed identity hashes `[seed_name,team,slot]`; full history hash includes preset/version/resolved choices, excluding support metadata. Research history is explicitly `research_existing_save_v1_NOT_maximum_content` and must never be relabeled as initialized player history.

Each native mutation checks the currently loaded save's identity/history. Gaps fail, duplicate indices return done, old-save replay/lost replies preserve indexed semantics. Credits use AdjustResource type0, measured clamping, notification=false, ignoreBudget=true; capped filler consumes its index so it cannot block intel. Failures restore balance/cursor where possible. Preserve these policies when broadening delivery.

The state-block audit covered 4,454 supplied PCCs, the executable and 21 configs with zero scan errors/no meaningful reference collisions. Third-party mods and computed IDs are outside that proof. See `research/le3_delivery_storage_audit_summary.json` and raw reviews. Do not copy ME2's bool 21000–21999 range: it collides with 900 LE3 database entries.

## Live installation, saves and evidence

Game: `C:\Steam\steamapps\common\Mass Effect Legendary Edition\Game\ME3`.

Live files: `Binaries/Win64/bink2w64.dll` (official-source ME3Tweaks loader) and `Binaries/Win64/ASI/LE3APBridge.asi` (0.2.0 delivery-development). Original Bink is retained as `bink2w64_original.dll` and `build/live-original/bink2w64.dll`. Install/restore helper verifies paths, closed game, receipts and hashes and backs up prior ASIs. Inspect before changing anything; never overwrite a loaded module or bypass changed-file refusals.

Dependency revisions: LEBinkProxy `1c435d8df0367642d9fc8572b67b6ae92295967e`; LExASIs `aaad03ab6e5112e27ff5528f7b08c3bcf3870c31`; SDK submodule `3885be14113816ff1d2a0d941aa96bba6df9dc58`.

**The owner confirmed delivery/save/reload already succeeded before an interruption. Do not ask for a repeat merely to recreate a missing receipt.** Logged credit delivery was 21→1,021, cursor 0→1; same-index retry added nothing. Wrong seed/history/gap were rejected. Owner then created/reloaded Save 61. Disk recovery independently found all 20 expected nonzero schema/mode/hash/cursor index/value pairs in Save 61 and none in the earlier saves. The post-reload pipe receipt itself was never written because Codex approval review hit a usage-limit error; this was not an observed game failure. Credit persistence after reload is owner-confirmed; the recovered byte scan is narrower than a full save parser. A fresh-process replay is a separate future test, not something already logged.

Protected pre-delivery Save 60: `build/test-save-backups/pre-delivery/Save_0060.pcsav`, SHA-256 `46af0da9c51991c29446b5ff4df23955e4307e820275ead49dbedf6327c496e7`. Original career/source path is in `research/le3_pre_delivery_save_backup.json`. Do not overwrite it, edit saves on disk, or automatically bind arbitrary user careers. The already-bound research save belongs to its research identity, not any new AP room.

Key receipts:

- `research/live_install_receipt.json`: installation; some legacy top-level flags lag the richer runtime-validation section.
- `research/le3_live_check_evidence.json`, `live_earth_after_pickups_01.json`, `live_earth_reloaded_01.json`: medkit/Cain GUID evidence. `tools/replay_live_pickups.py` replays detectors.
- `research/delivery_bind_01.json`, `delivery_credit_01.json`, `delivery_rejection_01.json`: real native binding/delivery/rejections.
- `research/delivery_runtime_validation.json`, `delivery_persistence_recovered_01.json`: distinguish owner confirmation, logged native evidence and recovered save bytes.
- `research/le3_local_multiworld_receipt.json`, `le3_delivery_only_multiworld_receipt.json`: real local AP server with **fake game endpoint**, not real-game end-to-end proof.
- `research/le3_development_validation.json`, `le3_history_profile_validation.json`: offline/package/test summaries.

## History work: what exists and what remains

`history.py` implements 11 native major-plot reader models with 33 bools/nine ints and ambiguity diagnostics. `tools/verify_history_mapping.py` checks indices/order/config/database paths, romance thresholds and both Virmire setter branches. ME1 romance needs an active flag **and dialogue counter >=4**. ME2's major-romance reader recognizes relationship int **==5**. Wrex's reader prioritizes in-party over death flags. A reader fallback is not proof of initialized history; Collector Base even defaults to preserved when both outcomes are unset.

`history_profile.py` provides the 51-fact draft schema, immutable resolved profile, structural validation and offline compilation preview. It preserves loyalty/past romance after later death, rejects recruitment contradictions and missing/invalid saved fields, and hashes full choices through the existing digest contract. Sex/romance compatibility, intermediate romance timelines, ME1 romance/Virmire legality and additional continuity still need source/native review. Its maximum-content defaults are a proposed all-recruited/alive/loyal history, not a proven maximum check-count optimum.

`history_bundles.json` contains 16 annotated options across seven mapped families (six ME1 families plus Collector Base). Default profile: seven mapped, **44 facts unmapped**. The compiler reports every gap, retains native substate metadata and always marks the plan non-executable. `data.HISTORY` and `world.fill_slot_data()` still use the older placeholder; history options are not exposed in generation. Do not wire the draft into production as though all 51 facts initialize correctly.

New source evidence: `Le3Probe --state-events` extracts binary state-event maps, which are absent from normal export properties. The retained Genesis map contains 48 transitions/437 elements (41 substates); the base map has 4,159 transitions. `tools/research/build_history_catalog.py` builds `research/le3_genesis_transition_catalog.json` and optionally syncs reviewed recipe data into the world. Preserve parents/siblings and native processing instead of flattening a substate to a lone bool.

Genesis reset **5915 clears 111 ME1 and ME2 elements**; it is not an isolated ME1 reset. ME2 result bundles couple loyalty/recruitment/survival; romance bundles 5850–5853 can resurrect/loyalize partners. Never use those shortcuts to silently change unrelated requested history. Retained dialogue/transition data is not proof that every old comic branch is reachable in LE3; only 14 retained transition dialogue labels resolved in the supplied English files.

New-career source ordering (`research/le3_history_callers.jsonl`): `BioSFHandler_NewCharacter.FinalCommit` creates the career, handles import data, initializes plot state, adds codex entries, runs `SetPlotChoices` for fresh non-imported games, updates the player save record, then starts the campaign event. A candidate insertion point is **after vanilla SetPlotChoices and before UpdatePlayerSaveRecord/start event**. Imported careers skip that call. Import previews also initialize temporary plot tables; do not initialize those or ordinary non-AP careers. Origin/service history feed `CreateCareer` earlier through player data, requiring consistent player/save-record handling.

Native `BioWorldInfo.ExecuteStateTransition(int,int)` is a candidate executor for retained substate semantics. Its map availability at career creation, actual side effects, fresh-career scoping and save/reload persistence are unverified. The observer is meant to test the proposed seam before adding writes.

## Completion direction

Finish/review the observer and verify the initialization seam, complete coherent native/profile mappings and source-availability rules, implement the actual mission gate, then integrate production AP synchronization. Broaden granular checks and reward handling alongside this work, with stable IDs and conservative progression placement where current-game branches/deadlines remain unresolved. A working release needs real-game evidence across those systems, not just an increasing offline test count.

Suggested opening prompt for Claude Code:

> Continue this ME3 Legendary Edition Archipelago project. Read CLAUDE.md and CLAUDE-HANDOFF.md first. Preserve the current work, source IDs and save backups. Start by reviewing/building the unfinished read-only career observer, then advance history initialization, real mission gating and production integration. Maximize granular checks and support seed-selected Shepard history. The earlier credit delivery/reload test already succeeded; don't ask me to repeat it because a receipt was interrupted. Ask when you need a new gameplay action or an actual design decision.
