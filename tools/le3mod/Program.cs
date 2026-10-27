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

    // Imported careers (D3: every AP career) skip Earth: ME2_Import True -> survivor check -> squad transitions ->
    // a new AreaTransition to BioP_Nor. Non-import and NG+ routes keep Biop_ProEar. Fails closed on any unexpected shape.
    // This LEC build gives new sequence objects their class-default outputs, so link into an existing output by name
    // and only add an output when the class has none of that name.
    static void Link(ExportEntry from, string output, ExportEntry to)
    {
        if (KismetHelper.GetOutputLinkNames(from).Contains(output)) KismetHelper.CreateOutputLink(from, output, to);
        else KismetHelper.CreateNewOutputLink(from, output, to);
    }

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
            Link(liara, "Out", normandy);
            using (var saved = pcc.SaveToStream(true, true, true)) File.WriteAllBytes(outPcc, saved.ToArray());
        }
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
            var ja = Follow(a); var jk = Follow(k); var li = Follow(ja); var area = Follow(li);
            bool ok = survivor.ClassName == "BioSeqAct_PMCheckState" && Id(survivor) == RescuedAshBool
                && Id(a) == AshleyJoins && Id(k) == KaidanJoins && ja == jk && Id(ja) == JamesJoins && Id(li) == LiaraNotSelectable
                && area?.ClassName == "BioSeqAct_AreaTransition" && area.GetProperty<NameProperty>("AreaName")?.Value.Instanced == "BioP_Nor"
                && pcc.FindExport(ProEarArea).GetProperty<NameProperty>("AreaName")?.Value.Instanced == "Biop_ProEar";
            Console.WriteLine($"validate: ME2_Import True -> S{Id(survivor)} ? T{Id(a)} : T{Id(k)} -> T{Id(ja)} -> T{Id(li)} -> {area?.GetProperty<NameProperty>("AreaName")?.Value.Instanced}");
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
            using (var saved = pcc.SaveToStream(true, true, true)) File.WriteAllBytes(outPcc, saved.ToArray());
        }
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
            using (var saved = pcc.SaveToStream(true, true, true)) File.WriteAllBytes(outPcc, saved.ToArray());
        }
        var cnd = new CNDFile { ConditionalEntries = [] };
        foreach (var (id, expression) in new[] { (MarsConditional, MarsExpression), (LocalClusterConditional, LocalClusterExpression) })
        {
            var entry = new CNDFile.ConditionalEntry { ID = id };
            ME3ConditionalsCompiler.Compile(entry, expression);
            cnd.ConditionalEntries.Add(entry);
        }
        var cndPath = Path.Combine(cooked, $"Conditionals{ModFolder}.cnd");
        cnd.ToFile(cndPath);
        using (var pcc = MEPackageHandler.OpenMEPackage(outPcc, forceLoadFromDisk: true))
        {
            var mars = pcc.FindExport(MarsPath);
            var cluster = pcc.FindExport(LocalClusterPath);
            var back = CNDFile.FromFile(cndPath).ConditionalEntries.ToDictionary(e => e.ID, e => ME3ConditionalsCompiler.Decompile(e));
            if (DiagVanilla) return 0;
            bool ok = mars?.GetProperty<StrProperty>("MapName")?.Value == "BioP_ProMar"
                && mars.GetProperty<IntProperty>("PlanetLandCondition")?.Value == MarsConditional
                && cluster?.GetProperty<IntProperty>("VisibleConditional")?.Value == LocalClusterConditional
                && cluster.GetProperty<IntProperty>("UsableConditional")?.Value == LocalClusterConditional
                && back.Count == 2 && back.GetValueOrDefault(MarsConditional) == MarsExpression
                && back.GetValueOrDefault(LocalClusterConditional) == LocalClusterExpression;
            Console.WriteLine($"validate: Mars MapName={mars?.GetProperty<StrProperty>("MapName")?.Value} land=C{mars?.GetProperty<IntProperty>("PlanetLandCondition")?.Value}; Local Cluster C{cluster?.GetProperty<IntProperty>("VisibleConditional")?.Value}; {string.Join("; ", back.Select(kv => $"C{kv.Key} = {kv.Value}"))}");
            if (!ok) { Console.Error.WriteLine("validation FAILED; staging left unchanged"); return 1; }
        }
        if (DiagVanilla) { Console.WriteLine("DIAGNOSTIC build: vanilla conditionals 2744/79 on Local Cluster and Mars"); return 0; }
        Console.WriteLine($"Mars landable (galaxy source {source})");
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
        // Flags copied from a vanilla single-player DLC (Leviathan) so the mount type matches.
        var template = new MountFile(Path.Combine(bioGame, "DLC", "DLC_EXP_Pack001", "CookedPCConsole", "Mount.dlc"));
        new MountFile { Game = MEGame.LE3, MountPriority = MountPriority, TLKID = NameStrRef, MountFlags = template.MountFlags }
            .WriteMountFile(Path.Combine(cooked, "Mount.dlc"));
        HuffmanCompression.SaveToTlkFile(Path.Combine(cooked, $"{ModFolder}_INT.tlk"),
            [new TLKStringRef(NameStrRef, "Archipelago ME3 (open start test)")]);
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
            "[ModManager]\r\ncmmver = 8.0\r\n\r\n[ModInfo]\r\ngame = LE3\r\nmodname = Archipelago ME3 open start (TEST)\r\n" +
            "moddesc = Test build: an imported ME2 career skips the Earth prologue and starts on the Normandy.\r\n" +
            "modver = 0.0.7\r\nmoddev = Jerrod\r\n\r\n[CUSTOMDLC]\r\nsourcedirs = " + ModFolder + "\r\ndestdirs = " + ModFolder + "\r\n");
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

    static int Main(string[] args)
    {
        var oodle = Environment.GetEnvironmentVariable("LE3_OODLE_DLL")
            ?? @"C:\Steam\steamapps\common\Mass Effect Legendary Edition\Game\ME3\Binaries\Win64\oo2core_8_win64.dll";
        OodleHelper.LoadOodleDll(oodle);
        MEPackageHandler.Initialize();
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
