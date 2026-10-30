// le3mod: builds the LE3 game-side mod (DLC_MOD_ArchipelagoME3) from the player's own game files, modeled on the ME2
// project's le2mod (copied pattern; the ME2 checkout is not modified). Writes only under a staging folder.
//   le3mod trace <LE3 BioGame dir> <package file> <remote event>   prints the Kismet reachable from a remote event
using System.IO;
using LegendaryExplorerCore;
using LegendaryExplorerCore.Compression;
using LegendaryExplorerCore.GameFilesystem;
using LegendaryExplorerCore.Kismet;
using LegendaryExplorerCore.Packages;
using LegendaryExplorerCore.Packages.CloningImportingAndRelinking;
using LegendaryExplorerCore.TLK;
using LegendaryExplorerCore.TLK.ME2ME3;
using LegendaryExplorerCore.Unreal;

static class Program
{
    const string ModFolder = "DLC_MOD_ArchipelagoME3";
    const string ModName = "ArchipelagoME3";
    const int NameStrRef = 43000000;
    const int MountPriority = 4300;   // above every installed LE3 DLC (checked at build time)
    const int ModuleNumber = 4300;    // Engine.DLCModules id; vanilla LE3 uses 9..60
    const string Seq = "TheWorld.PersistentLevel.Main_Sequence";
    const string ImportCheck = Seq + ".SeqCond_CompareBool_1";      // ME2_Import (21554)
    const string ProEarArea = Seq + ".BioSeqAct_AreaTransition_1";   // Biop_ProEar
    const int ImportBool = 21554;
    const int RescuedAshBool = 13827;
    // Earth's lasting squad outcome (research/le3_proear_transitions.tsv and the 2026-10-26 save diff):
    // the Virmire survivor joins (32 Ashley / 31 Kaidan: In_Party + Is_Selectable) and James (64 Marine).
    const int AshleyJoins = 32, KaidanJoins = 31, JamesJoins = 64;
    // 49 = Is_Selectable.Liara false. Vanilla meets Liara on Mars; with her selectable before it, picking her for Mars
    // hung the level load (2026-10-27). Mars itself makes her selectable when she joins.
    const int LiaraNotSelectable = 49;

    // Inline bulk data (Wwise banks, package-stored texture mips) stores its own absolute file offset in the export
    // binary as [.. sizeOnDisk][offsetInFile][data], with offsetInFile = the position right after that field. This LEC
    // build re-saves those bytes unchanged even when the export moves, so the game read audio from the wrong place
    // (Normandy "boom" and silence, 2026-10-27). After saving, rewrite every such self-offset from the vanilla source
    // to the export's new position, save again (sizes are unchanged, so nothing moves) and verify.
    // One save path everywhere (compressed, like vanilla), so the bulk-offset fix-up sees a stable layout.
    static void SavePackage(IMEPackage pcc, string path)
    {
        using var saved = pcc.SaveToStream(true, true, true);
        File.WriteAllBytes(path, saved.ToArray());
    }

    static int FixInlineBulkOffsets(string source, string saved)
    {
        // path -> (vanilla data offset, positions of self-offsets). Only spots LEC left stale (still the vanilla value
        // after the export moved) are rewritten; LEC already updates texture mip offsets itself.
        Dictionary<string, (int origin, List<int> hits)> spots;
        using (var vanilla = MEPackageHandler.OpenMEPackage(source, forceLoadFromDisk: true))
        {
            spots = new();
            // Only classes that carry inline bulk data (audio, texture mips, mesh buffers): a scan of every class also
            // matched coincidental ints (a MaterialInstanceConstant, a BioPlanet). The 0.0.8 offline check found stale
            // offsets in Texture2D, TextureFlipBook, StaticMesh and SkeletalMesh too, not only WwiseBank.
            foreach (var e in vanilla.Exports.Where(x => x.ClassName.StartsWith("Wwise") || x.ClassName.Contains("Texture")
                                                         || x.ClassName is "StaticMesh" or "SkeletalMesh"))
            {
                var data = e.Data;
                var hits = new List<int>();
                for (int i = 0; i + 4 <= data.Length; i += 1)
                    if (BitConverter.ToInt32(data, i) == e.DataOffset + i + 4) hits.Add(i);
                if (hits.Count > 0) spots[(e.ClassName + "|" + e.InstancedFullPath)] = (e.DataOffset, hits);
            }
        }
        int patched = 0;
        Dictionary<string, int> positions = new();
        using (var pcc = MEPackageHandler.OpenMEPackage(saved, forceLoadFromDisk: true))
        {
            foreach (var e in pcc.Exports)
            {
                if (!spots.TryGetValue((e.ClassName + "|" + e.InstancedFullPath), out var spot)) continue;
                var data = e.Data;
                var stale = spot.hits.Where(i => i + 4 <= data.Length && BitConverter.ToInt32(data, i) == spot.origin + i + 4
                                                 && e.DataOffset != spot.origin).ToList();
                if (stale.Count == 0) continue;
                foreach (var i in stale) BitConverter.GetBytes(e.DataOffset + i + 4).CopyTo(data, i);
                patched += stale.Count;
                e.Data = data;
                positions[(e.ClassName + "|" + e.InstancedFullPath)] = e.DataOffset;
                spot.hits.RemoveAll(i => !stale.Contains(i));
            }
            SavePackage(pcc, saved);
        }
        using (var pcc = MEPackageHandler.OpenMEPackage(saved, forceLoadFromDisk: true))
        {
            foreach (var e in pcc.Exports)
            {
                if (!positions.ContainsKey((e.ClassName + "|" + e.InstancedFullPath))) continue;
                var data = e.Data;
                if (e.DataOffset != positions[(e.ClassName + "|" + e.InstancedFullPath)] || spots[(e.ClassName + "|" + e.InstancedFullPath)].hits.Any(i => BitConverter.ToInt32(data, i) != e.DataOffset + i + 4))
                    return Fail($"inline bulk offset still wrong in {(e.ClassName + "|" + e.InstancedFullPath)} ({e.ClassName}): offset {positions[(e.ClassName + "|" + e.InstancedFullPath)]} -> {e.DataOffset}, values [{string.Join(",", spots[(e.ClassName + "|" + e.InstancedFullPath)].hits.Select(i => BitConverter.ToInt32(data, i) - (e.DataOffset + i + 4)))}] (0 = correct)");
            }
        }
        Console.WriteLine($"validate: {Path.GetFileName(saved)} stale inline bulk offsets rewritten: {patched} in {positions.Count} exports");
        return 0;
        static int Fail(string message) { Console.Error.WriteLine("validation FAILED: " + message); return 1; }
    }

    // Imported careers (D3: every AP career) skip Earth: ME2_Import True -> survivor check -> squad transitions ->
    // a new AreaTransition to BioP_Nor. Non-import and NG+ routes keep Biop_ProEar. Fails closed on any unexpected shape.
    // This LEC build gives new sequence objects their class-default outputs, so link into an existing output by name
    // and only add an output when the class has none of that name.
    static void Link(ExportEntry from, string output, ExportEntry to)
    {
        if (KismetHelper.GetOutputLinkNames(from).Contains(output)) KismetHelper.CreateOutputLink(from, output, to);
        else KismetHelper.CreateNewOutputLink(from, output, to);
    }

    // Plot bool set on the open start (just before the Normandy transition): an Archipelago career.
    const int ApCareerBool = 26085;

    static int OpenStart(string bioGame, string cooked)
    {
        var source = Winner(bioGame, "BioP_Char.pcc");
        var outPcc = Path.Combine(cooked, "BioP_Char.pcc");
        using (var pcc = MEPackageHandler.OpenMEPackage(source, forceLoadFromDisk: true))
        {
            var seq = pcc.FindExport(Seq);
            var check = pcc.FindExport(ImportCheck);
            var proEar = pcc.FindExport(ProEarArea);
            var names = check == null ? null : KismetHelper.GetOutputLinkNames(check);
            var links = check == null ? null : KismetHelper.GetOutputLinksOfNode(check);
            int trueIdx = names?.IndexOf("True") ?? -1;
            bool importVar = check != null && KismetHelper.GetVariableLinksOfNode(check).SelectMany(v => v.LinkedNodes).OfType<ExportEntry>()
                .Any(v => v.ClassName == "BioSeqVar_StoryManagerBool" && v.GetProperty<IntProperty>("m_nIndex")?.Value == ImportBool);
            if (pcc.Game != MEGame.LE3 || seq == null || proEar == null || trueIdx < 0 || !importVar
                || links[trueIdx].Count != 1 || links[trueIdx][0].LinkedOp != proEar
                || proEar.GetProperty<NameProperty>("AreaName")?.Value.Instanced != "Biop_ProEar")
            {
                Console.Error.WriteLine("refusing: BioP_Char does not have the expected vanilla import route");
                return 1;
            }
            ExportEntry Create(string cls)
            {
                var node = SequenceObjectCreator.CreateSequenceObject(pcc, cls, null, null);
                KismetHelper.AddObjectToSequence(node, seq, true);
                return node;
            }
            ExportEntry Transition(int id)
            {
                var node = Create("BioSeqAct_PMExecuteTransition");
                node.WriteProperty(new IntProperty(id, "m_nIndex"));
                return node;
            }
            var survivor = Create("BioSeqAct_PMCheckState");
            survivor.WriteProperty(new IntProperty(RescuedAshBool, "m_nIndex"));
            var ashley = Transition(AshleyJoins);
            var kaidan = Transition(KaidanJoins);
            var james = Transition(JamesJoins);
            var liara = Transition(LiaraNotSelectable);
            // Marks the career as an Archipelago open start; the client only links careers that have it.
            var marker = Create("SeqAct_SetBool");
            var markerVar = Create("BioSeqVar_StoryManagerBool");
            markerVar.WriteProperty(new IntProperty(ApCareerBool, "m_nIndex"));
            var trueVar = Create("SeqVar_Bool");
            trueVar.WriteProperty(new IntProperty(1, "bValue"));
            KismetHelper.CreateVariableLink(marker, "Target", markerVar);
            KismetHelper.CreateVariableLink(marker, "Value", trueVar);
            var normandy = Create("BioSeqAct_AreaTransition");
            normandy.WriteProperty(new NameProperty("BioP_Nor", "AreaName"));
            links[trueIdx].Clear();
            KismetHelper.WriteOutputLinksToNode(check, links);
            KismetHelper.CreateOutputLink(check, "True", survivor);
            Link(survivor, "True", ashley);
            Link(survivor, "False", kaidan);
            Link(ashley, "Out", james);
            Link(kaidan, "Out", james);
            Link(james, "Out", liara);
            Link(liara, "Out", marker);
            Link(marker, "Out", normandy);
            SavePackage(pcc, outPcc);
        }
        if (FixInlineBulkOffsets(source, outPcc) != 0) return 1;
        using (var pcc = MEPackageHandler.OpenMEPackage(outPcc, forceLoadFromDisk: true))
        {
            var check = pcc.FindExport(ImportCheck);
            var links = KismetHelper.GetOutputLinksOfNode(check);
            var survivor = links[KismetHelper.GetOutputLinkNames(check).IndexOf("True")].Single().LinkedOp as ExportEntry;
            var sNames = KismetHelper.GetOutputLinkNames(survivor);
            var sLinks = KismetHelper.GetOutputLinksOfNode(survivor);
            ExportEntry Follow(ExportEntry n) => KismetHelper.GetOutputLinksOfNode(n)[0].Single().LinkedOp as ExportEntry;
            int Id(ExportEntry n) => n?.GetProperty<IntProperty>("m_nIndex")?.Value ?? -1;
            var a = sLinks[sNames.IndexOf("True")].Single().LinkedOp as ExportEntry;
            var k = sLinks[sNames.IndexOf("False")].Single().LinkedOp as ExportEntry;
            var ja = Follow(a); var jk = Follow(k); var li = Follow(ja); var mark = Follow(li); var area = Follow(mark);
            var markTarget = KismetHelper.GetVariableLinksOfNode(mark).Where(v => v.LinkDesc == "Target").SelectMany(v => v.LinkedNodes).OfType<ExportEntry>().SingleOrDefault();
            var markValue = KismetHelper.GetVariableLinksOfNode(mark).Where(v => v.LinkDesc == "Value").SelectMany(v => v.LinkedNodes).OfType<ExportEntry>().SingleOrDefault();
            bool ok = survivor.ClassName == "BioSeqAct_PMCheckState" && Id(survivor) == RescuedAshBool
                && Id(a) == AshleyJoins && Id(k) == KaidanJoins && ja == jk && Id(ja) == JamesJoins && Id(li) == LiaraNotSelectable
                && mark.ClassName == "SeqAct_SetBool" && markTarget?.ClassName == "BioSeqVar_StoryManagerBool" && Id(markTarget) == ApCareerBool
                && markValue?.GetProperty<IntProperty>("bValue")?.Value == 1
                && area?.ClassName == "BioSeqAct_AreaTransition" && area.GetProperty<NameProperty>("AreaName")?.Value.Instanced == "BioP_Nor"
                && pcc.FindExport(ProEarArea).GetProperty<NameProperty>("AreaName")?.Value.Instanced == "Biop_ProEar";
            Console.WriteLine($"validate: ME2_Import True -> S{Id(survivor)} ? T{Id(a)} : T{Id(k)} -> T{Id(ja)} -> T{Id(li)} -> set B{Id(markTarget)} -> {area?.GetProperty<NameProperty>("AreaName")?.Value.Instanced}");
            if (!ok) { Console.Error.WriteLine("validation FAILED; staging left unchanged"); return 1; }
        }
        Console.WriteLine($"Earth skipped for imported careers (source {source})");
        return 0;
    }

