# Mass Effect 3 Legendary Edition: Archipelago feasibility

Research date: 2026-10-14. Target: PC Legendary Edition ME3. First milestone: feasibility and check discovery; no playable mod or AP world has been built yet. Subsequent work is recorded in `CHECKS-CATALOG.md`, `FUNCTIONALITY.md` and `HANDOFF.md`: the read-only research bridge now compiles, and the user confirmed a maximum-content history preset for the first release.

## Assessment

**Feasible, with strong static evidence for a large, granular check pool.** The recommended implementation is a Python AP world/client, an LE3-specific ASI bridge, and a staged DLC/merge mod for progression gates and persistent check instrumentation. The ME1 implementation provides working patterns; the ME2 branch provides a more explicit transaction protocol and generation/client tests. Neither substitutes for validating LE3 behavior.

The highest-value next work is to enumerate individual interactions and assets, then prove their persistence in a small runtime prototype. Mission completion alone would leave much of the available coverage unused. A final check count would be premature: the numbers below describe database entries and package objects, not confirmed playable locations.

## Evidence inspected

| Source | Finding | Limit |
|---|---|---|
| `ME3LE Backup` | 4,454 PCC packages; base game and official DLC directories, including From Ashes, Leviathan, Omega and Citadel families | A backup is sufficient for offline analysis; an installed game and test career are needed for runtime proof |
| Local `LegendaryExplorerCore.dll`, embedded `le3.json` | 15,978 bools, 1,696 ints, 80 floats, 3,769 conditionals, 6,402 transitions | Named states can be obsolete, inherited, mutually exclusive, transient or unused |
| Plot ancestry reconstructed with normalized numeric IDs | 10,329 of 17,754 state rows sit under imported ME1/ME2 trees; 7,425 are outside those trees | Imported state still matters for history and prerequisites; it is not evidence of an action performed in ME3 |
| Base `SFXGame.pcc` export table | GAW handler, asset save records, treasure metadata, codex/inventory functions are present | Export existence does not prove a hook fires, that a field is sufficient, or that a callable SDK wrapper exists |
| Five `BioD_Nor_203aGalaxyMap.pcc` copies | Base contains 66 non-default `SFXPlanetFeatureGAWAsset` instances; each of four inspected DLC/patch copies contains 77 | These are overlapping versions, never 374 distinct checks. Determine the mounted winner, asset IDs, availability and unique interactions |
| ME1 source/catalog/handoff | Persistent plot checks, object keys, custom flags, shop and drop-slot patterns | The handoff itself distinguishes built features from owner-tested features |
| ME2 reference branch | World/client/bridge source available locally; README reports 418 maximum checks and an uncompiled, untested bridge | Those are ME2 project claims, not LE3 results or a runtime-tested bridge |

ME2 reference: `ME_Archipelago_Background`, branch `claude/me2-ap-world`, inspected commit `98ca74111b5ee2a32bc6b4384c430fa9dd47613c`.

Reproducible local evidence:

- `research/le3_plot_inventory.csv`: every bool/int/float with full ancestry, legacy tag and evidence status.
- `research/le3_check_candidates.csv`: 2,068 nonlegacy rows selected by broad discovery heuristics. Categories overlap. Includes internal states, so this is **not 2,068 checks**.
- `research/le3_plot_summary.json`: counts and source hashes, plus the ME2 bool-range collision list.
- `research/le3_package_probe.txt`: selected exports from SFXGame, Startup and the base galaxy map.
- `research/le3_galaxy_map_variants.txt`: export evidence from all five inspected galaxy-map copies.

## Check coverage, from broadest useful families to experimental additions

The objective is maximum **distinct, finite, recoverable actions**. Expose families as options so a short campaign and a completionist campaign can share the implementation.

