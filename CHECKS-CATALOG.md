# LE3 checks: sources and behavior

Updated 2026-10-14. This is a research catalog, not a release location ledger. None of the sources is runtime-verified yet.

## What has actually been located

The package scan read 3,229 non-localized PCC files without errors. It found 1,752 reward-related objects in the selected classes. Resolving duplicate package names by the supplied backup's mount priorities leaves 1,457 objects. These overlap and include internal machinery, so they must not be added together as a playable check count.

| Source family | Located in mounted packages | Interpretation |
|---|---:|---|
| Treasure use modules | 320 | Fixed credits/supplies and med stations; 301 have explicit valid world-instance GUIDs |
| Weapon-mod use modules | 70 | Placed mod interactions with distinct GUIDs |
| Armor use modules | 27 | Placed armor interactions with distinct GUIDs |
| Weapon use modules | 25 | Includes two bonus-weapon modules; heavy/special weapon interactions need individual eligibility review |
| Unique valid world use GUIDs across those families | **423** | Strong source identities; not yet a guarantee of reachability or desired check behavior |
| Named galaxy-map GAW recoveries | **76** | Distinct named recovery candidates in the highest-mounted local map package |
| GAW award nodes | 229 | Includes individual silent awards and bulk per-level award nodes; multiple nodes may award the same asset |
| Mission-XP nodes | 632 | Objective/combat reward events; not 632 missions or automatically 632 checks |

Nineteen additional use modules have no explicit valid GUID and appear in prefab/template paths. They need inheritance/instancing investigation, not invented check IDs. The scan covered named classes listed in the research README; it is not an exhaustive search of every possible reward path or DLC subclass.

## Pickup behavior and identity

Decompiled local LE3 methods show:

- `SFXModule_SavedUse.HasBeenUsed` looks for an exact GUID in `SFXEngine.UseModuleList`.
- `Used` records a new GUID only if all four components are nonzero and it has not already been recorded.
- `SFXTreasureUseModule.OnUsed` first attempts `AwardResource`. It returns if the award fails. Only after success does it disable the interaction and record use.
- `SFXSaveGame` declares `UseModuleRecords`, providing a concrete serialization target to investigate. Actual save/reload testing remains required.

This is more useful than detecting a credit balance increase or ownership of a weapon: a GUID identifies a source interaction and survives the actor being streamed out if its engine/save bookkeeping works as expected. The first implementation should use those native records where validated, with additional instrumentation for sources that have no reliable saved state.

Specific Mars examples located in the backup:

| Source package | Source object suffix | Candidate |
|---|---|---|
| `BioD_ProMar_230Lockers.pcc` | `SFXArmorNode_0.ArmorUseModule0` | Arms melee-damage armor pickup |
| `BioD_ProMar_240ExteriorWalk.pcc` | `SFXArmorNode_0.ArmorUseModule0` | Torso shield-regeneration armor pickup |
| `BioD_ProMar_620Security.pcc` | `SFXWeaponModNode_0.WeaponModUseModule0` | Shotgun reload-speed mod pickup |
| `BioD_ProMar_210Parking.pcc` | `SFXMedkit_3.TreasureModule0` | Fixed medical supply interaction |

The readable names above describe serialized reward types; final in-game display names and successful-use behavior still need verification. Exact source paths, export indices and signed GUIDs are in `research/le3_saved_pickup_sources.csv`.

For supply checks, decide how a full inventory should behave. The current vanilla completion path can refuse a failed award. A mod may need to allow the AP check independently while preserving the vanilla reward rules. Heavy-weapon pickups, reusable sources and forced story equipment also need separate policies.

## War effort: recruitment, reinforcement, retrieval and delivery

The base/DLC configuration defines 268 distinct GAW IDs. Case-normalized types are 122 military assets, 96 modifiers, 24 salvage rewards, 13 intel rewards, 12 artifacts and one quest reward. Definitions include unavailable and history-dependent content.

Decompiled `UnlockGAWAsset` establishes an important distinction:

1. It rejects an already-unlocked ID.
2. It stores the awarded ID in `UnlockedGAWAssets`, including modifier IDs with zero starting strength.
3. It applies previously unlocked modifiers to a new asset and applies a newly unlocked modifier to existing targets.
4. It sets `UnlockPlotStates` bools **as an effect of the award**. These are not prerequisite conditions.
5. Salvage awards have a separate credit-reward path; other types can trigger different notifications.

We can therefore investigate an individual modifier as a persistent check identity rather than infer it from the recipient fleet's changed score. There are 106 modifier-target edges, including 29 negative adjustments. Several negative effects represent imported decisions or losses; they should not become desirable extra checks merely because an ID exists.

Examples:

| Source/action | Potential check interpretation |
|---|---|
| Recruit the Blood Pack / Blue Suns / Eclipse support | Three separate reinforcement candidates; each modifier adds to the Terminus Fleet asset |
| Recover a Banner of the First Regiment | Exploration retrieval candidate; emitted fetch-quest state can support a later delivery check |
| Recover and use Battle Footage intel | Acquisition and terminal-use candidates with distinct bools 21531 / 21532 |
| Recover Intelligence Archives and use them | Acquisition and use candidates with bools 21541 / 21542 |
| Earn a history-derived starting fleet | Baseline state, not a newly performed ME3 action |

Keep recovery, delivery and reinforcement distinct only when the player performs distinct actions. A pickup plus its notification and emitted bool are evidence for one action, not three checks.

`research/le3_gaw_candidates.csv` links asset IDs to emitted bool paths. `le3_gaw_modifiers.csv` lists target/value relationships. `le3_gaw_award_sources.csv` locates the sequence nodes. One modifier references an asset ID absent from the extracted definitions; it remains unresolved.

