# ME2 delivery reference for LE3

Reviewed 2026-10-15 after the owner pointed to the updated repository.

Reference checkout: `ME_Archipelago_Background`, branch `claude/me2-ap-world`, fast-forwarded cleanly to `cab3dea3012acff9ae5609e805a1e1c2f770f1eb`.

## Reuse the transaction design

`tools/le2apbridge/LE2APBridge/Bridge.cpp` implements `TXN <index> <op> ...`:

- Save cursor greater than index: return `done`, apply nothing.
- Save cursor less than index: reject the gap.
- Equal: apply the whitelisted operation, then advance the cursor in the same game-thread dispatch.
- Client retries a lost reply using the same index. Loading an older save replays only its missing suffix.

ME2 also stores identity in save plot integers, refuses rebinding a non-empty identity, rejects binding a post-game save, validates allowed operations and batches source reads. Its 2026-10-15 SCOPE notes record a live resource transaction, skipped retry and AP plot persistence. Those notes still leave ID/IDSET testing and visible credit-amount verification open; README's broader 'not yet run' status is stale relative to SCOPE.

LE3 `client_core.py` already models indexed delivery, lost-reply recovery and save-owned identity checks. Implement its native counterpart using this reference. Do not replace it with a client-only received-item cursor.

## LE3 adaptations established locally

1. Keep the LE3 HUD-thread dispatch and the corrected native calls. LE3's global plot table is an authoritative class-default singleton. Generated SDK native wrappers contain a function-flag mutation defect; the tested LE3 reader bypasses them.
2. Allocate a separately audited LE3 state block. ME2 bool21000–21999 collides with 900 LE3 database rows. Proposed LE3 int30000+ remains provisional until compiled/native references, other mods and serialization are checked.
3. Preserve the LE3 client's full seed/team/slot SHA-256 identity and versioned maximum-content history identity. ME2's CRC31 seed plus packed team/slot is a reference wire/storage scheme, not a reason to weaken this contract. Reject completed careers at binding, using an LE3 goal predicate once validated.
4. Local LE3 decompilation confirms `SFXInventoryManager.AdjustResource` exists with resource type0 = credits, amount, show-notification and ignore-budget arguments. Credit delivery should resolve the active player's inventory, bypass the native treasure budget intentionally, measure the resulting credit value, and account for MaxCredits clamping before committing the cursor. A void return alone is not proof that the expected amount arrived.
5. Do not copy LE2 ship-upgrade bools, weapon-unlock ints, resource pool or IFF gate. The initial LE3 item pool remains Crucible Intel (counter) and Credits1000. The finale gate must affect real mission access before the world is playable.
6. Validate first credit delivery, duplicate retry, save/reload, loading the pre-delivery save, wrong-seed rejection and timeout/save-switch behavior. Native binding checks should accompany mutations, including queued requests, rather than relying solely on a prior client-side identity read.

LE3 API evidence: `research/le3_delivery_api_scripts.jsonl`, decompiled read-only from local `SFXGame.pcc`. It includes AdjustResource/GetResource/AwardResource and the native plot setter declarations. No reward writes have been installed or run as part of this review.
