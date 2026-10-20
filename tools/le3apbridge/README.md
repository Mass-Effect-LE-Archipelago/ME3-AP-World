# LE3 read-only research bridge

Current implementation/install status is tracked in `../../CURRENT-STATUS.md`; the 0.1.2 observations below are historical read-channel evidence. The currently installed build is 0.2.0 delivery-development, described under Build and in `DELIVERY-PROTOCOL.md`.

## History readback

`python tools/le3apbridge/history_probe.py research/new_history_receipt.json` collects 33 bools and nine ints for the source-mapped vanilla major-plot readers. It summarizes recognized ME1/ME2 choices/romances, Wrex state and squad count, retaining raw reads and warnings. Use `--from-snapshot <path>` for offline analysis of a complete snapshot. Missing values are refused; existing pickup-only snapshots do not contain these plots. This tool reads only and does not bind, initialize or modify a career. Later ME3 events may change these plots, so the output is not a full reconstruction of imported history.

`python tools/verify_history_mapping.py` checks reader indices/romance thresholds and the four complementary Virmire setter flags against extracted vanilla script/config/database evidence. Runtime initialization and affected-check mapping remain unfinished.

Status: version 0.1.2 installed and read channels verified in gameplay on 2026-10-15. The baseline captured 21 bools, eight ints and 69 GAW entries (23 zero-strength). Exact GUID transitions for the Earth rooftop medkit and AA-gun Cain matched the extracted objects and packaged AP detector; both survived a new manual save/reload. Their bytes are present in the new save and absent from earlier saves. Fresh-process and separate-map persistence are not yet tested. `PLOTINFO` confirmed the authoritative table is a class-default singleton; native function flags were unchanged across fixed reads. This remains research infrastructure: no grants, setters, seed binding, history initialization or AP location reporting.

## Build

Development delivery work is in `DELIVERY-PROTOCOL.md`. The explicitly selected0.2.0 development build is installed; normal builds keep writes disabled. A live item raised credits 21->1,021 and cursor 0->1, retry granted nothing, and wrong identity/history/gap requests were refused. Save/reload success is owner-confirmed; all 20 expected persistent fields were independently recovered from the new save on 2026-10-16. Both profiles compile and pass 35 native transaction checks; five installer rollback/profile checks pass. The receive-only AP client is now wired to this protocol; its network test uses a fake native endpoint and sends no checks/goals.

From the project root:

```powershell
python tools/le3apbridge/build.py
```

Requires Visual Studio 2026 C++ and Windows SDK, Python and the dependency checkout at `tools/vendor/LExASIs` including its submodules. The build script normalizes the child environment to avoid MSBuild's duplicate PATH/Path issue and removes upstream game-copy environment variables. It writes only workspace build artifacts.

Output: `tools/le3apbridge/build/bin/Release/LE3APBridge.asi`.

Dependency revisions used:

- LExASIs: `aaad03ab6e5112e27ff5528f7b08c3bcf3870c31`
- LExSDKv2: `3885be14113816ff1d2a0d941aa96bba6df9dc58`

## Read-only protocol

Pipe: `\\.\pipe\LE3APBridge`, local clients only, message mode. One ASCII request and one UTF-8 response per message. Replies begin with `OK` or `ERR`. At most 4,096 request bytes and 64 plot indices per batch; indices 0–65,535.

| Request | Reply payload after `OK` |
|---|---|
| `PING` | `pong` |
| `HELLO 1` | `1 LE3 readonly` |
| `VER` | `0.1.0-research` |
| `CAPS` | supported read commands |
| `MAP` | outer package name of the HUD's world |
| `GETB n`, `GETI n` | one plot value |
| `GETBS n ...`, `GETIS n ...` | values in request order |
| `GAW` | count followed by `asset_id:strength` pairs; includes zero-strength modifier IDs |
| `PLOTINFO` | authoritative table name, default-object status, object flags, bool-word count and native function flags |
| `USES offset count` | total used-GUID count followed by up to `count` signed `A:B:C:D` GUIDs; count 1–128 |

Metadata requests are answered by the pipe thread. Game reads run only at the `SFXGame.BioHUD.PostRender` callback with a re-entrancy guard. Requests time out after five seconds if that callback is unavailable, including potentially some paused/menu/loading states. `ERR noworld`, `noplayer`, `nogaw`, `noengine` and `noplots` indicate unavailable state. The module is pinned for the process lifetime so its pipe thread cannot execute unloaded code.

The `USES` command reads `SFXEngine.UseModuleList`. Decompiled `SFXModule_SavedUse` methods identify it as the source used by `HasBeenUsed`; `SFXSaveGame` also declares `UseModuleRecords`. Persistence across saves and reloads still requires an actual game test.

## Runtime validation, when the owner returns

Use a disposable test career. The live installation now has this ASI plus a locally built, unmodified [official ME3Tweaks loader](https://github.com/ME3Tweaks/LEBinkProxy), source commit `1c435d8df0367642d9fc8572b67b6ae92295967e`. Installed hashes and the backup location are recorded in `research/live_install_receipt.json`. A loader-compatible binary existing is not evidence that these requests work in-game.

Inspect with `python tools/le3apbridge/install_research.py inspect`. With the game closed, restore the original DLL and remove this ASI using `python tools/le3apbridge/install_research.py restore`; the helper refuses changed files. `update` installs a newly hash-pinned research build and backs up the previous ASI. It leaves research logs and the verified workspace backup intact. Live writes require host approval outside the workspace. Four isolated tests exercise restoration, changed-file refusal, copy-failure rollback and restoration after an update: `python -m unittest tools.le3apbridge.test_install -v`.

Build the loader with `python tools/le3apbridge/build_loader.py`. Its local MSBuild invocation needs execution outside the restricted sandbox; sandboxed compiler IPC produced LNK1101. The build makes no game writes.

After installation and loading a test career, take a baseline while idle:

```powershell
python tools/le3apbridge/probe.py snapshot research/before.json --catalog-plots
```

Perform exactly one action, then:

```powershell
python tools/le3apbridge/probe.py snapshot research/after.json --catalog-plots
python tools/le3apbridge/probe.py diff research/before.json research/after.json
```

The helper refuses to overwrite earlier observations. Snapshots record UTC times, map, requested plots, GAW inventory and the used-GUID list. Each native request is a frame-level read, but a whole snapshot spans frames. Stay idle while it is collected; the helper rejects map changes and changes to the used-GUID count during pagination.

Test one successful fixed credit cache, one medi-gel interaction at full inventory and after using a charge, an armor/mod pickup, a scan/probe recovery and a positive asset modifier. Save and reload, change maps, and repeat with the AP helper disconnected during the action. Match observed GUIDs to `research/le3_saved_pickup_sources.csv` and asset IDs to `le3_gaw_candidates.csv`.

Only after those observations should the bridge gain save-owned AP state or reward writes. Source checks must remain independent of the same item arriving through AP.

For a bounded read-only recording while the tester plays:

```powershell
python tools/le3apbridge/watch_research.py research/new_earth_session --seconds 180 --interval 5
```

The output directory must be new. This includes the manifest's plot predicates plus the database's `LE3.End_Game.` bools/ints, saves changed snapshots and deltas, and logs transient read failures during loading. `session.json` maps plot IDs to source paths. It reads only, stops at the requested duration, and never sends AP checks. Capturing a transition proves an observed state change; assigning a check still requires availability, reset/persistence and distinct-action review.