## Galaxy-map discoveries

The winning local official map package is `DLC_METR_Patch01/.../BioD_Nor_203aGalaxyMap.pcc`, mount priority 4000. It has 77 GAW feature instances, of which 76 have named config matches. The remaining instance is unnamed and under an always-false usability condition.

Named recovery examples:

| Cluster | System | Planet | Recovery |
|---|---|---|---|
| Ismar Frontier | Aquila | Metaponto | Advanced Biotic Amps |
| Nubian Expanse | Dakka | Pragia | Biotic Research Data |
| Nubian Expanse | Kalabsha | Yamm | Alliance Marine Recon Unit |
| Nubian Expanse | Qertassi | Norehsa | Alliance Frigate Trafalgar |
| Exodus Cluster | Utopia | Zion | Prothean Data Files |
| Exodus Cluster | Asgard | Terra Nova | Alliance Cruiser Shanghai |

The 76 config-linked candidates comprise 37 military, seven modifier, twelve salvage, twelve artifact, seven intel and one quest recovery. Do not add these to the 268 asset definitions: they refer to the same GAW system from the interaction side.

`PlanetLandCondition=False` does not make a scan recovery unavailable; most such planets cannot be landed on. Visibility/usability conditions must be traced separately through cluster, system, planet and feature. Serialized omissions may inherit defaults. `research/le3_exploration_sources.csv` retains these explicit conditions and source identities for logic work.

## Mission objectives and other families

`BioSeqAct_GiveMissionXP_NativeBase.Activated` scales the current level's XP allocation by a reward fraction and branches on whether the game's XP award succeeds. Many nodes belong to combat, objective steps or cutscenes. Their existence does not establish a unique, irreversible objective completion. Trace incoming/outgoing links and corresponding plot/journal state before selecting them.

Some `SFXSeqAct_GiveWeapon` nodes explicitly equip enemy troopers and hunters. They are not player weapon checks. Likewise, bulk end-of-level GAW awards can overlap with separately earned assets.

The earlier plot index remains useful for mission completions, assignments, codex, cabin models, intel, social scenes and Citadel activities. Shops, Spectre recovery, normal weapon grants, journal tasks and DLC-specific subclasses still need broader source tracing. The maximum-content history preset should preserve returning characters, but within-ME3 choices and deadlines still need reachability rules.

## Location acceptance record

Before assigning a public AP location ID, each candidate needs:

- A player-facing action and stable source identity.
- A detector proven after disconnect, map change and save/reload.
- A distinction between native source use and the same reward being granted by AP.
- History, story-phase, item and branch prerequisites, plus expiration/recovery behavior.
- A one-time completion rule for repeatable interactions.
- A documented category option and progression-placement policy.

Detailed raw data is retained under `research/`; the current read-only bridge and snapshot helper are under `tools/le3apbridge/`.

## Initial live observations — 2026-10-15

Bridge 0.1.2 reads the authoritative class-default plot table without changing native function flags. A Normandy baseline recorded 21 selected bools, eight selected mission-order ints and 69 GAW entries, including 23 zero-strength IDs. The saved-use list was empty. Presence in an existing save does not establish how or when a source was earned.

The test career only had the Earth finale available. `research/live_earth_session_01` recorded ten changed states with zero read errors over three minutes: Normandy-to-Earth map transition, journal update 22737, opening combat/autosave states, current-objective int10372 advancing to one, shuttle departure and combat-wave/retreat states. These demonstrate working observation, not ten new accepted checks. Technical flags such as Saving_Disabled can return to zero; meaningful action, lifetime and persistence must be established separately. The named transition report is `research/live_earth_transition_analysis.json`.

The tester then collected a medkit and the Cain. Two distinct GUID transitions matched the extracted source objects exactly: rooftop `SFXMedkit_0.TreasureModule0` (AP1295192584) and AA-gun `SFXWeaponNode_0.WeaponUseModule0` (AP1295192353). Cain_Recovered bool19749 simultaneously changed0->1 and current objective2->3. Actual before/after snapshots replayed through the packaged AP detector yielded exactly those two new location IDs. Evidence is in `research/le3_live_check_evidence.json` and `le3_live_detector_replay.json`; the persistence follow-up is below. Neither source was sent to an AP server.

Persistence follow-up passed: both GUIDs remained after the tester created and reloaded a new manual save; the packaged detector recognized the same two locations. Exact GUID bytes appear consecutively in the new save after a count of two, and neither appears in the earlier chapter/pre-test manual saves. Targeted disk evidence is in `research/le3_pickup_save_bytes.json`; it is not a full save parser. Separate-map and fresh-process persistence, failed/full-inventory interactions and other source subclasses remain untested.

Weapon interactions require a further distinction: the decompiled weapon path calls inherited SavedUse.Used before validating/granting the weapon, whereas the treasure path records use only after AwardResource succeeds. A weapon GUID therefore proves a marked interaction, not necessarily a successful item grant. Weapon checks remain experimental.

## Experimental AP manifest

The current source ledger is `world/mass_effect_le3/locations.json`: 527 stable IDs comprising the 423 GUID candidates, 76 exploration candidates, 11 story predicates and 17 specifically named Mars objective completion bools. Generation selects 502 by default; the optional weapon-interaction family adds 25. These counts describe the development manifest, not a runtime-verified release pool.

The generator reserves optional/missable sources for filler while their deadlines and alternatives are audited. It places Crucible Intel in the presumed mandatory pre-finale story/objective checks and gates the modeled finale on that intel. Both those predicates and the native gate still need game validation. The JSON ledger retains evidence and notes rather than losing those limitations when turning research into code.
