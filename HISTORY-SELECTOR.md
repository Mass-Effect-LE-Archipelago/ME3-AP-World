# Seed-bound Shepard history selector

Adopted direction, 2026-10-16. This replaces fixed-history-only first-release scope; it does not claim the selector is already playable.

## Player flow

1. Choose a preset or custom inherited history while creating the seed. Maximum-content remains a convenient starting point.
2. Select major ME1/ME2 outcomes, survivor and loyalty states, imported romance, and relevant Shepard background. The selector explains contradictions and shows known effects on available content/checks.
3. Resolve and validate a single coherent profile before generation. Any future optional random/weighted history selections must resolve here, once, using the seed RNG.
4. Generate regions, locations, pool size and progression placement from that exact profile. Show its resolved choices in the seed's spoiler/setup output and slot data.
5. Create an AP career using that profile before ME3 derives character, journal, mission or war-asset state. Bind the full profile digest to the save; mismatches require the matching career or a new one.

The history editor/creator writes ordinary AP YAML/options; generation must validate those options even when players edit YAML by hand. UI validation alone is insufficient. A separate graphical YAML creator can follow the same shared schema; no standalone website/service is required.

## Initial choice families to map

| Family | Examples to research/map | Logic responsibility |
|---|---|---|
| Shepard | origin, service history, story-relevant identity | Preserve customization where it does not conflict with imported story/romance facts. |
| ME1 major decisions | Virmire survivor, Wrex, Council, Rachni | Select available characters and alternate content; never enable mutually exclusive past outcomes together. |
| ME2 squad/crew | recruitment, survival, loyalty, rescued crew | Map returning-character scenes, assignments and their source checks. |
| ME2 major decisions | relevant loyalty outcomes, research, geth/Collector choices | Initialize coherent plot bundles and account for downstream variants. |
| Romance | inherited relationship/timeline and relevant DLC continuity | Validate compatibility with the chosen history and identify affected scenes/checks. |

These are scope examples, not verified option enums or plot-write instructions. Exact vanilla constraints, DLC interactions and plot bundles must come from the supplied databases/scripts and game tests.

Romance is a timeline: record relevant ME1 and ME2 relationships, breakups and DLC continuity separately. Past romance and ongoing relationship status are distinct facts. Do not erase a past relationship solely because it ended or the character later died; validate the actual game-supported combination and its resulting content. The schema can share ME1 history keys with an ME2 selector, while the ME3 adapter additionally handles the resolved ME2 history. This project does not modify the ME2 reference checkout.

## Check and progression rules

- Remove checks that cannot exist under the selected inherited history. Keep stable location IDs for the same source across profiles; do not renumber the ledger.
- Use alternate checks only when they represent documented reachable alternatives. Do not invent an equivalent reward event merely to preserve the count.
- Recompute progression placement capacity and item totals after history filtering. Custom histories may yield fewer checks; show that tradeoff instead of silently rewriting the story.
- Keep current-ME3 choices playable. Use branch-neutral checks or exclude branch-dependent sources from progression until their reachability is proven. Seed history by itself cannot make every future branch safe.
- Preview only verified counts/availability. Unknown dependencies remain explicitly unsupported or conservative, never presented as fully validated coverage.

## Data and native contract

One versioned resolved profile is authoritative for options, generation, client and native initialization. Include stable decision keys and resolved values, not transient UI labels. Hash every resolved choice along with preset/schema version; runtime support metadata is not a story choice. Different custom histories using the same preset name must never share a history digest.

The existing native state reserves a full SHA-256 history digest. Its current research-only mode explicitly names an existing test save and must not be promoted into a real history profile without initialization and verification. Normal campaign synchronization stays blocked until native initialization and real gating exist.

Native initialization needs explicit reviewed plot bundles, including clearing opposite outcomes and applying dependent import/fixup state. Copying favorable flags onto a running save is insufficient. Identify the earliest reliable career-creation hook before derived ME3 state is initialized, then verify each supported profile through save/reload.

Source review has identified the new-character commit order and the four complementary Virmire flags. See [native initialization evidence](research/le3_history_initialization.md). The candidate hook follows the vanilla fresh-career plot chooser; import-preview tables also initialize plots, so interception must distinguish them. Origin/service history require earlier player-record handling. This is source evidence, not a verified in-game selector.

## Implementation order

1. Shared history schema and dependency rules; map supported major-decision/romance bundles to native plots and affected catalog entries.
2. Native new-career initialization and verification for the supported profiles.
3. AP history options and profile-driven location/region filtering; validation, spoilering and full profile hashing.
4. Optional history/YAML editor using that schema, with availability previews and presets.
5. Expand secondary history choices as their native behavior and check dependencies are verified.

Do not expose custom history options on the current 527-source world before the initialization and availability mapping exist: the current pool only filters by category/DLC, so doing so would claim unsupported reachability.

## Implemented offline profile compiler

`world/mass_effect_le3/history_profile.py` defines a shared 51-fact draft schema, resolves the proposed maximum-content preset or custom overrides into a complete versioned profile, and validates structural dependencies. Recruitment, survival and loyalty are separate facts for all 12 ME2 squad slots; past romance/loyalty can remain true after a later death. The Mystic slot has a separate Samara/Morinth identity. Background, major decisions, crew rescue, separate ME1/ME2 romances and Liara relationship continuity are represented. Appearance customization is not assigned by this draft schema.

These are requested-story fields, not a claim that every combination is legal in vanilla. Sex/romance compatibility, intermediate relationship timelines, ME1 romance/Virmire constraints and native/player-record mappings still need review. The preset's all-recruited/alive/loyal choices aim at more returning content; no check-count optimum has been established. Overrides are labeled `custom` and never silently corrected. Serialized resolved profiles must contain every fact; loading a profile does not fill missing facts from current defaults.

The offline compiler loads `history_bundles.json` from the AP package and composes seven source-mapped decision families. It clears ME1 romance alternatives before applying a selected partner, preserves native parent/sibling metadata, and does not substitute the broad Genesis reset or ME2 romance bundles that also change loyalty/survival. It reports every unmapped fact, including explicit false values. Preview artifacts are always marked non-executable and `implemented_in_game: false`; normal AP generation still uses its earlier placeholder history and blocks campaign synchronization.

From the project root:

```powershell
python tools/research/build_history_catalog.py --sync-world
python tools/preview_history.py build/new-history-preview.json
python tools/preview_history.py build/new-custom-history-preview.json --input research/history-custom-example.json
```

The preview tool is offline, contacts neither game nor server, and refuses to overwrite artifacts. Input is currently JSON for development; the future AP YAML options/editor will use this same schema. Output contains the full resolved profile, its full history digest, complete mapped native elements, direct readback targets and an explicit mapping-gap list. Direct targets omit parent/substate processing and do not prove runtime initialization. The default profile currently has seven mapped families and 44 unmapped facts.
