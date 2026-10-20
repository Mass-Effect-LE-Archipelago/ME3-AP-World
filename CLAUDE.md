# Mass Effect 3 LE Archipelago development

Read [CLAUDE-HANDOFF.md](CLAUDE-HANDOFF.md) first, then [CURRENT-STATUS.md](CURRENT-STATUS.md) and [HISTORY-SELECTOR.md](HISTORY-SELECTOR.md).

The project is experimental and not a playable randomized campaign yet. Continue the existing implementation; do not restart feasibility research. The user's priorities are maximum granular check coverage and selectable inherited Shepard history during seed creation.

The most recent native career observer changes are **uncompiled and uninstalled**. Existing native binaries/tests predate them. The normal AP client intentionally blocks production synchronization until initialized history and real mission gating exist.

The owner already confirmed the credit delivery/save/reload test succeeded. Do not ask them to repeat it because the last tool receipt was interrupted. Keep real-game evidence, owner confirmation, offline tests and fake-endpoint network tests distinct.

`HANDOFF.md` is a historical work log containing obsolete instructions. It is not the current task list. Preserve existing source IDs, test-save backups and vanilla analysis inputs. Inspect the actual checkout and receipts before changing the live installation.
