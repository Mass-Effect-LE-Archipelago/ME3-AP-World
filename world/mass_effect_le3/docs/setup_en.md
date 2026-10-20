# Mass Effect Legendary Edition 3 — experimental setup

This development build can generate seeds and evaluate cataloged source observations. It is **not a playable release**: maximum-content history initialization and the native finale gate remain unfinished. Native research identity, indexed credit delivery and duplicate suppression have been tested in-game. A receive-only AP development client is available separately from normal campaign synchronization.

The world targets Archipelago 0.6.8 or newer. Place `mass_effect_le3.apworld` in the local `custom_worlds` directory and restart Archipelago. The game is hidden from the public game list while under development. Generate locally with the provided development YAML.

The launcher registers `ME3 Client (Experimental)`. Normal campaign synchronization deliberately remains blocked until history initialization and real mission gating exist. Research delivery support does not make an existing save a valid randomized campaign.

## Receive-only delivery testing

With this world importable in an Archipelago environment, launch:

```text
python -m worlds.mass_effect_le3.client --delivery-test --connect localhost:38281 --name ME3Developer
```

This explicit mode accepts Credits1000 and Crucible Intel counters through the 0.2.0 delivery-development ASI. It sends **no location checks or goal completion**, applies no Shepard preset and unlocks no missions. Use a disposable save. Add `--bind-research-save` only to deliberately bind an unbound test save to the connected room's seed/team/slot. A previously bound save from another test seed is refused; it is never rebound. The standalone credit-test Save 61 belongs to its earlier research seed, so it will not match an arbitrary AP room. The pristine pre-binding Save 60 remains available for a later, separate AP network/game test.

Native pipe, credit delivery/retry and save storage have live evidence. The new AP receive-only mode passed tests and a real localhost server round-trip with a **fake native protocol endpoint**. A combined real-server-to-real-game run has not yet been logged. The CLI has no option to enable campaign check/goal reporting in this mode.

The world catalog includes 527 stable source IDs: 423 saved-use interactions, 76 exploration recoveries, 11 story predicates and 17 Mars objective predicates. Default options select 502 checks; the heavy/special weapon interaction option adds 25. Predicates and source reachability still need runtime validation. Optional/missable pickup and exploration checks are filler-only while that audit is incomplete.

The intended goal requires Crucible Intel before launching the final assault, followed by the game's final decision. Generation implements that rule; **the game does not enforce it yet**. Do not host this build for a real multiworld playthrough.

Use the project's research bridge snapshot helper to validate source GUIDs, GAW asset IDs and plot predicates on a disposable test career. A read-only bridge must not be treated as proof that item delivery or history initialization works.
