# Rannoch peace option (research 2026-10-28, read-only)

Conversation `gth002_bigchoice_m_dlg` in BioD_Gth002_400Resolution_LOC_INT.pcc.

- The peace lines are replies 62 and 81 ("No. Nobody else dies today. Legion, ...") with conditional 121, and their
  Renegade twins 60/79 with conditional 127. Both conditionals are the reputation check
  `((ints[10380] + ints[10159] + ints[10160]) * (1 + floats[10065])) > ints[10643]`.
- Entries 13-17 add peace points through transition 217 (param 1 or 2) when: bool 757 (ME2 heretics destroyed),
  C483 (ints[10174] != 0), C216 (Tali alive and ME2 Legion/Tali outcomes), bool 18184 (saved Admiral Koris), bool 1585
  (ME2 kept the peace). Entries 64 and 82 then check C156 with param 5 (`ints[10212] >= 5`, the peace score).
- Patch (like the ME1 Paragon patch): point replies 60/62/79/81 and entries 64/82 at vanilla conditional 13
  (`Bool true`) in an override of that package, so peace is always offered and always works. Needs a live check that
  the outcome sets both fleets' war assets and keeps Tali and Legion's endings.
