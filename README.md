# Mass Effect 3 Legendary Edition Archipelago project

For continuing development in Claude Code, read [the current transfer handoff](CLAUDE-HANDOFF.md). `CLAUDE.md` points Claude Code to it automatically. The handoff distinguishes the tested delivery binaries from the latest uncompiled native observer source.

Start with [the feasibility overview](ME3-FEASIBILITY.md).

Current status: an experimental AP world generates real development seeds, with a stable 527-location source manifest. Plot/map/war-asset reads, two Earth pickups, research save binding and indexed credit delivery/retry were verified in-game. The owner confirmed delivery save/reload succeeded; all 20 expected persistent fields were recovered from the new save. An explicit receive-only AP client now uses the native delivery protocol while suppressing check/goal reporting; its localhost integration test uses a fake native endpoint. 24 tests and 102 generation subtests pass. Maximum-content history initialization and real mission gating remain unfinished, so this is not a playable randomized campaign. See `CURRENT-STATUS.md` and `tools/le3apbridge/DELIVERY-PROTOCOL.md`.

Development artifacts: `build/mass_effect_le3.apworld`, `Mass Effect Legendary Edition 3 - Development.yaml`, and `build/development_seed/`. Build with `python tools/build_apworld.py --sync`. The source world is under `world/mass_effect_le3/`.

Read [the check catalog](CHECKS-CATALOG.md), [functionality design](FUNCTIONALITY.md), [confirmed decisions](DECISIONS.md) and [handoff](HANDOFF.md) for the current implementation state.

- `research/`: generated plot inventory, candidate index, source hashes and package export evidence.
- `tools/research/`: read-only discovery tooling; see its README.
- `tools/le3apbridge/`: compiled research ASI, source, protocol and snapshot/diff helper.
- `ME_Archipelago_Background/`: cloned ME2 reference branch, retained as a separate repository.
- `other randomizers/masseffect1/`: supplied ME1 reference implementation.
- `Archipelago-main/`: supplied Archipelago source.
- `ME3LE Backup/`: supplied vanilla backup, used only as an analysis input.