| Family | Finest useful unit | Detection / work needed | Main logic issue |
|---|---|---|---|
| Main missions | Mission completion plus independently meaningful objectives | Trace plot transitions and Kismet objectives; use branch-neutral completion predicates | Preserve story prerequisites and scripted companions |
| N7 and other side missions | Completion and individual objectives/interactions | Mission state plus object/sequence instrumentation | Expiration when story advances |
| Citadel assignments | Discover request, retrieve object, deliver object, resolve assignment | Dedicated states where present; journal and conversation transitions otherwise | Some steps are automatic or alternate routes to the same action |
| Galaxy exploration | Each recoverable planet/system discovery | Map feature identity and GAW/plot state; instrument the recovery action if necessary | Discovery and probing may be different events; systems unlock over time |
| War assets | Each independently earned asset | GAW unlock state, asset definitions and source events | Starting/imported assets, replacements and mutually exclusive awards |
| Asset improvements | Each distinct reinforcement/modifier event | Modifier ID and source completion; persistent instrumentation where required | Several sources can modify one displayed asset; score deltas lose identity |
| Military-strength milestones | Each chosen threshold reached once | GAW score API plus persistent high-water/check flags | Score can fall; AP rewards must not accidentally award their own checks |
| Intel terminal | Acquire each intel item, optionally use each | Local DB has 12 apparent acquired/used pairs plus two additional outcome/use flags | Two upgrade choices from one intel item should resolve one use check |
| Weapons found in missions | Each physical pickup | Map/package/object identity or pickup sequence | Receiving the same weapon from AP must not count as finding it |
| Weapon mods | Each placed pickup and separately identified shop upgrade | Source identity, rank-aware inventory/event handling | Owning a mod is not proof of visiting every source |
| Armor | Each pickup or one-time purchase | Source event and acquisition state | Shared inventory flags conflate AP grants and vanilla acquisition |
| Credits/salvage | Each fixed cache, safe, datapad reward or salvage interaction | Package/object or sequence identity; persistence audit | Generic credit increases cannot identify the source |
| Medi-gel/grenades/ammo | Each fixed placed supply object, first use only | Object-specific hook and saved check bit | Full inventory may block use; replenishing objects must not farm checks |
| Shops | Each finite purchase slot, item or upgrade rank | Purchase-success event and stable slot/rank key | Affordability, duplicate stock and Normandy procurement overlap |
| Spectre requisitions/authorizations | Each finite terminal authorization or purchase | Dedicated plot or terminal transaction | Story availability and alternate methods of obtaining the same object |
| Codex | Each genuinely unlockable page | Local DB has 151 bool entries under `Global.Codex_Entries`; inspect actual codex records too | Imported/startup entries and alternate personal-history entries |
| Cabin collectibles | Each model, pet/fish acquisition and other distinct collectible | 16 LE3 model-ship bool entries; source hooks for retrieval | Imported possession, replacement purchases and fish death |
| Normandy/Citadel social events | Each distinct conversation/event stage | Plot transitions; source event for scenes with no lasting state | Character survival, romance exclusivity, mission-count windows |
| DLC campaigns | All the above families within each DLC | Package-level catalog including DLC overrides | Entry/exit restrictions and campaign prerequisites |
| Citadel activities | Each finite challenge, unique prize or event | Separate minigame/result investigation | Repeatable games and mutually exclusive party scenes |
| Armax Arena | First clear per curated challenge/map/enemy tier; finite score milestones | DB contains 118 bools and 82 ints in `CmbtSim`, many internal; result hook likely needed | Avoid arbitrary combinations and unlimited repeat farming |
| Combat feats / level milestones | Unique encounter objective or bounded feat/level target | Runtime event plus persistent per-seed ledger | Generic enemy kills, XP totals and global achievements are weak location identities |

Do not infer one check per raw state. A conversation's started/active/finished flags usually describe one event. Conversely, one displayed war asset can represent several independently checkable actions.

### Examples already grounded in the LE3 database

| State | Meaning in database | What it could support |
|---|---|---|
| bool 21531 / 21532 | Battle Footage acquired / used | Acquisition and terminal-use checks, after source verification |
| bool 21541 / 21542 | Intelligence Archives acquired / used | Same two-step pattern |
| bool 22419 / 22420 | Feron intel acquired / used | History-sensitive acquisition/use |
| bool 21323 | Normandy pilot: Gave GAW Asset | A social contribution, with exact trigger still to trace |
| bool 21870 | Citadel sanctuary log: GAW01 found | A specific discovery candidate |
| bool 21042 | Cabin model Ship_1 | Possession candidate; map its actual source before assigning a location |
| bool 23551 | Omega processing-facility spare-room treasure collected | Individual treasure candidate |
| bool 24882 / 24883 | Citadel DLC credits01 / credits02 received | Separate fixed rewards, subject to package verification |

All examples are `DB_ONLY`, not runtime-verified.

## Galactic Readiness and war effort

The user's suggestion opens a substantial check family. EA documents that Legendary Edition rebalanced Galaxy at War and removed external multiplayer/companion influence on readiness. We should use the LE3 implementation directly rather than assume original-ME3 percentage behavior or ending thresholds.