    // Fixed-squad missions. BioP_Nor's re_MapTransition runs Check_Hench_Select (and Check_Hench_Select_0 after
    // streaming), a chain of map-name compares whose matches skip squad selection and the weapon screen (vanilla: the
    // hubs). We put BioP_ProMar at the head of both chains. In the first one, the Mars branch also forces the story
    // squad before leaving: 28 (clear In_Squad) -> Rescued Ash ? 9 (Ashley) : 8 (Kaidan) -> 62 (James). Picking Liara
    // for Mars hung the load (2026-10-27).
    static readonly string[] HenchChecks =
        ["TheWorld.PersistentLevel.Main_Sequence.Area_transition.Check_Hench_Select",
         "TheWorld.PersistentLevel.Main_Sequence.Area_transition.Check_Hench_Select_0"];
    const string FixedSquadMap = "BioP_ProMar";
    const int ClearSquad = 28, AshleyInSquad = 9, KaidanInSquad = 8, JamesInSquad = 62;

    static int FixedSquad(string bioGame, string cooked)
    {
        var source = Winner(bioGame, "BioP_Nor.pcc");
        var outPcc = Path.Combine(cooked, "BioP_Nor.pcc");
        using (var pcc = MEPackageHandler.OpenMEPackage(source, forceLoadFromDisk: true))
        {
            for (int c = 0; c < HenchChecks.Length; c++)
            {
                var seq = pcc.FindExport(HenchChecks[c]);
                var start = seq == null ? null : pcc.Exports.SingleOrDefault(e => e.Parent == seq && e.ClassName == "SeqEvent_SequenceActivated");
                var first = start == null ? null : KismetHelper.GetOutputLinksOfNode(start)[0].SingleOrDefault()?.LinkedOp as ExportEntry;
                if (first?.ClassName != "SeqCond_CompareName")
                {
                    Console.Error.WriteLine($"refusing: {HenchChecks[c]} does not start with a map-name compare");
                    return 1;
                }
                var names = KismetHelper.GetOutputLinkNames(first);
                var skip = KismetHelper.GetOutputLinksOfNode(first)[names.IndexOf("A == B")].Single().LinkedOp as ExportEntry;
                var bLink = KismetHelper.GetVariableLinksOfNode(first).Single(v => v.LinkDesc == "B");
                var ours = EntryCloner.CloneEntry(first);
                var name = EntryCloner.CloneEntry((ExportEntry)bLink.LinkedNodes.Single());
                name.WriteProperty(new NameProperty(FixedSquadMap, "NameValue"));
                // Clones are not in the sequence's SequenceObjects list; unlisted ops are ignored at runtime (0.0.6
                // still showed squad selection on Mars). Register both.
                KismetHelper.AddObjectToSequence(ours, seq, false);  // false: keep the cloned variable links
                KismetHelper.AddObjectToSequence(name, seq, false);
                var vars = KismetHelper.GetVariableLinksOfNode(ours);
                vars.Single(v => v.LinkDesc == "B").LinkedNodes = [name];
                KismetHelper.WriteVariableLinksToNode(ours, vars);
                // The clone carries the original's outputs; rewrite them: match -> (squad) -> skip, else -> original chain.
                var outs = KismetHelper.GetOutputLinksOfNode(ours);
                foreach (var l in outs) l.Clear();
                KismetHelper.WriteOutputLinksToNode(ours, outs);
                Link(ours, "A != B", first);
                if (c == 0)
                {
                    ExportEntry T(int id)
                    {
                        var n = SequenceObjectCreator.CreateSequenceObject(pcc, "BioSeqAct_PMExecuteTransition", null, null);
                        KismetHelper.AddObjectToSequence(n, seq, true);
                        n.WriteProperty(new IntProperty(id, "m_nIndex"));
                        return n;
                    }
                    var clear = T(ClearSquad);
                    var survivor = SequenceObjectCreator.CreateSequenceObject(pcc, "BioSeqAct_PMCheckState", null, null);
                    KismetHelper.AddObjectToSequence(survivor, seq, true);
                    survivor.WriteProperty(new IntProperty(RescuedAshBool, "m_nIndex"));
                    var ash = T(AshleyInSquad); var kai = T(KaidanInSquad); var james = T(JamesInSquad);
                    Link(ours, "A == B", clear);
                    Link(clear, "Out", survivor);
                    Link(survivor, "True", ash);
                    Link(survivor, "False", kai);
                    Link(ash, "Out", james);
                    Link(kai, "Out", james);
                    Link(james, "Out", skip);
                }
                else Link(ours, "A == B", skip);
                var startLinks = KismetHelper.GetOutputLinksOfNode(start);
                startLinks[0].Clear();
                KismetHelper.WriteOutputLinksToNode(start, startLinks);
                Link(start, "Out", ours);
            }
            SavePackage(pcc, outPcc);
        }
        if (FixInlineBulkOffsets(source, outPcc) != 0) return 1;
        using (var pcc = MEPackageHandler.OpenMEPackage(outPcc, forceLoadFromDisk: true))
        {
            foreach (var path in HenchChecks)
            {
                var seq = pcc.FindExport(path);
                var start = pcc.Exports.Single(e => e.Parent == seq && e.ClassName == "SeqEvent_SequenceActivated");
                var ours = KismetHelper.GetOutputLinksOfNode(start)[0].Single().LinkedOp as ExportEntry;
                var b = KismetHelper.GetVariableLinksOfNode(ours).Single(v => v.LinkDesc == "B").LinkedNodes.Single() as ExportEntry;
                var a = KismetHelper.GetVariableLinksOfNode(ours).Single(v => v.LinkDesc == "A").LinkedNodes.Single() as ExportEntry;
                var names = KismetHelper.GetOutputLinkNames(ours);
                var links = KismetHelper.GetOutputLinksOfNode(ours);
                var match = links[names.IndexOf("A == B")].Single().LinkedOp as ExportEntry;
                var other = links[names.IndexOf("A != B")].Single().LinkedOp as ExportEntry;
                var listed = seq.GetProperty<ArrayProperty<ObjectProperty>>("SequenceObjects").Select(o => o.Value).ToHashSet();
                bool ok = listed.Contains(ours.UIndex) && listed.Contains(b.UIndex) && listed.Contains(match.UIndex)
                          && ours.ClassName == "SeqCond_CompareName" && string.Equals(b.GetProperty<NameProperty>("NameValue")?.Value.Instanced, FixedSquadMap, StringComparison.OrdinalIgnoreCase)  // names are case-insensitive; the package already has "Biop_ProMar"
                          && a.ClassName == "SeqVar_External" && other.ClassName == "SeqCond_CompareName"
                          && (path == HenchChecks[0] ? match.GetProperty<IntProperty>("m_nIndex")?.Value == ClearSquad : match.ClassName is "SeqAct_FinishSequence" or "BioSeqAct_PMExecuteTransition");
                Console.WriteLine($"validate: {path.Split('.').Last()} first compare = {b.GetProperty<NameProperty>("NameValue")?.Value.Instanced}; match -> {match.ObjectName.Instanced} {match.GetProperty<IntProperty>("m_nIndex")?.Value}; else -> {other.ObjectName.Instanced}");
                if (!ok) { Console.Error.WriteLine("validation FAILED; staging left unchanged"); return 1; }
            }
        }
        Console.WriteLine($"Mars uses its story squad without squad selection (source {source})");
        return 0;
    }

    // Mars on the galaxy map. Vanilla Sol BioPlanet_3 (Mars) has no MapName, so it cannot be landed on. Ours gets
    // BioP_ProMar and a landing conditional from this DLC's own CND file (LE3 loads Conditionals<DLC folder>.cnd by
    // name, as the vanilla DLCs do; only DLC_Shared needs a config line). Vanilla conditional ids end at 4232.
    // Test build: Mars is landable until its mission completes (20552 ProMar.MissionComplete). The AP unlock item
    // will be ANDed in once a safe plot bool range is audited.
    const string GalaxyFile = "BioD_Nor_203aGalaxyMap.pcc";
    const string MarsPath = "biog_galaxymap.GalaxyMap.SFXCluster_2.SFXSystem_0.BioPlanet_3";
    const int MarsConditional = 43001;
    const string MarsExpression = "(plot.bools[20552] == Bool false)";
    // Vanilla shows and opens the Local Cluster only after Cronos Station (C2752 visible / C80 usable, both
    // ints[10185] != 0: Mission_Completion_Order.Cat004). Ours keeps that and also opens it while Mars is unfinished.
    // Earth stays gated by its own land conditional 78 and the bridge.
    const string LocalClusterPath = "biog_galaxymap.GalaxyMap.SFXCluster_2";
    const int LocalClusterConditional = 43002;
    const string LocalClusterExpression = "((plot.ints[10185] != i0) || (plot.bools[20552] == Bool false))";

