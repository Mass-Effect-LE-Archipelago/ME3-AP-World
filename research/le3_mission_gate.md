# Cerberus HQ / Earth entry gate: source evidence

Reviewed 2026-10-20 from the supplied vanilla `BioD_Nor_203aGalaxyMap.pcc` and `SFXGame.pcc` with `Le3Probe --objects` / `--script`. Static evidence only; no runtime test yet.

## Galaxy map entry

Mission planets are `BioPlanet` objects under `biog_galaxymap.GalaxyMap.SFXCluster_N.SFXSystem_N`. Each landable mission names its level in `MapName` and its landing conditional in `PlanetLandCondition`.

| Export | Path | MapName | PlanetLandCondition | CritPathPlot |
|---|---|---|---|---|
| 319 | `SFXCluster_2.SFXSystem_0.BioPlanet_2` | `BioP_End001` (Cronos Station / Cerberus HQ) | 78 | true |

Earth (`BioP_End002`) is not a galaxy map destination; it follows Cronos Station, so gating Cronos Station landing also gates Earth.

`SFXGame.BioPlanet.CanBeInteractedWith` (export 13300) is a script **event** that returns `BioWorldInfo.CheckConditional(PlanetLandCondition)`. A decompile of every SFXGame function under GalaxyMap/BioPlanet/SFXSystem/SFXCluster found no script caller, so the native galaxy map calls it as an event through `UObject::ProcessEvent`, which the bridge already hooks. `CheckConditional` (export 18047) is native.

## Proposed gate (not implemented)

After the original `CanBeInteractedWith` returns, if the planet's `MapName` is `BioP_End001`, the loaded save is AP-bound with a nonzero intel requirement, and delivered intel is below that requirement, return false. Vanilla conditional 78 still applies (logical AND). Unbound careers are untouched. Intel count and requirement live in the save's owned integer block so the gate holds while the client is disconnected.

Open runtime questions: whether native landing re-checks the event after the button is shown, whether the UI caches the result while the map is open, and what message the player sees. A plot bool alone is not a gate; this event is the consumer.