Local `SFXGame.pcc` provides particularly useful evidence:

- `SFXSaveGame.GAWAssetSaveInfo` has `Id` and `Strength`; the player save record has a `GAWAssets` array.
- `SFXGAWAssetsHandler.GAWAsset` includes `Id`, `AssetName`, `UnlockPlotStates`, `StartingStrength`, `CurrentStrength`, `MaxStrength`, `bIsExploration` and `ModTargets`.
- Modification targets have `TargetID` and `Value`.
- Handler functions include `IsGAWAssetUnlocked`, `UnlockGAWAsset`, `UpdateGAWAsset`, `GetTotalStrengthByType`, `GetTotalScore`, `GetFinalScore` and readiness accessors.
- Galaxy-map feature classes expose `AssetID`, `OnScanned` and `FeatureProbed`.

Recommended option layers:

1. **Exploration recoveries:** one check per unique recovery source.
2. **Asset recruitment:** one check per independently earned asset, with starting assets handled explicitly.
3. **Reinforcements:** one per distinct improvement source, including separate updates to the same asset.
4. **Strength milestones:** an optional finite threshold list, latched permanently once reached.

Next, extract asset definitions from the actual LE3 configuration and cross-reference their unlock states/modifiers against mission sequences. Asset types also include nonmilitary rewards, so a GAW feature count is not automatically a war-asset recruitment count.

A total alone cannot reconstruct each contribution. Asset snapshots can recover persistent unlocks, but an unlock-then-loss between polls can require a hook and saved latch. Hooks must run while the AP client is offline too. Persist check identity, not just a transient event queue.

Keep natural action checks separate from AP item rewards. If AP can grant military strength, document whether milestones count it; the recommended default is natural-earned progress, tracked separately. Otherwise an asset/strength item can satisfy its own location requirement. Any randomized war-effort goal must account for the guaranteed attainable strength of the selected history and check options.

## Shepard history: preset first, configurable history afterward

Both user proposals are viable. Start with a versioned, internally consistent **AP Shepard history preset** chosen to preserve many ME3 opportunities. Add configurable YAML history using the same underlying schema. This concerns story history; it need not force appearance, name, class or gender unless a selected check actually depends on one of them.

The preset must be a reviewed set of compatible decisions, not “set every favorable flag true.” Some outcomes are mutually exclusive. Candidate history dimensions include Virmire survivor, Wrex, rachni decision, ME2 squad/crew survival, loyalty and character-specific outcomes that affect ME3. Exact supported values require dependency tracing; do not expose hundreds of raw bools in the UI.

Use one manifest as the authority:

1. YAML selects a preset and supported overrides before generation. A custom creator is a convenient editor for ordinary world options; generation must also work without that creator.
2. Resolve defaults and validate incompatible combinations. Store the complete resolved history, schema version and stable digest in slot data.
3. Generate only checks supported by that history. Use branch-neutral location names where different actors/outcomes fulfill the same role. Preserve stable IDs across history variants; omit unavailable locations instead of renumbering others.
4. At AP new-game initialization, apply that history **before** ME3 derives journals, character availability, inventory and starting assets. Prototype the exact lifecycle point. Late plot edits alone can leave derived state inconsistent.
5. Record initialization and seed binding in the save. Validate the save against slot data on reconnect. Never reapply the initializer to a progressed career.
6. For existing imports, a later helper may inspect a save and emit compatible YAML before generation. An arbitrary save loaded after generation cannot redefine the server's location pool. First release should use a new AP career; imported histories are an expansion.

Historical plot flags establish prerequisites. They do not become ME3 checks merely because the preset sets them. Establish a baseline for imported possessions, codex and assets, and deliberately define any intended start checks.

This handles historical availability, but not decisions made during ME3. For exclusive branches, use one outcome-neutral check, select a branch before generation, preserve a recovery route, or keep unsafe locations free of progression. No preset can make every contradictory story outcome occur in one career.

## Progression, missables and item design

First preserve the normal story graph and add modest AP access requirements. Arbitrary mission-order randomization is a separate, harder project: ME3 scripts expect story phases, particular squadmates and changes to the Citadel/Normandy.

Possible progression items: mission authorization/intel, access to optional areas/DLC and a bounded finale requirement. Useful/filler candidates: weapons, progressive mod ranks, credits, supply upgrades and supported war-effort bonuses. Retain a viable starting loadout and required story companions. Trace item grant paths and their native reward suppression before committing to a pool.

