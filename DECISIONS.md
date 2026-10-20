# Project decisions

## D1 — Seed creation includes selectable Shepard history

Updated by the user on 2026-10-16: include a history selector for major decisions, romances and related background so the randomized campaign retains the player's Mass Effect story. This supersedes the 2026-10-14 fixed-preset-first decision.

Retain maximum-content as a convenient preset, alongside explicitly selected custom history. Resolve the complete inherited history before generating the location pool or placing progression. Store that resolved profile in slot data and bind it to the career. Apply it during AP career creation before dependent ME3 state initializes. Retain character customization where it does not affect story/romance eligibility.

The selector must validate mutually exclusive outcomes, survivor/loyalty/romance dependencies, and resulting check availability. Exclude genuinely unavailable checks rather than overriding the player's chosen past. Expose options only when their native initialization and affected-source rules are mapped. ME3 decisions during gameplay remain player choices; timed/mutually exclusive current-game checks require separate rules. See `HISTORY-SELECTOR.md` for the design and implementation order.

## D2 — Granular check coverage is the primary catalog objective

User priority: “the most checks it can have” and minute options for check families. Catalog individual recoveries, rewards and reinforcement sources rather than stopping at mission completions. Optional finite milestones can supplement distinct interactions. Definitions and raw flags are research evidence, not approved checks.

The user suggested Galactic Readiness as an additional check source. Investigate GAW assets, modifiers, discoveries, intel and military-strength milestones separately.