    // Diagnostic: point Mars/Local Cluster at vanilla conditionals that are true on the Normandy (Serpent Nebula's
    // 2744 visible / 79 usable) to tell "our CND is not loaded" apart from "our galaxy map package is not loaded".
    static bool DiagVanilla;

    // The galaxy map objects (biog_galaxymap.GalaxyMap...) exist in two packages. BioD_Nor_203CIC loads first and its
    // copy is the one the game uses; patching only 203aGalaxyMap had no effect in game (2026-10-27 diagnostic).
    static readonly string[] GalaxyPackages = ["BioD_Nor_203CIC.pcc", GalaxyFile];
    static bool NoMars;

    // Mars debug loadout (D5: the career starts with only the Predator). When Mars loads as an early mission its
    // SetupDebugLoad sequence clears the inventory and gives Predator, Avenger, shield and the Legion heavy weapon.
    // Ours keeps the clear, the Predator and the shield (an open-start Shepard has no other source of one).
    const string MarsPersistent = "BioP_ProMar.pcc";
    const string DebugInventoryPath = "TheWorld.PersistentLevel.Main_Sequence.SetupDebugLoad.SeqAct_GiveInventory_0";
    static readonly string[] MarsLoadout = ["SFXGameContent.SFXWeapon_Pistol_Predator", "SFXGameContent.SFXShield_Energy_Player"];

    static int MarsWeapons(string bioGame, string cooked)
    {
        var source = Winner(bioGame, MarsPersistent);
        var outPcc = Path.Combine(cooked, MarsPersistent);
        using (var pcc = MEPackageHandler.OpenMEPackage(source, forceLoadFromDisk: true))
        {
            var give = pcc.FindExport(DebugInventoryPath);
            var list = give?.GetProperty<ArrayProperty<ObjectProperty>>("InventoryList");
            var names = list?.Select(o => pcc.GetEntry(o.Value)?.InstancedFullPath).ToList() ?? [];
            if (give?.ClassName != "SeqAct_GiveInventory" || names.Count != 4 || !MarsLoadout.All(names.Contains))
            { Console.Error.WriteLine("refusing: Mars debug inventory is not the vanilla four items in " + source); return 1; }
            give.WriteProperty(new ArrayProperty<ObjectProperty>(list.Where(o => MarsLoadout.Contains(pcc.GetEntry(o.Value)?.InstancedFullPath)), "InventoryList"));
            SavePackage(pcc, outPcc);
        }
        if (FixInlineBulkOffsets(source, outPcc) != 0) return 1;
        using (var pcc = MEPackageHandler.OpenMEPackage(outPcc, forceLoadFromDisk: true))
        {
            var names = pcc.FindExport(DebugInventoryPath)?.GetProperty<ArrayProperty<ObjectProperty>>("InventoryList")?
                .Select(o => pcc.GetEntry(o.Value)?.InstancedFullPath).ToList() ?? [];
            Console.WriteLine($"validate: Mars debug loadout = {string.Join(", ", names)}");
            if (names.Count != 2 || !MarsLoadout.All(names.Contains)) { Console.Error.WriteLine("validation FAILED: Mars loadout"); return 1; }
        }
        return 0;
    }

    // Rannoch peace (research/le3_rannoch_peace.md): the "Nobody else dies today" lines (replies 62/81, Paragon C121) and
    // their Renegade twins (60/79, C127) need a reputation check, and the success entries 64/82 need a peace score of 5
    // (C156 param 5). All six point at vanilla conditional 13 (Bool true), so peace is always offered and always works.
    const string PeaceFile = "BioD_Gth002_400Resolution_LOC_INT.pcc";
    const string PeaceConversation = "gth002_bigchoice_m_dlg";
    static readonly (string List, int Index, int Vanilla)[] PeaceNodes =
        [("m_ReplyList", 60, 127), ("m_ReplyList", 62, 121), ("m_ReplyList", 79, 127), ("m_ReplyList", 81, 121),
         ("m_EntryList", 64, 156), ("m_EntryList", 82, 156)];
    const int AlwaysTrueConditional = 13;

    static int RannochPeace(string bioGame, string cooked)
    {
        var source = Winner(bioGame, PeaceFile);
        var outPcc = Path.Combine(cooked, PeaceFile);
        using (var pcc = MEPackageHandler.OpenMEPackage(source, forceLoadFromDisk: true))
        {
            var convo = pcc.Exports.SingleOrDefault(e => e.ClassName == "BioConversation" && e.ObjectName.Instanced == PeaceConversation);
            if (convo == null) { Console.Error.WriteLine("refusing: no " + PeaceConversation + " in " + source); return 1; }
            var lists = new Dictionary<string, ArrayProperty<StructProperty>>
                { ["m_ReplyList"] = convo.GetProperty<ArrayProperty<StructProperty>>("m_ReplyList"), ["m_EntryList"] = convo.GetProperty<ArrayProperty<StructProperty>>("m_EntryList") };
            foreach (var (list, index, vanilla) in PeaceNodes)
            {
                var node = lists[list][index];
                if (node.GetProp<IntProperty>("nConditionalFunc")?.Value != vanilla || node.GetProp<BoolProperty>("bFireConditional")?.Value != true)
                { Console.Error.WriteLine($"refusing: {list}[{index}] is not vanilla C{vanilla}"); return 1; }
                node.GetProp<IntProperty>("nConditionalFunc").Value = AlwaysTrueConditional;
            }
            foreach (var (name, list) in lists) convo.WriteProperty(list);
            SavePackage(pcc, outPcc);
        }
        if (FixInlineBulkOffsets(source, outPcc) != 0) return 1;
        using (var pcc = MEPackageHandler.OpenMEPackage(outPcc, forceLoadFromDisk: true))
        {
            var convo = pcc.Exports.Single(e => e.ClassName == "BioConversation" && e.ObjectName.Instanced == PeaceConversation);
            var got = PeaceNodes.Select(n => convo.GetProperty<ArrayProperty<StructProperty>>(n.List)[n.Index].GetProp<IntProperty>("nConditionalFunc")?.Value).ToList();
            Console.WriteLine($"validate: Rannoch peace nodes -> C{string.Join(",C", got)}");
            if (got.Any(c => c != AlwaysTrueConditional)) { Console.Error.WriteLine("validation FAILED: Rannoch peace"); return 1; }
        }
        return 0;
    }

    // Mission access items (D9). Each keyed planet (mission_keys.json, exported from the world's data.MISSION_KEYS) lands
    // on "key bool && mission not done && Cronos not done (&& extra)" instead of its story condition. "vanilla" entries
    // (Omega and the story arcs) keep their vanilla landing condition and AND the key. The planet's system and cluster must also show and open while
    // the key is held, so their own conditionals become "(vanilla) || any key in them".
    const int MissionKeyBool = 26100, MissionKeyConditional = 43300, MapAccessConditional = 43400;

    static Dictionary<int, string> VanillaConditionals(string bioGame)
    {
        var all = new Dictionary<int, string>();
        foreach (var file in new[] { Path.Combine(bioGame, "CookedPCConsole", "Conditionals.cnd") }
                     .Concat(Directory.EnumerateFiles(Path.Combine(bioGame, "DLC"), "Conditionals*.cnd", SearchOption.AllDirectories)
                         .Where(f => !f.Contains("DLC_MOD_", StringComparison.OrdinalIgnoreCase))))
            foreach (var entry in CNDFile.FromFile(file).ConditionalEntries)
                all.TryAdd(entry.ID, ME3ConditionalsCompiler.Decompile(entry));
        return all;
    }
    static Dictionary<int, string> _vanilla;

