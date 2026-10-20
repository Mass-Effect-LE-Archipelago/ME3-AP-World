# LE3 development delivery protocol

Status: 0.2.0 development build, explicitly enabled with `build.py --delivery-dev`. Default CMake/build option is OFF; both parsing and native write callbacks reject mutations in that build. Installed development profile is recorded in the install receipt. This is a standalone research spike, not a playable AP integration.

Live result: the research identity bound successfully; item 0 increased credits 21->1,021, committed cursor 1, and a same-index retry returned done with no extra grant. Wrong seed, wrong history and a gap were rejected without changing state. The owner confirmed the new-save/reload test succeeded before the interruption. On 2026-10-16 disk recovery independently found all 20 expected schema/identity/history/cursor index-value pairs in Save 61 and none in the pre-delivery Save 60. The separate tool-side post-reload inspection receipt was never created because approval review was interrupted by a usage limit; do not ask the owner to repeat the successful test just to recreate that receipt.

The pipe/read-only requests remain compatible with the observation helper. New commands:

| Request | Reply after OK |
|---|---|
| `DEV_SESSION` | `1 research_only unbound 0`, or `1 research_only <identity64hex> <history64hex> <cursor>` |
| `DEV_WALLET` | current credits and maximum credits |
| `DEV_BIND <identity64hex> <history64hex> RESEARCH_ONLY` | `bound research_only` |
| `DEV_TXN <identity64hex> <history64hex> <index> CREDITS <amount>` | `<committed_cursor> <actual_credit_delta> applied`, or `<cursor> 0 done` |
| `DEV_TXN <identity64hex> <history64hex> <index> COUNTER` | same cursor reply, zero credit delta |

Digests must contain exactly 64 hex characters and must not be all zero. Amount is 1..1,000,000; item index is 0..999,999. Unsupported operations and extra tokens are refused. This interface has no generic plot setter, arbitrary resource grant or finale gate.

Binding is permitted only when all 24 owned integers are zero and the current final-decision predicate is false. A partial/foreign storage block is refused. The schema marker is written last. The history digest in this spike names an **existing research save**, not the approved maximum-content preset; no AP client may treat this as initialized history.

Every transaction loads and validates the identity/history of the current save on the HUD/game thread before checking the item index. Lower index -> already done; higher index -> gap error; equal -> execute then commit the next cursor. A queued request cannot use a prior client-side identity read as authority after a save switch. A timeout before dispatch cancels the request; a transaction already executing may finish, so retry uses the same explicit index.

Credit delivery resolves the current player's inventory and calls LE3 AdjustResource with type0, notification=false, ignoreBudget=true. It measures the actual balance against the expected clamped amount. Credits at the cap consume the filler item (delta0), so they cannot block later intel. On an unexpected effect/commit exception, the prior balance and cursor are restored. This is a game-thread transaction, not an assertion of atomic hardware writes or crash-safe external journaling. Native save serialization of both credit and cursor must be demonstrated in the live spike.

## Storage

Owned sparse integer-map keys: `0x4D336000` through `0x4D336017` (1295212544..1295212567). These are **not bool-array indices**. Layout:

| Offset | Meaning |
|---|---|
| 0 | marker 0x4D334150, written last during binding |
| 1 | storage schema1 |
| 2 | received-item cursor |
| 3 | research-only mode1 |
| 4..11 | all eight SHA-256 seed/team/slot identity words, preserving signed bit patterns |
| 12..19 | all eight history digest words |
| 20..23 | reserved, must remain zero |

The chosen range had zero plot-database, typed IntProperty, function-export, native-executable or config hits in the supplied official game/DLC data. Audit scanned 4,454 PCCs and the executable with no errors; 42 raw byte matches belonged to mesh/material/shader/movie/audio data and no matching typed integer properties. All 21 supplied coalesced files were checked. Summary and raw review: `research/le3_delivery_storage_audit_summary.json`, `le3_delivery_storage_audit.jsonl`, `le3_delivery_storage_review.jsonl`. Dynamic arithmetic and third-party mods are outside this bounded audit. Runtime high-key serialization is now supported by the new-save byte evidence in `research/delivery_persistence_recovered_01.json`. The development build helper requires this audit to match the header's range.

SDK `SFXSaveGame.PlotTableSaveRecord.IntVariables` is an array of `FIntVariablePair`, whose Index and Value are each32-bit integers. Together with the live table's sparse IntVariables map, this establishes that these keys do not request a billion-element array. Their actual acceptance/save/reload is still verified separately rather than inferred from the layout.

## Live spike

Only use the disposable career. The original pre-delivery Save 60 was backed up and hash-verified under `build/test-save-backups/pre-delivery/`; no test helper edits save files on disk.

```powershell
python tools/le3apbridge/delivery_probe.py inspect research/delivery_inspect_01.json
python tools/le3apbridge/delivery_probe.py bind-test-save research/delivery_bind_01.json
python tools/le3apbridge/delivery_probe.py credits research/delivery_credit_01.json --index 0 --amount 1000
```

The credits command deliberately retries the same index and records wallet/source inventories before/after. It never contacts AP. Then create a **new** manual save, reload it, inspect again and retry index0: credits/cursor/identity must persist and the retry must grant nothing. Loading the backed-up pre-binding save should show unbound state and its original balance. Wrong-seed requests must fail without mutation.

Native tests (35 assertions) cover those transaction policies with a fake host, including high-bit digest words, state collisions, missing pawn, capped rewards, malformed requests, post-write failure rollback and save-switch identity validation. They do not establish actual engine calls or save serialization. Build logs and real pipe receipts distinguish these evidence levels.
