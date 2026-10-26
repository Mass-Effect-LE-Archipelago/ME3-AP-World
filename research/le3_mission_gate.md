# Cerberus HQ / Earth entry gate: source evidence

Reviewed 2026-10-20 from the supplied vanilla `BioD_Nor_203aGalaxyMap.pcc` and `SFXGame.pcc` with `Le3Probe --objects` / `--script`. Static evidence only; no runtime test yet.

## Galaxy map entry

Mission planets are `BioPlanet` objects under `biog_galaxymap.GalaxyMap.SFXCluster_N.SFXSystem_N`. Each landable mission names its level in `MapName` and its landing conditional in `PlanetLandCondition`.

| Export | Path | MapName | PlanetLandCondition | CritPathPlot |
|---|---|---|---|---|
| 196 | `SFXCluster_11.SFXSystem_0.BioPlanet_1` | `BioP_Cat004` (Cronos Station / Cerberus HQ) | 64 | true |
| 319 | `SFXCluster_2.SFXSystem_0.BioPlanet_2` | `BioP_End001` (Earth) | 78 | true |
| 320 | `SFXCluster_2.SFXSystem_0.BioPlanet_3` | none (Mars; not landable in vanilla) | none | |

Correction 2026-10-26: names resolved from `BIOGame_INT.tlk` show `BioP_End001` is **Earth**, and Cronos Station is `BioP_Cat004`. The original gate matched only Earth; it now gates both (bridge source after commit 73c4699, not yet rebuilt). Earth is reached from the galaxy map after Cronos Station.

`SFXGame.BioPlanet.CanBeInteractedWith` (export 13300) is a script **event** that returns `BioWorldInfo.CheckConditional(PlanetLandCondition)`. A decompile of every SFXGame function under GalaxyMap/BioPlanet/SFXSystem/SFXCluster found no script caller, so the native galaxy map calls it as an event through `UObject::ProcessEvent`, which the bridge already hooks. `CheckConditional` (export 18047) is native.

## Gate (implemented in bridge 0.2.1-delivery-dev, not runtime-tested)

After the original `CanBeInteractedWith` returns, if the planet's `MapName` is `BioP_Cat004` or `BioP_End001`, the loaded save is AP-bound with a nonzero intel requirement, and delivered intel is below that requirement, return false. Vanilla conditional 78 still applies (logical AND). Unbound careers are untouched. Intel count and requirement live in the save's owned integer block so the gate holds while the client is disconnected.

Open runtime questions: whether native landing re-checks the event after the button is shown, whether the UI caches the result while the map is open, and what message the player sees. A plot bool alone is not a gate; this event is the consumer.