    static int MissionKeys(string bioGame, IMEPackage pcc)
    {
        var keys = System.Text.Json.JsonDocument.Parse(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "mission_keys.json"))).RootElement;
        _vanilla ??= VanillaConditionals(bioGame);
        var planets = pcc.Exports.Where(e => e.ClassName == "BioPlanet" && !string.IsNullOrEmpty(e.GetProperty<StrProperty>("MapName")?.Value)).ToList();
        var parentKeys = new Dictionary<ExportEntry, List<int>>();
        for (int k = 0; k < keys.GetArrayLength(); k++)
        {
            var key = keys[k];
            var map = key.GetProperty("map").GetString();
            var planet = planets.SingleOrDefault(p => p.GetProperty<StrProperty>("MapName").Value.Equals(map, StringComparison.OrdinalIgnoreCase));
            if (planet == null) { Console.Error.WriteLine($"refusing: no galaxy-map planet for {map}"); return 1; }
            var keyTerm = $"(plot.bools[{MissionKeyBool + k}] == Bool true)";
            var extra = key.GetProperty("extra").GetString();
            var vanillaLand = planet.GetProperty<IntProperty>("PlanetLandCondition")?.Value ?? 0;
            var expression = extra == "vanilla" ? $"({_vanilla[vanillaLand]} && {keyTerm})"
                : $"({keyTerm} && (plot.ints[{key.GetProperty("done_int").GetInt32()}] == i0) && (plot.ints[10185] == i0){(extra.Length > 0 ? " && " + extra : "")})";
            Conditionals[MissionKeyConditional + k] = expression;
            planet.WriteProperty(new IntProperty(MissionKeyConditional + k, "PlanetLandCondition"));
            // The mission label ("Priority: ..." / quest marker) shows exactly while the planet can be landed on.
            if (planet.GetProperty<IntProperty>("PlanetPlotLabelCondition") != null)
                planet.WriteProperty(new IntProperty(MissionKeyConditional + k, "PlanetPlotLabelCondition"));
            for (var parent = planet.Parent as ExportEntry; parent != null && parent.ClassName is "SFXSystem" or "SFXCluster"; parent = parent.Parent as ExportEntry)
                (parentKeys.TryGetValue(parent, out var list) ? list : parentKeys[parent] = []).Add(k);
        }
        int next = MapAccessConditional;
        foreach (var (parent, ks) in parentKeys.OrderBy(kv => kv.Key.UIndex))
            foreach (var name in new[] { "VisibleConditional", "UsableConditional" })
            {
                var current = parent.GetProperty<IntProperty>(name)?.Value;
                if (current is null or 0) continue;  // no condition: always shown/usable
                var anyKey = string.Join(" || ", ks.Select(k => $"(plot.bools[{MissionKeyBool + k}] == Bool true)"));
                var baseExpr = Conditionals.TryGetValue(current.Value, out var ours) ? ours : _vanilla.GetValueOrDefault(current.Value);
                if (baseExpr == null) { Console.Error.WriteLine($"refusing: {parent.InstancedFullPath} {name} C{current} not found"); return 1; }
                var expr = $"({baseExpr} || {anyKey})";
                var id = Conditionals.FirstOrDefault(kv => kv.Key >= MapAccessConditional && kv.Value == expr).Key;
                if (id == 0) { id = next++; Conditionals[id] = expr; }
                parent.WriteProperty(new IntProperty(id, name));
            }
        Console.WriteLine($"validate: {keys.GetArrayLength()} keyed planets; {next - MapAccessConditional} system/cluster conditionals opened by keys");
        return 0;
    }

    // Every conditional and TLK string the DLC adds, written once by Build.
    static readonly Dictionary<int, string> Conditionals = [];
    static readonly Dictionary<int, string> Strings = [];

    // Missed-checks salvage (D7). The Normandy store terminal (BioD_Nor_500 Normandy_Store, class
    // SFXGameChoiceGUIData_StoreData_Normandy, local to that package) lists vanilla stores as nested rows. We append
    // one TYPE_QUEST row per (mission k, price tier t): buying it charges the tier price and sets plot bool
    // SalvageBool + k, which the bridge takes (DEV_SALVAGE) and the client turns into one missed check. Row (k, t) shows
    // only while the client's published tier is t, mission k has open checks and its bought flag is clear (all plot bools).
    // Mission order and names: salvage.json, exported from the world's data.SALVAGE_MISSIONS (a world test keeps it in step).
    const string StoreFile = "BioD_Nor_500.pcc";
    const string StorePath = "SFXGameContent.Default__SFXGameChoiceGUIData_StoreData_Normandy";
    // Plot bools shared with the bridge (Delivery.hpp): bought 26000+k, available 26040+k, price tier 26080+t.
    const int SalvageBool = 26000, SalvageAvailBool = 26040, SalvageTierBool = 26080;
    const int SalvageConditional = 43100, SalvageNameStrRef = 43000100, SalvageDescriptionStrRef = 43000099;
    static readonly int[] SalvagePrices = [0, 500, 1000, 2500, 5000];

    static int Salvage(string bioGame, string cooked)
    {
        var missions = System.Text.Json.JsonSerializer.Deserialize<string[]>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "salvage.json")))!;
        if (missions.Length == 0 || missions.Length > 40) { Console.Error.WriteLine("refusing: salvage.json needs 1..40 missions"); return 1; }
        var source = Winner(bioGame, StoreFile);
        var outPcc = Path.Combine(cooked, StoreFile);
        int vanillaRows;
        using (var pcc = MEPackageHandler.OpenMEPackage(source, forceLoadFromDisk: true))
        {
            var store = pcc.FindExport(StorePath);
            var items = store?.GetProperty<ArrayProperty<StructProperty>>("StoreItemArray");
            if (items == null || items.Count == 0 || items.Any(i => i.GetProp<EnumProperty>("ItemType")?.Value.Instanced != "TYPE_NESTEDCATEGORY"))
            { Console.Error.WriteLine("refusing: Normandy store rows are not the vanilla nested categories in " + source); return 1; }
            vanillaRows = items.Count;
            var template = items[0];
            Strings[SalvageDescriptionStrRef] = "Recover a check you missed on a mission you can't return to. Each purchase sends one of the checks still left there.";
            for (int k = 0; k < missions.Length; k++)
            {
                Strings[SalvageNameStrRef + k] = $"{missions[k]} Salvage";
                for (int t = 0; t < SalvagePrices.Length; t++)
                {
                    var row = (StructProperty)template.DeepClone();
                    row.Properties.AddOrReplaceProp(new StrProperty("", "ItemClassName"));
                    row.Properties.AddOrReplaceProp(new ArrayProperty<IntProperty>([new IntProperty(SalvageBool + k)], "PlotPurchaseID"));
                    row.Properties.AddOrReplaceProp(new IntProperty(SalvagePrices[t], "BaseCost"));
                    row.Properties.AddOrReplaceProp(new IntProperty(SalvageConditional + 5 * k + t, "PlotUnlockConditionalID"));
                    row.GetProp<StrProperty>("SmallImage").Value = "GUI_Icons.Notifications.NT_Store_256x1286";
                    row.GetProp<EnumProperty>("ItemType").Value = new NameReference("TYPE_QUEST");
                    var choice = row.GetProp<StructProperty>("ChoiceEntry");
                    choice.Properties.AddOrReplaceProp(new StringRefProperty(SalvageNameStrRef + k, "srChoiceName"));
                    choice.Properties.AddOrReplaceProp(new StringRefProperty(SalvageDescriptionStrRef, "srChoiceDescription"));
                    items.Add(row);
                    Conditionals[SalvageConditional + 5 * k + t] =
                        $"((plot.bools[{SalvageTierBool + t}] == Bool true) && ((plot.bools[{SalvageAvailBool + k}] == Bool true) && (plot.bools[{SalvageBool + k}] == Bool false)))";
                }
            }
            store.WriteProperty(items);
            SavePackage(pcc, outPcc);
        }
        if (FixInlineBulkOffsets(source, outPcc) != 0) return 1;
        using (var pcc = MEPackageHandler.OpenMEPackage(outPcc, forceLoadFromDisk: true))
        {
            var items = pcc.FindExport(StorePath)?.GetProperty<ArrayProperty<StructProperty>>("StoreItemArray");
            var added = items?.Skip(vanillaRows).ToList() ?? [];
            bool ok = added.Count == missions.Length * SalvagePrices.Length && added.All(r => r.GetProp<EnumProperty>("ItemType")?.Value.Instanced == "TYPE_QUEST")
                && added.Select(r => r.GetProp<IntProperty>("PlotUnlockConditionalID")?.Value).Distinct().Count() == added.Count
                && added[^1].GetProp<ArrayProperty<IntProperty>>("PlotPurchaseID")?.Single().Value == SalvageBool + missions.Length - 1
                && added[^1].GetProp<IntProperty>("BaseCost")?.Value == SalvagePrices[^1];
            Console.WriteLine($"validate: Normandy store {vanillaRows} vanilla + {added.Count} salvage rows; last {Strings[SalvageNameStrRef + missions.Length - 1]} C{added.LastOrDefault()?.GetProp<IntProperty>("PlotUnlockConditionalID")?.Value}");
            if (!ok) { Console.Error.WriteLine("validation FAILED: salvage rows"); return 1; }
        }
        return 0;
    }

    static int Mars(string bioGame, string cooked)
    {
        foreach (var file in GalaxyPackages)
            if (MarsPackage(bioGame, cooked, file) != 0) return 1;
        return 0;
    }

    static int MarsPackage(string bioGame, string cooked, string file)
    {
        var source = Winner(bioGame, file);
        var outPcc = Path.Combine(cooked, file);
        using (var pcc = MEPackageHandler.OpenMEPackage(source, forceLoadFromDisk: true))
        {
            var mars = pcc.FindExport(MarsPath);
            if (pcc.Game != MEGame.LE3 || mars == null || mars.ClassName != "BioPlanet"
                || !string.IsNullOrEmpty(mars.GetProperty<StrProperty>("MapName")?.Value) || mars.GetProperty<IntProperty>("PlanetLandCondition") != null)
            {
                Console.Error.WriteLine("refusing: Mars is missing or already has a mission in " + source);
                return 1;
            }
            // Use the Earth planet's property types as the pattern for a landable mission planet.
            mars.WriteProperty(new StrProperty("BioP_ProMar", "MapName"));
            mars.WriteProperty(new IntProperty(MarsConditional, "PlanetLandCondition"));
            var cluster = pcc.FindExport(LocalClusterPath);
            if (cluster?.GetProperty<IntProperty>("VisibleConditional")?.Value != 2752 || cluster.GetProperty<IntProperty>("UsableConditional")?.Value != 80)
            {
                Console.Error.WriteLine("refusing: Local Cluster conditionals are not the vanilla 2752/80");
                return 1;
            }
            cluster.WriteProperty(new IntProperty(DiagVanilla ? 2744 : LocalClusterConditional, "VisibleConditional"));
            cluster.WriteProperty(new IntProperty(DiagVanilla ? 79 : LocalClusterConditional, "UsableConditional"));
            if (DiagVanilla) mars.WriteProperty(new IntProperty(79, "PlanetLandCondition"));
            if (MissionKeys(bioGame, pcc) != 0) return 1;
            SavePackage(pcc, outPcc);
        }
        if (FixInlineBulkOffsets(source, outPcc) != 0) return 1;
        Conditionals[MarsConditional] = MarsExpression;
        Conditionals[LocalClusterConditional] = LocalClusterExpression;
        using (var pcc = MEPackageHandler.OpenMEPackage(outPcc, forceLoadFromDisk: true))
        {
            var mars = pcc.FindExport(MarsPath);
            var cluster = pcc.FindExport(LocalClusterPath);
            if (DiagVanilla) return 0;
            bool ok = mars?.GetProperty<StrProperty>("MapName")?.Value == "BioP_ProMar"
                && mars.GetProperty<IntProperty>("PlanetLandCondition")?.Value == MarsConditional
                && cluster?.GetProperty<IntProperty>("VisibleConditional")?.Value == LocalClusterConditional
                && cluster.GetProperty<IntProperty>("UsableConditional")?.Value == LocalClusterConditional;
            Console.WriteLine($"validate: Mars MapName={mars?.GetProperty<StrProperty>("MapName")?.Value} land=C{mars?.GetProperty<IntProperty>("PlanetLandCondition")?.Value}; Local Cluster C{cluster?.GetProperty<IntProperty>("VisibleConditional")?.Value}");
            if (!ok) { Console.Error.WriteLine("validation FAILED; staging left unchanged"); return 1; }
        }
        if (DiagVanilla) { Console.WriteLine("DIAGNOSTIC build: vanilla conditionals 2744/79 on Local Cluster and Mars"); return 0; }
        Console.WriteLine($"Mars landable (galaxy source {source})");
        return 0;
    }

    // Cutscene skips (D5): non-interactive matinees play at a very high rate instead of being cut out, so every track,
    // event and end position still applies (doors open, actors land where gameplay expects them).
    // Mars landing (owner 2026-10-27: in-engine, dropship descent + shuttle door): BioD_ProMar_110Shuttle
    // Initialize_And_Enter_ProMar, reached from RE_TELEPORT_TO_LEVELSTART after the level-start teleport.
    const float FastForwardRate = 100f;
    static readonly (string file, string[] interps)[] FastForwards =
    [
        ("BioD_ProMar_110Shuttle.pcc", ["TheWorld.PersistentLevel.Main_Sequence.Initialize_And_Enter_ProMar.SeqAct_Interp_1",
                                        "TheWorld.PersistentLevel.Main_Sequence.Initialize_And_Enter_ProMar.SeqAct_Interp_2"]),
    ];

    static int Cutscenes(string bioGame, string cooked)
    {
        foreach (var (file, interps) in FastForwards)
        {
            var source = Winner(bioGame, file);
            var outPcc = Path.Combine(cooked, file);
            using (var pcc = MEPackageHandler.OpenMEPackage(source, forceLoadFromDisk: true))
            {
                foreach (var path in interps)
                {
                    var interp = pcc.FindExport(path);
                    if (interp?.ClassName != "SeqAct_Interp" || interp.GetProperty<BoolProperty>("bLooping")?.Value == true)
                    {
                        Console.Error.WriteLine($"refusing: {path} is not a one-shot matinee in {source}");
                        return 1;
                    }
                    interp.WriteProperty(new FloatProperty(FastForwardRate, "PlayRate"));
                }
                SavePackage(pcc, outPcc);
            }
            if (FixInlineBulkOffsets(source, outPcc) != 0) return 1;
            using (var pcc = MEPackageHandler.OpenMEPackage(outPcc, forceLoadFromDisk: true))
            {
                foreach (var path in interps)
                {
                    var rate = pcc.FindExport(path)?.GetProperty<FloatProperty>("PlayRate")?.Value;
                    Console.WriteLine($"validate: {file} {path.Split('.').Last()} PlayRate={rate}");
                    if (rate != FastForwardRate) { Console.Error.WriteLine("validation FAILED"); return 1; }
                }
            }
        }
        return 0;
    }

    static int Build(string bioGame, string staging)
    {
        if (staging.StartsWith(bioGame, StringComparison.OrdinalIgnoreCase) || staging.Contains(@"\BioGame", StringComparison.OrdinalIgnoreCase))
        { Console.Error.WriteLine("refusing: staging must be outside any BioGame folder"); return 2; }
        // Must mount above every vanilla DLC and must not tie with another installed mod.
        var mounts = Directory.EnumerateFiles(Path.Combine(bioGame, "DLC"), "Mount.dlc", SearchOption.AllDirectories)
            .Where(m => !m.Contains(ModFolder, StringComparison.OrdinalIgnoreCase))
            .Select(m => (dlc: Path.GetFileName(Path.GetDirectoryName(Path.GetDirectoryName(m))), p: MountFile.GetMountPriority(m))).ToList();
        foreach (var (dlc, p) in mounts.OrderBy(x => x.p)) Console.WriteLine($"mount {p,6}  {dlc}");
        int vanilla = mounts.Where(x => !x.dlc.StartsWith("DLC_MOD_", StringComparison.OrdinalIgnoreCase)).Max(x => x.p);
        if (MountPriority <= vanilla || mounts.Any(x => x.p == MountPriority))
        { Console.Error.WriteLine($"refusing: mount priority {MountPriority} vs vanilla {vanilla} or a tie"); return 1; }
        var modRoot = Path.Combine(staging, ModName);
        var tmp = modRoot + ".tmp";
        if (Directory.Exists(tmp)) Directory.Delete(tmp, true);
        var cooked = Path.Combine(tmp, ModFolder, "CookedPCConsole");
        Directory.CreateDirectory(cooked);
        if (OpenStart(bioGame, cooked) != 0) return 1;
        if (!NoMars && Mars(bioGame, cooked) != 0) return 1;
        if (FixedSquad(bioGame, cooked) != 0) return 1;
        if (Cutscenes(bioGame, cooked) != 0) return 1;
        if (MarsWeapons(bioGame, cooked) != 0) return 1;
        if (Salvage(bioGame, cooked) != 0) return 1;
        if (RannochPeace(bioGame, cooked) != 0) return 1;
        // One CND for the whole DLC (LE3 loads Conditionals<DLC folder>.cnd by name); every entry must round-trip.
        var cnd = new CNDFile { ConditionalEntries = [] };
        foreach (var (id, expression) in Conditionals.OrderBy(kv => kv.Key))
        {
            var entry = new CNDFile.ConditionalEntry { ID = id };
            ME3ConditionalsCompiler.Compile(entry, expression);
            cnd.ConditionalEntries.Add(entry);
        }
        var cndPath = Path.Combine(cooked, $"Conditionals{ModFolder}.cnd");
        cnd.ToFile(cndPath);
        var compiled = CNDFile.FromFile(cndPath).ConditionalEntries;
        foreach (var entry in compiled)
        {
            var again = new CNDFile.ConditionalEntry { ID = entry.ID };
            ME3ConditionalsCompiler.Compile(again, ME3ConditionalsCompiler.Decompile(entry));
            if (!Conditionals.ContainsKey(entry.ID) || !again.Data.SequenceEqual(entry.Data))
            { Console.Error.WriteLine($"validation FAILED: conditional {entry.ID} does not round-trip"); return 1; }
        }
        Console.WriteLine($"validate: {compiled.Count} conditionals round-trip; e.g. " + string.Join("; ", compiled.Where(e => e.ID is MarsConditional or SalvageConditional).Select(e => $"C{e.ID} = {ME3ConditionalsCompiler.Decompile(e)}")));
        if (compiled.Count != Conditionals.Count) { Console.Error.WriteLine("validation FAILED: conditional count"); return 1; }
        // Flags copied from a vanilla single-player DLC (Leviathan) so the mount type matches.
        var template = new MountFile(Path.Combine(bioGame, "DLC", "DLC_EXP_Pack001", "CookedPCConsole", "Mount.dlc"));
        new MountFile { Game = MEGame.LE3, MountPriority = MountPriority, TLKID = NameStrRef, MountFlags = template.MountFlags }
            .WriteMountFile(Path.Combine(cooked, "Mount.dlc"));
        HuffmanCompression.SaveToTlkFile(Path.Combine(cooked, $"{ModFolder}_INT.tlk"),
            [new TLKStringRef(NameStrRef, "Archipelago ME3"), .. Strings.Select(kv => new TLKStringRef(kv.Key, kv.Value))]);
        // LE3 reports a DLC folder without its Default_<DLC>.bin config as corrupt (seen 2026-10-27). Modeled on the
        // smallest vanilla one (DLC_UPD_Patch01): the cooked path plus a DLC module number (vanilla uses 9..60).
        var coalesced = new Dictionary<string, string>
        {
            ["BioEngine.xml"] = $"""
                <?xml version="1.0" encoding="utf-8"?>
                <CoalesceAsset id="BioEngine" name="bioengine.ini" source="..\..\biogame\config\bioengine.ini">
                  <Sections>
                    <Section name="core.system">
                      <Property name="seekfreepcpaths" type="3">..\..\BIOGame\DLC\{ModFolder}\CookedPCConsole</Property>
                    </Section>
                    <Section name="engine.dlcmodules">
                      <Property name="{ModFolder.ToLowerInvariant()}" type="0">{ModuleNumber}</Property>
                    </Section>
                  </Sections>
                </CoalesceAsset>
                """,
        };
        var binPath = Path.Combine(cooked, $"Default_{ModFolder}.bin");
        using (var bin = LegendaryExplorerCore.Coalesced.CoalescedConverter.CompileFromMemory(coalesced))
            File.WriteAllBytes(binPath, bin.ToArray());
        using (var check = File.OpenRead(binPath))
        {
            var back = LegendaryExplorerCore.Coalesced.CoalescedConverter.DecompileGame3ToMemory(check);
            bool ok = back.TryGetValue("BioEngine.xml", out var xml) && xml.Contains(ModFolder + @"\CookedPCConsole") && xml.Contains($">{ModuleNumber}<");
            Console.WriteLine($"validate: Default_{ModFolder}.bin sections ok={ok}");
            if (!ok) { Console.Error.WriteLine("validation FAILED: DLC config"); return 1; }
        }
        // Every DLC folder carries its own PCConsoleTOC.bin; without one the game hangs at launch (seen 2026-10-27 with
        // AutoTOCLE-v2 stalling on a hand-copied 0.0.1). Mod Manager writes it on install; we write it ourselves.
        var dlcDir = Path.Combine(tmp, ModFolder);
        using (var toc = TOCCreator.CreateDLCTOCForDirectory(dlcDir, MEGame.LE3))
            File.WriteAllBytes(Path.Combine(dlcDir, "PCConsoleTOC.bin"), toc.ToArray());
        var entries = new TOCBinFile(Path.Combine(dlcDir, "PCConsoleTOC.bin")).GetAllEntries();
        Console.WriteLine($"validate: DLC TOC entries [{string.Join(", ", entries.Select(e => e.name))}]");
        if (entries.Count < Directory.GetFiles(cooked).Length) { Console.Error.WriteLine("validation FAILED: TOC is missing files"); return 1; }
        File.WriteAllText(Path.Combine(tmp, "moddesc.ini"),
            "[ModManager]\r\ncmmver = 8.0\r\n\r\n[ModInfo]\r\ngame = LE3\r\nmodname = Archipelago ME3\r\n" +
            "moddesc = Archipelago multiworld support: an imported ME2 career skips the Earth prologue and starts on the Normandy; missed checks can be bought back at the Normandy store.\r\n" +
            "modver = 0.1.0\r\nmoddev = Jerrod\r\n\r\n[CUSTOMDLC]\r\nsourcedirs = " + ModFolder + "\r\ndestdirs = " + ModFolder + "\r\n");
        if (Directory.Exists(modRoot)) Directory.Delete(modRoot, true);
        Directory.Move(tmp, modRoot);
        Console.WriteLine($"staged {modRoot}");
        return 0;
    }

    // The runtime winner of a package: the copy in the highest-mounting vanilla DLC that has it, else the base game.
    static string Winner(string bioGame, string file) =>
        Directory.EnumerateFiles(Path.Combine(bioGame, "DLC"), "Mount.dlc", SearchOption.AllDirectories)
            .Where(m => !m.Contains("DLC_MOD_", StringComparison.OrdinalIgnoreCase))
            .Select(m => (p: MountFile.GetMountPriority(m), f: Path.Combine(Path.GetDirectoryName(m)!, file)))
            .Where(x => File.Exists(x.f)).OrderByDescending(x => x.p).Select(x => x.f).FirstOrDefault()
        ?? new[] { Path.Combine(bioGame, "CookedPCConsole", file) }.FirstOrDefault(File.Exists);

    static string Describe(ExportEntry node)
    {
        var parts = new List<string>();
        foreach (var name in new[] { "EventName", "AreaName", "StartPoint", "m_nIndex", "nIndex", "Conv", "MovieName", "m_sMovieName" })
        {
            var p = node.GetProperties().FirstOrDefault(x => x.Name.Instanced == name);
            if (p == null) continue;
            parts.Add(name + "=" + p switch
            {
                IntProperty i => i.Value.ToString(),
                NameProperty n => n.Value.Instanced,
                StrProperty s => s.Value,
                ObjectProperty o => node.FileRef.GetEntry(o.Value)?.ObjectName.Instanced,
                _ => p.ToString()
            });
        }
        foreach (var v in KismetHelper.GetVariableLinksOfNode(node))
            foreach (var linked in v.LinkedNodes.OfType<ExportEntry>())
            {
                var idx = linked.GetProperties().FirstOrDefault(x => x.Name.Instanced is "m_nIndex" or "bValue" or "IntValue" or "StrValue");
                parts.Add($"{v.LinkDesc}:{linked.ClassName}{(idx is IntProperty i ? "#" + i.Value : idx is BoolProperty b ? "=" + b.Value : "")}");
            }
        return $"{node.UIndex} {node.ClassName} {node.ObjectName.Instanced} {string.Join(" ", parts)}";
    }

    static int Trace(string bioGame, string file, string remoteEvent)
    {
        var source = File.Exists(file) ? file : Winner(bioGame, file);
        Console.WriteLine("source " + source);
        using var pcc = MEPackageHandler.OpenMEPackage(source, forceLoadFromDisk: true);
        // remoteEvent "*start" traces level-start events instead of a named remote event.
        var starts = remoteEvent.StartsWith("class:")
            ? pcc.Exports.Where(e => e.ClassName == remoteEvent[6..]).ToList()
            : remoteEvent == "*start"
            ? pcc.Exports.Where(e => e.ClassName is "SeqEvent_LevelLoaded" or "SFXSeqEvt_PersistentLevelStarted" or "SFXSeqEvt_LevelIsLive" && e.Parent?.ObjectName.Instanced == "Main_Sequence").ToList()
            : pcc.Exports.Where(e => e.ClassName == "SeqEvent_RemoteEvent"
                && e.GetProperty<NameProperty>("EventName")?.Value.Instanced == remoteEvent).ToList();
        var seen = new HashSet<ExportEntry>();
        void Visit(ExportEntry node, int depth)
        {
            if (depth > 60 || !seen.Add(node)) { Console.WriteLine(new string(' ', depth * 2) + "-> (seen) " + node.UIndex); return; }
            Console.WriteLine(new string(' ', depth * 2) + Describe(node));
            var names = KismetHelper.GetOutputLinkNames(node);
            var links = KismetHelper.GetOutputLinksOfNode(node);
            for (int i = 0; i < links.Count; i++)
                foreach (var link in links[i])
                    if (link.LinkedOp is ExportEntry next)
                    {
                        Console.WriteLine(new string(' ', depth * 2 + 1) + $"[{(i < names.Count ? names[i] : i.ToString())}]");
                        Visit(next, depth + 1);
                    }
        }
        foreach (var s in starts) Visit(s, 0);
        // Reverse view: every node that links into an area transition, recursively up to 12 levels.
        var ops = pcc.Exports.Where(e => e.GetProperty<ArrayProperty<StructProperty>>("OutputLinks") != null).ToList();
        void Up(ExportEntry node, int depth, HashSet<ExportEntry> path)
        {
            Console.WriteLine(new string(' ', depth * 2) + "<- " + Describe(node));
            if (depth >= 12 || !path.Add(node)) return;
            foreach (var pred in ops)
            {
                var names = KismetHelper.GetOutputLinkNames(pred);
                var links = KismetHelper.GetOutputLinksOfNode(pred);
                for (int i = 0; i < links.Count; i++)
                    if (links[i].Any(l => l.LinkedOp == node))
                    {
                        Console.WriteLine(new string(' ', depth * 2 + 1) + $"via [{(i < names.Count ? names[i] : i.ToString())}]");
                        Up(pred, depth + 1, new HashSet<ExportEntry>(path));
                    }
            }
        }
        if (remoteEvent != "*start" && !remoteEvent.StartsWith("class:")) foreach (var area in pcc.Exports.Where(e => e.ClassName == "BioSeqAct_AreaTransition")) Up(area, 0, []);
        return starts.Count == 0 ? 1 : 0;
    }

    // Lists area transitions, plot transitions and story-manager bool/int writes in every runtime-winning package
    // whose file name matches the pattern (base game plus DLC overrides, one winner per name).
    static int Scan(string bioGame, string pattern)
    {
        var names = Directory.EnumerateFiles(bioGame, pattern, SearchOption.AllDirectories)
            .Select(Path.GetFileName).Where(n => !n.Contains("_LOC_", StringComparison.OrdinalIgnoreCase))
            .Distinct(StringComparer.OrdinalIgnoreCase).Order();
        foreach (var name in names)
        {
            var source = Winner(bioGame, name);
            if (source == null) continue;
            using var pcc = MEPackageHandler.OpenMEPackage(source, forceLoadFromDisk: true);
            foreach (var e in pcc.Exports)
            {
                if (e.ClassName is "BioSeqAct_AreaTransition" or "BioSeqAct_PMExecuteTransition"
                    || System.Text.RegularExpressions.Regex.IsMatch(e.ClassName, "Travel|LoadMap|OpenMap|Area|ChangeLevel|Normandy|GalaxyMap|LoadLevel", System.Text.RegularExpressions.RegexOptions.IgnoreCase)
                    || (e.ClassName is "SeqAct_SetBool" or "SeqAct_SetInt" && KismetHelper.GetVariableLinksOfNode(e)
                        .Any(v => v.LinkedNodes.OfType<ExportEntry>().Any(x => x.ClassName.StartsWith("BioSeqVar_StoryManager")))))
                    Console.WriteLine($"{name}	{e.InstancedFullPath.Replace("TheWorld.PersistentLevel.", "")}	{Describe(e)}");
            }
        }
        return 0;
    }

    // boolsetters <BioGame> <bools.txt> <out.tsv>: every runtime-winning package that can set one of the listed plot
    // bools, through a plot transition (Kismet PMExecuteTransition, conversation entry/reply) or a direct Kismet
    // SetBool on a story-manager bool. Transitions come from every mounted BioStateEventMap (base + DLC startups).
    static int BoolSetters(string bioGame, string boolList, string output)
    {
        var wanted = File.ReadAllLines(boolList).Select(l => l.Trim()).Where(l => l.Length > 0).Select(int.Parse).ToHashSet();
        var setters = new Dictionary<int, HashSet<int>>();  // transition id -> wanted bools it sets true
        var maps = Directory.EnumerateFiles(bioGame, "*.pcc", SearchOption.AllDirectories)
            .Where(f => Path.GetFileName(f).Equals("SFXGameInfoSP_SF.pcc", StringComparison.OrdinalIgnoreCase)
                        || (Path.GetFileName(f).StartsWith("Startup_", StringComparison.OrdinalIgnoreCase) && f.EndsWith("_INT.pcc", StringComparison.OrdinalIgnoreCase)));
        foreach (var f in maps)
        {
            using var pcc = MEPackageHandler.OpenMEPackage(f, forceLoadFromDisk: true);
            foreach (var e in pcc.Exports.Where(e => e.ClassName == "BioStateEventMap"))
                foreach (var ev in LegendaryExplorerCore.Unreal.BinaryConverters.ObjectBinary.From<LegendaryExplorerCore.Unreal.BinaryConverters.BioStateEventMap>(e).StateEvents)
                    foreach (var el in ev.Elements)
                    {
                        int b = el switch
                        {
                            LegendaryExplorerCore.Unreal.BinaryConverters.BioStateEventMap.BioStateEventElementBool x when x.NewState || x.UseParam => x.GlobalBool,
                            LegendaryExplorerCore.Unreal.BinaryConverters.BioStateEventMap.BioStateEventElementSubstate x when x.NewState || x.UseParam => x.GlobalBool,
                            _ => -1
                        };
                        if (wanted.Contains(b)) (setters.TryGetValue(ev.ID, out var hs) ? hs : setters[ev.ID] = []).Add(b);
                    }
        }
        Console.WriteLine($"{setters.Count} transitions set a listed bool");
        using var w = new StreamWriter(output);
        w.WriteLine("package	bool	via	object");
        var names = Directory.EnumerateFiles(bioGame, "*.pcc", SearchOption.AllDirectories).Select(Path.GetFileName)
            .Where(n => !n.Contains("_LOC_", StringComparison.OrdinalIgnoreCase) || n.EndsWith("_LOC_INT.pcc", StringComparison.OrdinalIgnoreCase)).Distinct(StringComparer.OrdinalIgnoreCase).Order().ToList();
        int done = 0;
        foreach (var name in names)
        {
            if (++done % 250 == 0) Console.WriteLine($"{done}/{names.Count}");
            var source = Winner(bioGame, name);
            if (source == null) continue;
            IMEPackage pcc;
            try
            {
                pcc = MEPackageHandler.UnsafePartialLoad(source, e => e.ClassName is "BioSeqAct_PMExecuteTransition" or "BioConversation" or "SeqAct_SetBool" or "BioSeqVar_StoryManagerBool");
            }
            catch (Exception ex) { Console.WriteLine($"skip {name}: {ex.Message}"); continue; }
            using (pcc)
            {
                void Hit(int transition, string via, ExportEntry e)
                {
                    if (setters.TryGetValue(transition, out var bools))
                        foreach (var b in bools) w.WriteLine($"{name}	{b}	{via} {transition}	{e.InstancedFullPath}");
                }
                foreach (var e in pcc.Exports)
                {
                    try
                    {
                        switch (e.ClassName)
                        {
                            case "BioSeqAct_PMExecuteTransition":
                                if (e.GetProperty<IntProperty>("m_nIndex") is { } t) Hit(t.Value, "kismet", e);
                                break;
                            case "BioConversation":
                                foreach (var list in new[] { "m_EntryList", "m_ReplyList" })
                                    if (e.GetProperty<ArrayProperty<StructProperty>>(list) is { } nodes)
                                        foreach (var n in nodes)
                                            if (n.GetProp<IntProperty>("nStateTransition") is { Value: >= 0 } st) Hit(st.Value, "conversation", e);
                                break;
                            case "SeqAct_SetBool":
                                foreach (var v in KismetHelper.GetVariableLinksOfNode(e).Where(v => v.LinkDesc == "Target"))
                                    foreach (var x in v.LinkedNodes.OfType<ExportEntry>().Where(x => x.ClassName == "BioSeqVar_StoryManagerBool"))
                                        if (x.GetProperty<IntProperty>("m_nIndex") is { } bi && wanted.Contains(bi.Value))
                                            w.WriteLine($"{name}	{bi.Value}	setbool	{e.InstancedFullPath}");
                                break;
                        }
                    }
                    catch (Exception) { }
                }
            }
        }
        return 0;
    }

    static int Main(string[] args)
    {
        var oodle = Environment.GetEnvironmentVariable("LE3_OODLE_DLL")
            ?? @"C:\Steam\steamapps\common\Mass Effect Legendary Edition\Game\ME3\Binaries\Win64\oo2core_8_win64.dll";
        OodleHelper.LoadOodleDll(oodle);
        // InitLib registers the package saver. SaveToStream alone skipped LEC's post-save offset fixups, so embedded
        // Wwise bank data kept stale absolute offsets and Normandy audio broke (2026-10-27).
        LegendaryExplorerCoreLib.InitLib(TaskScheduler.Default);
        if (args.Length is 2 or 3 && args[0] == "cnd")
        {
            var cnd = CNDFile.FromFile(args[1]);
            Console.WriteLine($"ids {cnd.ConditionalEntries.Min(e => e.ID)}..{cnd.ConditionalEntries.Max(e => e.ID)}");
            foreach (var entry in cnd.ConditionalEntries.Where(e => args.Length < 3 || e.ID.ToString() == args[2]).Take(40))
                Console.WriteLine($"{entry.ID}: {ME3ConditionalsCompiler.Decompile(entry)}");
            Console.WriteLine($"({cnd.ConditionalEntries.Count} entries)");
            return 0;
        }
        if (args.Length == 2 && args[0] == "coal")
        {
            using var fs = File.OpenRead(args[1]);
            foreach (var (name, xml) in LegendaryExplorerCore.Coalesced.CoalescedConverter.DecompileGame3ToMemory(fs))
                Console.WriteLine($"=== {name}\n{xml}");
            return 0;
        }
        if (args.Length == 4 && args[0] == "boolsetters") return BoolSetters(Path.GetFullPath(args[1]), args[2], args[3]);
        if (args.Length == 2 && args[0] == "sefuncs")
        {
            using var pcc = MEPackageHandler.OpenMEPackage(args[1], forceLoadFromDisk: true);
            foreach (var e in pcc.Exports.Where(e => e.ClassName == "BioStateEventMap"))
            {
                var m = LegendaryExplorerCore.Unreal.BinaryConverters.ObjectBinary.From<LegendaryExplorerCore.Unreal.BinaryConverters.BioStateEventMap>(e);
                Console.WriteLine($"{m.StateEvents.Count} events; " + string.Join(", ", m.StateEvents.SelectMany(v => v.Elements).GroupBy(x => x.Type).Select(g => $"{g.Key}={g.Count()}")));
                foreach (var g in m.StateEvents.SelectMany(v => v.Elements).OfType<LegendaryExplorerCore.Unreal.BinaryConverters.BioStateEventMap.BioStateEventElementFunction>().GroupBy(f => f.ClassName.Instanced + "." + f.FunctionName.Instanced))
                    Console.WriteLine($"  {g.Count(),5} {g.Key}");
            }
            foreach (var e in pcc.Exports.Where(e => e.ClassName == "BioCodexMap"))
            {
                var c = LegendaryExplorerCore.Unreal.BinaryConverters.ObjectBinary.From<LegendaryExplorerCore.Unreal.BinaryConverters.BioCodexMap>(e);
                Console.WriteLine($"codex {c.Sections.Count} sections {c.Pages.Count} pages");
                foreach (var pg in c.Pages) Console.WriteLine("  " + string.Join(" ", pg.GetType().GetFields().Concat<System.Reflection.MemberInfo>(pg.GetType().GetProperties()).Select(f => f.Name + "=" + (f is System.Reflection.FieldInfo fi ? fi.GetValue(pg) : ((System.Reflection.PropertyInfo)f).GetValue(pg)))));
            }
            return 0;
        }
        if (args.Length >= 3 && args[0] == "tlk")
        {
            // tlk <file.tlk>[;<file2.tlk>...] <strref>...: first file that has the string wins
            var files = args[1].Split(';').Select(f => new LegendaryExplorerCore.TLK.ME2ME3.ME2ME3TalkFile(f)).ToList();
            foreach (var id in args.Skip(2).Select(int.Parse))
                Console.WriteLine(id + "\t" + (files.Select(f => f.FindDataById(id)).FirstOrDefault(x => x != null && x != "No Data") ?? "").Replace("\n", " ").Replace("\t", " "));
            return 0;
        }
        if (args.Length == 3 && args[0] == "classscan")
        {
            // classscan <BioGame> <class>: every runtime-winning package (incl. _LOC_INT) with exports of that class
            var root = Path.GetFullPath(args[1]);
            foreach (var name in Directory.EnumerateFiles(root, "*.pcc", SearchOption.AllDirectories).Select(Path.GetFileName)
                         .Where(n => !n.Contains("_LOC_", StringComparison.OrdinalIgnoreCase) || n.EndsWith("_LOC_INT.pcc", StringComparison.OrdinalIgnoreCase))
                         .Distinct(StringComparer.OrdinalIgnoreCase).Order())
            {
                try
                {
                    using var pcc = MEPackageHandler.UnsafePartialLoad(Winner(root, name), e => e.ClassName == args[2]);
                    foreach (var e in pcc.Exports.Where(e => e.ClassName == args[2]))
                        Console.WriteLine($"{name}	{e.InstancedFullPath}	" + string.Join(" ", e.GetProperties().Where(p => p is not ArrayProperty<StructProperty> && p.Name.Instanced is not ("ObjPosX" or "ObjPosY" or "ParentSequence" or "ObjInstanceVersion")).Select(p => p.Name.Instanced + "=" + (p switch { IntProperty i => i.Value.ToString(), NameProperty n => n.Value.Instanced, ObjectProperty o => pcc.GetEntry(o.Value)?.InstancedFullPath, StrProperty st => st.Value, _ => "?" }))));
                }
                catch (Exception) { }
            }
            return 0;
        }
        if (args.Length == 2 && args[0] == "methods")
        {
            var t = typeof(MEPackageHandler).Assembly.GetType(args[1]);
            foreach (var m in t.GetMethods().Where(m => m.IsStatic).OrderBy(m => m.Name))
                Console.WriteLine($"{m.Name}({string.Join(", ", m.GetParameters().Select(p => p.ParameterType.Name + " " + p.Name))})");
            return 0;
        }
        if (args.Length == 4 && args[0] == "convo")
        {
            // convo <BioGame> <pkg> <tlk;tlk>: every conversation entry/reply with its text, conditional and transition
            var tlks = args[3].Split(';').Select(f => new LegendaryExplorerCore.TLK.ME2ME3.ME2ME3TalkFile(f)).ToList();
            string Text(int id) => tlks.Select(t => t.FindDataById(id)).FirstOrDefault(x => x != null && x != "No Data") ?? "";
            using var pcc = MEPackageHandler.OpenMEPackage(File.Exists(args[2]) ? args[2] : Winner(Path.GetFullPath(args[1]), args[2]), forceLoadFromDisk: true);
            foreach (var e in pcc.Exports.Where(x => x.ClassName == "BioConversation"))
                foreach (var list in new[] { "m_EntryList", "m_ReplyList" })
                {
                    var nodes = e.GetProperty<ArrayProperty<StructProperty>>(list);
                    if (nodes == null) continue;
                    for (int i = 0; i < nodes.Count; i++)
                    {
                        var n = nodes[i];
                        int Int(string name) => n.GetProp<IntProperty>(name)?.Value ?? -9;
                        var srText = n.GetProp<StringRefProperty>("srText")?.Value ?? 0;
                        var para = n.GetProp<StringRefProperty>("srParaphrase")?.Value ?? 0;
                        Console.WriteLine($"{e.ObjectName.Instanced}	{list[2..^4]}[{i}]	cond={Int("nConditionalFunc")}/{Int("nConditionalParam")} fire={n.GetProp<BoolProperty>("bFireConditional")?.Value} trans={Int("nStateTransition")}/{Int("nStateTransitionParam")}	{Text(para)} | {Text(srText).Replace("\n", " ")}");
                    }
                }
            return 0;
        }
        if (args.Length == 4 && args[0] == "galaxy")
        {
            // galaxy <BioGame> <pkg> <tlk>: every cluster/system/planet with its name and visibility/usable/land conditionals
            var tlk = new LegendaryExplorerCore.TLK.ME2ME3.ME2ME3TalkFile(args[3]);
            using var pcc = MEPackageHandler.OpenMEPackage(File.Exists(args[2]) ? args[2] : Winner(Path.GetFullPath(args[1]), args[2]), forceLoadFromDisk: true);
            foreach (var e in pcc.Exports.Where(x => x.ClassName is "SFXCluster" or "SFXSystem" or "BioPlanet").OrderBy(x => x.InstancedFullPath))
            {
                int? I(string n) => e.GetProperty<IntProperty>(n)?.Value;
                var name = e.GetProperty<StringRefProperty>("DisplayName")?.Value ?? 0;
                Console.WriteLine($"{e.InstancedFullPath.Replace("BIOG_GalaxyMap.GalaxyMap.", "").Replace("biog_galaxymap.GalaxyMap.", "")}	{tlk.FindDataById(name)}	vis={I("VisibleConditional")} use={I("UsableConditional")} land={I("PlanetLandCondition")} map={e.GetProperty<StrProperty>("MapName")?.Value}");
            }
            return 0;
        }
        if (args.Length == 2 && args[0] == "types")
        {
            foreach (var t in typeof(MEPackageHandler).Assembly.GetTypes().Where(t => System.Text.RegularExpressions.Regex.IsMatch(t.FullName ?? "", args[1])))
                Console.WriteLine(t.FullName + " : " + string.Join(",", t.GetFields().Select(f => f.FieldType.Name + " " + f.Name).Concat(t.GetProperties().Select(f => f.PropertyType.Name + " " + f.Name))));
            return 0;
        }
        if (args.Length == 1 && args[0] == "api")
        {
            foreach (var t in typeof(MEPackageHandler).Assembly.GetTypes().Where(t => t.Name is "MEPackage" or "IMEPackage" or "UnrealPackageFile" or "IMEPackageExtensions" || t.Name.Contains("PackageExtensions")))
                foreach (var m in t.GetMethods().Where(m => m.Name.StartsWith("Save")))
                    Console.WriteLine($"{t.Name}.{m.Name}({string.Join(", ", m.GetParameters().Select(p => p.ParameterType.Name + " " + p.Name))})");
            return 0;
        }
        DiagVanilla = args.Contains("--diag-vanilla-conditionals");
        NoMars = args.Contains("--no-mars");
        args = args.Where(a => a != "--diag-vanilla-conditionals" && a != "--no-mars").ToArray();
        if (args.Length == 3 && args[0] == "openstart") return Build(Path.GetFullPath(args[1]), Path.GetFullPath(args[2]));
        if (args.Length == 4 && args[0] == "trace") return Trace(Path.GetFullPath(args[1]), args[2], args[3]);
        if (args.Length == 4 && args[0] == "props")
        {
            using var pcc = MEPackageHandler.OpenMEPackage(File.Exists(args[2]) ? args[2] : Winner(Path.GetFullPath(args[1]), args[2]), forceLoadFromDisk: true);
            var e = pcc.FindExport(args[3]);
            foreach (var prop in e.GetProperties()) Console.WriteLine($"{prop.GetType().Name} {prop.Name.Instanced} = {prop switch { IntProperty i => i.Value.ToString(), NameProperty n => n.Value.Instanced, StrProperty st => st.Value, BoolProperty b => b.Value.ToString(), ObjectProperty o => pcc.GetEntry(o.Value)?.InstancedFullPath, EnumProperty en => en.EnumType.Instanced + "::" + en.Value.Instanced, _ => prop.ToString() }}");
            foreach (var arr in e.GetProperties().OfType<ArrayProperty<StructProperty>>())
                for (int i = 0; i < arr.Count; i++)
                    Console.WriteLine($"  {arr.Name.Instanced}[{i}] " + string.Join(" ", arr[i].Properties.Select(sp => $"{sp.Name.Instanced}={sp switch { IntProperty x => x.Value.ToString(), NameProperty x => x.Value.Instanced, StrProperty x => x.Value, BoolProperty x => x.Value.ToString(), FloatProperty x => x.Value.ToString(), StringRefProperty x => x.Value.ToString(), EnumProperty x => x.Value.Instanced, ArrayProperty<IntProperty> x => "[" + string.Join(",", x.Select(v => v.Value)) + "]", ArrayProperty<NameProperty> x => "[" + string.Join(",", x.Select(v => v.Value.Instanced)) + "]", StructProperty x => "{" + string.Join(" ", x.Properties.Select(q => q.Name.Instanced + "=" + (q switch { IntProperty y => y.Value.ToString(), StringRefProperty y => y.Value.ToString(), NameProperty y => y.Value.Instanced, StrProperty y => y.Value, BoolProperty y => y.Value.ToString(), FloatProperty y => y.Value.ToString(), EnumProperty y => y.Value.Instanced, _ => q.GetType().Name }))) + "}", _ => sp.GetType().Name }}")));
            Console.WriteLine(Describe(e));
            return 0;
        }
        if (args.Length == 4 && args[0] == "ofclass")
        {
            using var pcc = MEPackageHandler.OpenMEPackage(Winner(Path.GetFullPath(args[1]), args[2]), forceLoadFromDisk: true);
            foreach (var e in pcc.Exports.Where(e => e.ClassName == args[3]))
            {
                Console.WriteLine(e.InstancedFullPath + " :: " + Describe(e));
                foreach (var prop in e.GetProperties().Where(p => p.Name.Instanced is not ("ObjPosX" or "ObjPosY" or "ParentSequence" or "OutputLinks" or "VariableLinks" or "InputLinks" or "ObjInstanceVersion" or "m_aObjComment")))
                    Console.WriteLine($"   {prop.Name.Instanced} = {prop switch { IntProperty i => i.Value.ToString(), NameProperty n => n.Value.Instanced, StrProperty st => st.Value, BoolProperty b => b.Value.ToString(), ObjectProperty o => pcc.GetEntry(o.Value)?.InstancedFullPath, ArrayProperty<ObjectProperty> a => string.Join(",", a.Select(x => pcc.GetEntry(x.Value)?.InstancedFullPath)), _ => prop.GetType().Name }}");
            }
            return 0;
        }
        if (args.Length == 3 && args[0] == "align")
        {
            // align <vanilla> <ours>: inline bulk data start (offset value) modulo 16/2048 for Wwise banks
            foreach (var path in new[] { args[1], args[2] })
            {
                using var pcc = MEPackageHandler.OpenMEPackage(path, forceLoadFromDisk: true);
                var mods = new List<string>();
                foreach (var e in pcc.Exports.Where(x => x.ClassName == "WwiseBank").Take(12))
                {
                    var d = e.Data;
                    for (int i = 0; i + 4 <= d.Length; i++)
                        if (BitConverter.ToInt32(d, i) == e.DataOffset + i + 4) { mods.Add($"{(e.DataOffset + i + 4) % 16}/{(e.DataOffset + i + 4) % 2048}"); break; }
                }
                Console.WriteLine($"{Path.GetFileName(Path.GetDirectoryName(Path.GetDirectoryName(path)))}: {string.Join(" ", mods)}");
            }
            return 0;
        }
        if (args.Length == 3 && args[0] == "stale")
        {
            // stale <vanilla> <ours>: per class, self-offsets that still hold the vanilla value although the export moved
            using var a = MEPackageHandler.OpenMEPackage(args[1], forceLoadFromDisk: true);
            using var b = MEPackageHandler.OpenMEPackage(args[2], forceLoadFromDisk: true);
            var theirs = b.Exports.GroupBy(e => e.InstancedFullPath).ToDictionary(g => g.Key, g => g.First());
            var counts = new Dictionary<string, (int stale, int tracked)>();
            foreach (var e in a.Exports)
            {
                if (!theirs.TryGetValue(e.InstancedFullPath, out var o) || o.DataOffset == e.DataOffset) continue;
                var d = e.Data; var od = o.Data;
                for (int i = 0; i + 4 <= d.Length && i + 4 <= od.Length; i++)
                {
                    if (BitConverter.ToInt32(d, i) != e.DataOffset + i + 4) continue;
                    var c = counts.GetValueOrDefault(e.ClassName);
                    if (BitConverter.ToInt32(od, i) == o.DataOffset + i + 4) c.tracked++; else if (BitConverter.ToInt32(od, i) == e.DataOffset + i + 4) c.stale++;
                    counts[e.ClassName] = c;
                }
            }
            foreach (var (cls, c) in counts.OrderBy(x => x.Key)) Console.WriteLine($"{cls}: stale={c.stale} tracked={c.tracked}");
            return 0;
        }
        if (args.Length == 3 && args[0] == "cmpaudio")
        {
            // cmpaudio <vanilla pcc> <ours pcc>: compare every Wwise/sound export's serialized data by path
            using var a = MEPackageHandler.OpenMEPackage(args[1], forceLoadFromDisk: true);
            using var b = MEPackageHandler.OpenMEPackage(args[2], forceLoadFromDisk: true);
            Console.WriteLine($"vanilla flags={a.Flags} compressed={a.IsCompressed} exports={a.ExportCount} | ours flags={b.Flags} compressed={b.IsCompressed} exports={b.ExportCount}");
            var theirs = b.Exports.GroupBy(e => e.InstancedFullPath).ToDictionary(g => g.Key, g => g.First());
            int same = 0, diff = 0, missing = 0;
            foreach (var e in a.Exports.Where(e => e.ClassName.StartsWith("Wwise") || e.ClassName.Contains("Sound") || e.ClassName.Contains("Audio")))
            {
                if (!theirs.TryGetValue(e.InstancedFullPath, out var o)) { missing++; Console.WriteLine("MISSING " + e.InstancedFullPath); continue; }
                if (e.Data.AsSpan().SequenceEqual(o.Data)) same++;
                else { diff++; if (diff <= 10) Console.WriteLine($"DIFF {e.ClassName} {e.InstancedFullPath} {e.DataSize} vs {o.DataSize}"); }
            }
            Console.WriteLine($"audio exports: same={same} diff={diff} missing={missing}");
            // Embedded bulk data uses absolute offsets inside the export binary; if an export moved but its bytes did
            // not change, any self-referencing offset is now stale.
            foreach (var e in a.Exports.Where(e => e.ClassName is "WwiseStream" or "WwiseBank" or "SoundNodeWave"))
            {
                var o = theirs[e.InstancedFullPath];
                var data = e.Data;
                bool selfRef = false;
                for (int i = 0; i + 4 <= data.Length; i += 4)
                {
                    int v = BitConverter.ToInt32(data, i);
                    if (v > 0 && v >= e.DataOffset && v < e.DataOffset + e.DataSize) { selfRef = true; break; }
                }
                bool oursSelf = false;
                var od = o.Data;
                for (int i = 0; i + 4 <= od.Length; i += 4)
                {
                    int v = BitConverter.ToInt32(od, i);
                    if (v > 0 && v >= o.DataOffset && v < o.DataOffset + o.DataSize) { oursSelf = true; break; }
                }
                if (selfRef != oursSelf) Console.WriteLine($"STALE {e.ClassName} {e.ObjectName.Instanced} vanilla={e.DataOffset} ours={o.DataOffset}");
                else if (selfRef) Console.WriteLine($"ok {e.ClassName} {e.ObjectName.Instanced} self-offset tracks its move ({e.DataOffset} -> {o.DataOffset})");
            }
            return 0;
        }
        if (args.Length == 4 && args[0] == "seqobjs")
        {
            using var pcc = MEPackageHandler.OpenMEPackage(File.Exists(args[2]) ? args[2] : Winner(Path.GetFullPath(args[1]), args[2]), forceLoadFromDisk: true);
            var seq = pcc.FindExport(args[3]);
            var listed = seq.GetProperty<ArrayProperty<ObjectProperty>>("SequenceObjects").Select(o => o.Value).ToHashSet();
            foreach (var e in pcc.Exports.Where(x => x.Parent == seq))
                Console.WriteLine($"{(listed.Contains(e.UIndex) ? "listed  " : "MISSING ")} {e.UIndex} {e.ClassName} {e.ObjectName.Instanced}");
            return 0;
        }
        if (args.Length == 4 && args[0] == "seqdump")
        {
            // seqdump <BioGame> <pkg> <sequence path>: every op directly in the sequence with its outputs and variables
            using var pcc = MEPackageHandler.OpenMEPackage(File.Exists(args[2]) ? args[2] : Winner(Path.GetFullPath(args[1]), args[2]), forceLoadFromDisk: true);
            var seq = pcc.FindExport(args[3]);
            foreach (var e in pcc.Exports.Where(x => x.Parent == seq).OrderBy(x => x.UIndex))
            {
                var outs = e.GetProperty<ArrayProperty<StructProperty>>("OutputLinks") == null ? "" : string.Join(" ", KismetHelper.GetOutputLinkNames(e).Zip(KismetHelper.GetOutputLinksOfNode(e),
                    (n, l) => $"[{n}->{string.Join(",", l.Select(x => x.LinkedOp?.ObjectName.Instanced))}]"));
                var val = e.GetProperties().FirstOrDefault(x => x.Name.Instanced is "NameValue" or "bValue" or "IntValue" or "VariableLabel" or "m_nIndex" or "LinkDesc" or "OutputLabel" or "InputLabel");
                Console.WriteLine($"{e.UIndex} {e.ClassName} {e.ObjectName.Instanced} {outs} {Describe(e).Split(' ', 4).ElementAtOrDefault(3)} {(val is NameProperty np ? "=" + np.Value.Instanced : val is StrProperty sp ? "=" + sp.Value : val is IntProperty ip ? "=" + ip.Value : "")}");
            }
            return 0;
        }
        if (args.Length == 4 && args[0] == "vars")
        {
            // vars <BioGame> <pkg> <export path>: each variable link with the linked variable's value
            using var pcc = MEPackageHandler.OpenMEPackage(File.Exists(args[2]) ? args[2] : Winner(Path.GetFullPath(args[1]), args[2]), forceLoadFromDisk: true);
            var e = pcc.FindExport(args[3]);
            foreach (var v in KismetHelper.GetVariableLinksOfNode(e))
                foreach (var linked in v.LinkedNodes.OfType<ExportEntry>())
                    Console.WriteLine($"{v.LinkDesc}: {linked.InstancedFullPath} {string.Join(" ", linked.GetProperties().Where(p => p.Name.Instanced is "bValue" or "IntValue" or "m_nIndex" or "ObjValue" or "FindVarName" or "VarName").Select(p => p.Name.Instanced + "=" + p switch { IntProperty i => i.Value.ToString(), BoolProperty b => b.Value.ToString(), NameProperty n => n.Value.Instanced, ObjectProperty o => pcc.GetEntry(o.Value)?.InstancedFullPath, _ => p.ToString() }))}");
            var refd = e.GetProperty<ObjectProperty>("oSequenceReference");
            if (refd != null) Console.WriteLine("references " + pcc.GetEntry(refd.Value)?.InstancedFullPath);
            return 0;
        }
        if (args.Length == 4 && args[0] == "find")
        {
            // find <BioGame> <file pattern> <export full path>: which runtime-winning packages define that export
            var root = Path.GetFullPath(args[1]);
            foreach (var name in Directory.EnumerateFiles(root, args[2], SearchOption.AllDirectories).Select(Path.GetFileName)
                         .Where(n => !n.Contains("_LOC_", StringComparison.OrdinalIgnoreCase)).Distinct(StringComparer.OrdinalIgnoreCase).Order())
            {
                using var pcc = MEPackageHandler.UnsafePartialLoad(Winner(root, name), e => e.InstancedFullPath.StartsWith(args[3], StringComparison.OrdinalIgnoreCase));
                var hits = pcc.Exports.Where(e => e.InstancedFullPath.Equals(args[3], StringComparison.OrdinalIgnoreCase)).ToList();
                if (hits.Count > 0) Console.WriteLine($"{name}: {string.Join(",", hits.Select(h => h.ClassName + "#" + h.UIndex))}");
            }
            return 0;
        }
        if (args.Length == 3 && args[0] == "classes")
        {
            using var pcc = MEPackageHandler.OpenMEPackage(File.Exists(args[2]) ? args[2] : Winner(Path.GetFullPath(args[1]), args[2]), forceLoadFromDisk: true);
            foreach (var g in pcc.Exports.Where(e => e.GetProperty<ArrayProperty<StructProperty>>("OutputLinks") != null)
                         .GroupBy(e => e.ClassName).OrderBy(g => g.Key))
                Console.WriteLine($"{g.Count(),5} {g.Key}");
            return 0;
        }
        if (args.Length == 3 && args[0] == "scan") return Scan(Path.GetFullPath(args[1]), args[2]);
        Console.Error.WriteLine("usage: le3mod trace <LE3 BioGame dir> <package> <remote event>");
        return 2;
    }
}
