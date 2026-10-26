// le3mod: builds the LE3 game-side mod (DLC_MOD_ArchipelagoME3) from the player's own game files, modeled on the ME2
// project's le2mod (copied pattern; the ME2 checkout is not modified). Writes only under a staging folder.
//   le3mod trace <LE3 BioGame dir> <package file> <remote event>   prints the Kismet reachable from a remote event
using System.IO;
using LegendaryExplorerCore;
using LegendaryExplorerCore.Compression;
using LegendaryExplorerCore.GameFilesystem;
using LegendaryExplorerCore.Kismet;
using LegendaryExplorerCore.Packages;
using LegendaryExplorerCore.TLK;
using LegendaryExplorerCore.TLK.ME2ME3;
using LegendaryExplorerCore.Unreal;

static class Program
{
    const string ModFolder = "DLC_MOD_ArchipelagoME3";
    const string ModName = "ArchipelagoME3";
    const int NameStrRef = 43000000;
    const int MountPriority = 4300;   // above every installed LE3 DLC (checked at build time)
    const string Seq = "TheWorld.PersistentLevel.Main_Sequence";
    const string ImportCheck = Seq + ".SeqCond_CompareBool_1";      // ME2_Import (21554)
    const string ProEarArea = Seq + ".BioSeqAct_AreaTransition_1";   // Biop_ProEar
    const int ImportBool = 21554;
    const int RescuedAshBool = 13827;
    // Earth's lasting squad outcome (research/le3_proear_transitions.tsv and the 2026-10-26 save diff):
    // the Virmire survivor joins (32 Ashley / 31 Kaidan: In_Party + Is_Selectable) and James (64 Marine).
    const int AshleyJoins = 32, KaidanJoins = 31, JamesJoins = 64;

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
            var normandy = Create("BioSeqAct_AreaTransition");
            normandy.WriteProperty(new NameProperty("BioP_Nor", "AreaName"));
            links[trueIdx].Clear();
            KismetHelper.WriteOutputLinksToNode(check, links);
            KismetHelper.CreateOutputLink(check, "True", survivor);
            Link(survivor, "True", ashley);
            Link(survivor, "False", kaidan);
            Link(ashley, "Out", james);
            Link(kaidan, "Out", james);
            Link(james, "Out", normandy);
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
            var ja = Follow(a); var jk = Follow(k); var area = Follow(ja);
            bool ok = survivor.ClassName == "BioSeqAct_PMCheckState" && Id(survivor) == RescuedAshBool
                && Id(a) == AshleyJoins && Id(k) == KaidanJoins && ja == jk && Id(ja) == JamesJoins
                && area?.ClassName == "BioSeqAct_AreaTransition" && area.GetProperty<NameProperty>("AreaName")?.Value.Instanced == "BioP_Nor"
                && pcc.FindExport(ProEarArea).GetProperty<NameProperty>("AreaName")?.Value.Instanced == "Biop_ProEar";
            Console.WriteLine($"validate: ME2_Import True -> S{Id(survivor)} ? T{Id(a)} : T{Id(k)} -> T{Id(ja)} -> {area?.GetProperty<NameProperty>("AreaName")?.Value.Instanced}");
            if (!ok) { Console.Error.WriteLine("validation FAILED; staging left unchanged"); return 1; }
        }
        Console.WriteLine($"Earth skipped for imported careers (source {source})");
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
        // Flags copied from a vanilla single-player DLC (Leviathan) so the mount type matches.
        var template = new MountFile(Path.Combine(bioGame, "DLC", "DLC_EXP_Pack001", "CookedPCConsole", "Mount.dlc"));
        new MountFile { Game = MEGame.LE3, MountPriority = MountPriority, TLKID = NameStrRef, MountFlags = template.MountFlags }
            .WriteMountFile(Path.Combine(cooked, "Mount.dlc"));
        HuffmanCompression.SaveToTlkFile(Path.Combine(cooked, $"{ModFolder}_INT.tlk"),
            [new TLKStringRef(NameStrRef, "Archipelago ME3 (open start test)")]);
        File.WriteAllText(Path.Combine(tmp, "moddesc.ini"),
            "[ModManager]\r\ncmmver = 8.0\r\n\r\n[ModInfo]\r\ngame = LE3\r\nmodname = Archipelago ME3 open start (TEST)\r\n" +
            "moddesc = Test build: an imported ME2 career skips the Earth prologue and starts on the Normandy.\r\n" +
            "modver = 0.0.1\r\nmoddev = Jerrod\r\n\r\n[CUSTOMDLC]\r\nsourcedirs = " + ModFolder + "\r\ndestdirs = " + ModFolder + "\r\n");
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
        var starts = pcc.Exports.Where(e => e.ClassName == "SeqEvent_RemoteEvent"
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
        foreach (var area in pcc.Exports.Where(e => e.ClassName == "BioSeqAct_AreaTransition")) Up(area, 0, []);
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
        if (args.Length == 1 && args[0] == "api")
        {
            foreach (var t in typeof(MEPackageHandler).Assembly.GetTypes().Where(t => t.Name is "MEPackage" or "IMEPackage" or "UnrealPackageFile" or "IMEPackageExtensions" || t.Name.Contains("PackageExtensions")))
                foreach (var m in t.GetMethods().Where(m => m.Name.StartsWith("Save")))
                    Console.WriteLine($"{t.Name}.{m.Name}({string.Join(", ", m.GetParameters().Select(p => p.ParameterType.Name + " " + p.Name))})");
            return 0;
        }
        if (args.Length == 3 && args[0] == "openstart") return Build(Path.GetFullPath(args[1]), Path.GetFullPath(args[2]));
        if (args.Length == 4 && args[0] == "trace") return Trace(Path.GetFullPath(args[1]), args[2], args[3]);
        if (args.Length == 4 && args[0] == "props")
        {
            using var pcc = MEPackageHandler.OpenMEPackage(Winner(Path.GetFullPath(args[1]), args[2]), forceLoadFromDisk: true);
            var e = pcc.FindExport(args[3]);
            foreach (var prop in e.GetProperties()) Console.WriteLine($"{prop.GetType().Name} {prop.Name.Instanced} = {prop switch { IntProperty i => i.Value.ToString(), NameProperty n => n.Value.Instanced, StrProperty st => st.Value, BoolProperty b => b.Value.ToString(), ObjectProperty o => pcc.GetEntry(o.Value)?.InstancedFullPath, _ => prop.ToString() }}");
            Console.WriteLine(Describe(e));
            return 0;
        }
        if (args.Length == 3 && args[0] == "classes")
        {
            using var pcc = MEPackageHandler.OpenMEPackage(Winner(Path.GetFullPath(args[1]), args[2]), forceLoadFromDisk: true);
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
