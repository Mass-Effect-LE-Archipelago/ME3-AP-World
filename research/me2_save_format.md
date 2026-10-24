# ME2 LE save format and import test

2026-10-24. Owner-supplied copies in `ME2 Saves/Vector_22_Sentinel_150123_368d7d4/` (8 saves, version 30). Originals are never modified.

- Checksum: trailing u32 LE = CRC-32/BZIP2 (poly 0x04C11DB7, init/xorout 0xFFFFFFFF, not reflected) of every preceding byte. Verified on all 8 saves (`tools/me2save/checksum.py`).
- Layout: field order from Trilogy Save Editor (KarlitosVII, CeCILL) read as a reference; own parser `tools/me2save/layout.py` walks all 8 saves exactly to the checksum. ME2 plot table: 238 bool words, 856 ints; inherited ME1 table: 244 words, 150 ints.
- Import-capable template: `Save_0050.pcsav` (end game state 2, lived), SHA256 `ca4b273b…9027`. All 12 squad members loyal/alive, Tali romanced, Collector Base destroyed, ME1 Ashley rescued and romanced.
- Index mapping (inferred, to be confirmed by import): ME2 plots keep their index in ME3 (Collector Base 1831/1832); ME1 plots appear in ME3 at +10000 (Virmire 3827/3828 -> 13827/13828, in-party 3939/3940 -> 13939/13940).

## Import test 01

Edits `research/me2_import_test_01_edits.json`: Collector Base destroyed -> saved; Virmire Ashley -> Kaidan in both the ME1 table and ME2's own copy (1540/1541). Output SHA256 `b0fd2108c65f04ab9829cc74eaf47da15770ff9a7c75920ac7db7007b9009459`, placed as a new career folder `Save/ME2/Vector_22_Sentinel_241026_a9e0001/Save_0001.pcsav` (no existing file touched). Expected after ME3 import: 13827=0, 13828=1, 13939=1, 13940=0, 1831=0, 1832=1.

### Result (2026-10-24, live)

Owner imported the edited career; ME3 accepted it and reached `Biop_ProEar` with no Genesis comic. Live readback: 13827=0, 13828=1, 13939=1, 13940=0, 1831=0, 1832=1, exactly as expected, confirming the ME2 same-index and ME1 +10000 mappings. History readers (`research/me2_import_test_01_history.json`): Kaidan, Collector Base preserved, ME1 Ashley romance, Tali, 12 squad, no warnings. Trace (`research/career_trace_02_import.json`): FinalCommit origin 2 (ME2 import), SetPlotChoices skipped as the source predicts.
