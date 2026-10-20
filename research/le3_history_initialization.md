# History initialization: source evidence

Reviewed 2026-10-16. This identifies a candidate integration point and one source-proven decision bundle. It does not establish runtime initialization or check reachability.

## New-career order

`le3_history_callers.jsonl` contains decompiled functions from the supplied vanilla `SFXGame.pcc`:

- `BioSFHandler_NewCharacter.FinalCommit`, export 20372, creates the career, copies imported data when applicable, calls `SetNewGamePlotStates`, adds starting codex entries, then calls `SetPlotChoices` for a non-imported new game. It subsequently updates the player save record and activates `re_StartNewGame`.
- `BioSFHandler_NewCharacter.SetPlotChoices`, export 20374, writes the four Virmire flags below to `oWorldInfo.GetGlobalVariables()`.
- `BioSFHandler_NewCharacter.ProcessExternalStates`, export 20470, also calls `SetNewGamePlotStates` on a newly allocated temporary table when previewing imported characters.

Candidate for a deliberately armed AP fresh career: apply the resolved history after the original `SetPlotChoices` finishes within `FinalCommit`, before the player save record update and campaign start event. This ordering avoids the vanilla Virmire chooser overwriting the AP choice. It still needs runtime verification: native default/fixup behavior, downstream derived state, call interception, and save persistence are not proven by this decompilation. Imported careers skip this call, so import support needs a separately reviewed path.

Do not hook every `SetNewGamePlotStates` invocation indiscriminately: import previews also invoke it. Ordinary careers and preview tables must not receive AP history or binding state.

## Source-proven Virmire bundle

Stable proposed history key: `me1.virmire_survivor`, values `ashley` or `kaidan`.

| Bool index | Meaning | Ashley survives | Kaidan survives |
|---|---|---|---|
| 13827 | Rescued Ash | true | false |
| 13828 | Rescued Kaidan | false | true |
| 13940 | HumanFemale in party | true | false |
| 13939 | HumanMale in party | false | true |

The complete complementary writes come directly from `SetPlotChoices`; indices independently match the named aliases in `le3_history_config.jsonl` and paths in `le3_plot_inventory.csv`. These are inherited state, not instructions to keep the survivor alive through subsequent ME3 decisions. The vanilla enum's `AshleyDies` means Kaidan survives; its `KaidenDies` spelling means Ashley survives.

No location exclusions or counts have been established for this choice. Do not expose it as supported seed logic until source dependencies and native initialization have been verified.

## Selector responsibilities

The shared profile must distinguish ME1 romance history, ME2 romance history, continuation/breakup state, and partner survival. A partner's later death does not invalidate the fact of an earlier relationship. Map the game's actual import/fixup rules before imposing compatibility restrictions or writing plot bundles.

Origin and service history also feed `CreateCareer` through `PlayerInfoEx.Origin` and `Notoriety` before the candidate plot hook. A profile that owns those values must resolve them before career creation and keep player/save records consistent; changing only plot booleans afterward would not cover this path.

Next mapping work: Wrex and squad survival, major ME1/ME2 outcomes, romance timelines, then affected source availability. Keep unsupported choices out of generated production slot data. The existing full-history digest can bind resolved choices once initialization is implemented.

## Implemented readback verification

`world/mass_effect_le3/history.py` now mirrors 11 major-plot getters, including the native precedence rules for conflicting values. ME1 romance needs its active bool plus a dialogue counter >=4; ME2 romance uses relationship int ==5. Wrex's reader distinguishes ignored/dead/alive and gives the in-party flag priority over death flags. The squad count uses all 12 in-party slots; the Mystic slot does not distinguish Samara from Morinth. None of these summaries establishes a complete past-history timeline.

`python tools/verify_history_mapping.py` cross-checks the referenced aliases/indices with config and database paths and checks both native Virmire setter branches. Receipt: `le3_history_mapping_validation.json`. Eight history tests cover thresholds, conflicts, missing/malformed reads and all squad slots; the complete suite passes 34 tests plus 116 subtests. These are offline checks, not runtime proof of initialization.

`python tools/le3apbridge/history_probe.py research/new_history_receipt.json` uses only existing read channels. With `--from-snapshot <path>` it works offline. Receipts retain the raw snapshot, recognized values, diagnostics and whether a live game was contacted. Existing pickup-only snapshots are insufficient and correctly fail without writing a receipt. No new game snapshot was taken during implementation.

## Retained Genesis transition bundles

The read-only probe now has a `--state-events` mode, because normal export properties omit the binary state-event data. The supplied Genesis startup package contains `PlotManagerAutoDLC_CON_DH1.StateTransitionMap` at export 3: 48 transitions, 437 elements, including 41 native substate operations. The base `SFXGameInfoSP_SF.pcc` map at export 5 contains 4,159 transitions. The package scan found nine state-event-map exports across 3,229 non-localized PCCs, with zero scan errors (`le3_plotmap_scan.log`). Empty consequence maps are not extra transitions.

Reproduction from the project root:

```powershell
dotnet tools/research/Le3Probe/bin/Debug/net10.0-windows/Le3Probe.dll --state-events 'ME3LE Backup/BioGame/DLC/DLC_CON_DH1/CookedPCConsole/Startup_CON_DH1_INT.pcc' 'ME3LE Backup/BioGame/CookedPCConsole/SFXGameInfoSP_SF.pcc'
python tools/research/build_history_catalog.py
```

The first command's captured output is `le3_history_state_events.jsonl`. The second creates `le3_genesis_transition_catalog.json`, matching every target/parent/sibling to its database path and retaining complete native elements and dialogue references. Sixteen choice mappings are annotated: 14 ME1 choices with resolved English narration, plus both Collector Base outcomes whose effects directly match the named imported plots. The catalog is research data, not production slot data or a runtime initializer.

| Choice | Transition IDs |
|---|---|
| ME1 romance | Ashley 5597; Kaidan 5598; Liara 5599; none 5600 |
| Rachni Queen | killed 5610; saved 5611 |
| Wrex | dead 5612; alive 5613 |
| Virmire survivor | Kaidan 5614; Ashley 5615 |
| Council | saved 5616; sacrificed 5617 |
| Human councilor | Udina 5618; Anderson 5619 |
| Collector Base | preserved 5763; destroyed 5764 |

Genesis Virmire transitions independently reproduce all four writes in the character-creation setter. Romance transitions supply the active flag and recognition counter, but selecting a new partner alone does not clear the others. Rachni, Council and Wrex transitions use native substate elements with parent and sibling metadata. Do not reduce those to raw target booleans.

Event 5915 clears 111 elements spanning ME1 **and ME2**, including squad, loyalty, death, crew and relationship state. It cannot serve as an isolated ME1 reset. The ME2 result bundles (5835, 5842, 5844–5849) combine recruitment, loyalty outcomes and survivors; romance bundles 5850–5853 also change survival/loyalty. A custom selector must separate the requested facts and avoid silently resurrecting or making a character loyal when selecting romance history.

The native `BioWorldInfo.ExecuteStateTransition(int nTransition, int nParam)` entry point is a candidate executor that would retain substate semantics. Its SDK parameter record has two ints. Invocation, map availability during career creation, side effects and readback still require verification; no new bridge write command has been added.

Reachability caveat: 45 catalog transitions have retained conversation-node references, but only 14 have resolved English text in the supplied INT talk files. Old Genesis data and the current patched character package both retain parts of the comic flow; those facts do not establish that every branch runs in LE3. Do not treat the retained comic as the AP player flow or skip its ordering review. Current patch character-sequence evidence is in `le3_current_character_sequence.jsonl`.