Every proposed check needs an availability record: history prerequisites, mission phase, required items, deadline, branch alternatives, repeatability and fallback. Examples needing dedicated tracing include Citadel phases, Grissom Academy, the Tuchanka bomb, Rannoch decisions, character encounters and the finale cutoff. These names identify research targets, not validated deadlines in this document.

For the broadest pool, prefer preserving or recovering missed sources where practical. Spectre recovery purchases and original pickups should resolve the same logical source when appropriate. If a check cannot be made reliably reachable, include it only in a documented optional mode or prevent progression placement there. Filler-only missables still affect completionists and should remain visible in the tracker.

## Technical contract and major risks

- **LE3-specific bridge:** reuse the ME2 protocol design, port against LE3 SDK types and prove each operation. ME2's bridge is not yet built/run according to its own README.
- **Plot storage collision:** 900 bool IDs from 21000–21999 already appear in the local LE3 DB. Do not copy that ME2 AP block. Audit vanilla/DLC and supported mods before selecting storage; unlisted IDs alone do not prove safety or serialization.
- **Persistence:** saved check flags or a save-associated ledger must survive client disconnect, map changes and restart. Volatile hooks alone fail AP's offline-check requirement.
- **Identity and item delivery:** bind full seed/slot identity, use indexed idempotent delivery and test lost replies, retries and old-save replay. Sequential execution does not establish crash safety by itself; verify actual save serialization of both reward and index.
- **Source identity:** receiving an AP weapon/mod/asset must not impersonate finding its vanilla source. Canonical package + object/sequence identity is preferable where possession flags conflate sources.
- **Overrides:** resolve mount priority before editing packages. Galaxy-map copies already demonstrate this problem. Multiple copies are not independent checks.
- **Hook coverage:** exported functions suggest instrumentation points, but native paths may bypass a ProcessEvent hook. Trace call sites and compare against observed state changes.
- **Compatibility:** stage DLC/merge changes and test with a clearly specified supported mod set. Inspect names and licenses before reusing source. Do not distribute vanilla PCC files as research outputs.

## Implementation sequence and acceptance criteria

1. **Catalog:** extract GAW/config treasure definitions and scan mission/DLC sequences. Produce a human-reviewed location manifest with source keys, evidence levels and availability. Existing CSVs are the starting discovery index.
2. **Read-only LE3 bridge spike:** handshake, current map, batched bool/int reads, codex and GAW snapshots. Observe one mission objective, pickup, scan/probe and asset award. Save/reload and disconnect the client during checks.
3. **AP career initialization:** prototype preset history before derived initialization. Verify character availability, journal state and initial GAW inventory on a new career and reload.
4. **Persistent instrumentation and delivery:** one source-specific pickup hook, one asset modifier, chosen AP storage, seed identity and one useful reward delivered exactly once. Test full inventory, map transitions, death/reload and older saves.
5. **World/client vertical slice:** a small reachable campaign section with item gates, real checks and a temporary explicit test goal. Fake-bridge tests plus actual runtime evidence; fake tests alone do not prove playability.
6. **Coverage expansion:** mission/assignment steps, exploration/GAW, pickups/shops, codex/collectibles, social and DLC activities. Append IDs; never regenerate public IDs from changing sort order.
7. **Generation and campaign QA:** exercise history/category combinations, minimum and maximum pools, spheres, item counts, progression before deadlines and attainable victory. Then an offline/reconnect test and a multiworld playthrough.

The next implementation priority is **GAW and treasure extraction plus the read-only bridge spike**. User guidance is needed before fixing the actual default history, optional romance/social scope and whether the finale uses vanilla strength, AP progression, or both. Those choices do not block catalog work.

## External primary sources

- [EA: Gameplay Calibrations — Galaxy at War Rebalancing](https://www.ea.com/ea-play/news/gameplay-calibrations)
- [Legendary Explorer: Introduction to Plot Management](https://github.com/ME3Tweaks/LegendaryExplorer/wiki/Introduction-to-Plot-Management)
- [LExASIs build configuration, including LE3 target](https://github.com/ME3Tweaks/LExASIs/blob/main/CMakeLists.txt)
- [Trilogy Save Editor FAQ: military strength is calculated from war assets](https://github.com/KarlitosVII/trilogy-save-editor/wiki/Frequently-Asked-Questions)
- Local AP contract: `Archipelago-main/docs/adding games.md`, particularly offline location recovery and indexed received-item handling.
