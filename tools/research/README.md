# LE3 research tools

Run from the project root. These tools read the supplied DLL/game backup and write research outputs; they do not modify packages or install a mod.

## Plot inventory

```powershell
python tools/research/le3_plot_inventory.py
```

Uses Python's standard library. Reads `Legendary Explorer/LegendaryExplorerCore.dll`, locates its embedded plot ZIP and inventories `le3.json`. Parent IDs are normalized because organizational entries use strings while leaf entries use integers.

Produces `research/le3_plot_inventory.csv`, `le3_check_candidates.csv` and `le3_plot_summary.json`. Discovery tags overlap; `DB_ONLY` rows are unverified research leads. Legacy import branches remain in the full inventory but are omitted from the candidate subset. The `review_hint` field is only a name heuristic, not an exclusion decision.

## Package export probe

Requires the installed .NET 10 SDK and the supplied Legendary Explorer libraries. It loads Oodle from the supplied backup. No NuGet package dependencies are declared.

```powershell
dotnet run --project tools/research/Le3Probe -- 'ME3LE Backup/BioGame/CookedPCConsole/SFXGame.pcc'
```

Pass one or more PCC paths. Loads export/import/name tables without export bodies and prints selected class/property/function/object names. `--api` prints selected local library APIs for troubleshooting. It has no package-save calls.

The checked-in probe output is static structural evidence, not decompiled behavior or runtime verification. For galaxy-map instances, omit class default objects and compare mounted package variants before deduplicating actual sources.

## Full source catalog pipeline

```powershell
python tools/research/run_catalog.py
python -m unittest tools.research.test_research -v
```

The pipeline rebuilds the probe, inventories plots, reads relevant coalesced sections, mounts and map object properties, resolves requested English names, and scans non-localized packages for selected reward classes. It emits config/asset, exploration, saved-pickup, GAW-award and objective-XP tables. A full reward scan reads 3,229 packages on the supplied backup. Use `--skip-reward-scan` only when the existing reward source scan is still current.

Additional probe modes:

- `--audit-int-block <first> <count> <directory-or-file> ...`: scan decompressed export data and raw native files for an aligned 256-page subrange of 32-bit values; includes all localized/overridden packages. Emits exact raw matches and completion/error counts.
- `--review-int-block <audit-jsonl>`: classify matching exports and inspect typed integer/struct/array properties, distinguishing incidental bulk-data bytes from meaningful integer fields. Config and DB checks remain separate; raw hits alone are not plot-reference proof.

- `--config <bin> ...`: selected GAW/treasure sections as JSON lines.
- `--objects <class-regex> <pcc> ...`: selected object properties.
- `--scan-objects <class-regex> <directory> ...`: recursive PCC scan with `_LOC_` packages omitted; errors are logged and make the command fail.
- `--mounts <dlc-directory>`: local official mount priorities.
- `--strings <json-ref-list> <tlk> ...`: only requested string references.
- `--script <function-path-regex> <pcc> ...`: decompile selected functions for local behavior research.

`le3_config_catalog.py` parses nested Unreal struct declarations including indexed fields and quoted commas. It preserves source/config actions. `le3_source_catalog.py` joins assets, names, emitted bools and map ancestry. `le3_reward_catalog.py` resolves higher-mounted package copies before selecting physical use modules and sequence candidates; it also checks overriding packages that contain no matching source objects.

The reward scan currently selects `SFXSeqAct_AwardGAWAsset`, its silent variant, `SFXSeqAct_AwardGAWAssetsForLevel`, `BioSeqAct_GiveMissionXP*`, `SFXTreasureNode`, `SFXSeqAct_GiveWeapon`, and the treasure/weapon/mod/armor use-module classes plus bonus-weapon modules. Additional scripted grant paths and DLC subclasses remain to investigate.

Local behavior evidence is retained in `research/le3_behavior_scripts.jsonl`. It contains decompiled game methods for private analysis; use the summarized findings in `CHECKS-CATALOG.md` for project documentation. No vanilla package binaries were copied into mod output.
