using LegendaryExplorerCore.Packages;
using System.IO;
using LegendaryExplorerCore.Coalesced;
using System.Xml.Linq;
using LegendaryExplorerCore.Unreal;
using System.Text.Json;
using System.Text.RegularExpressions;
using LegendaryExplorerCore.GameFilesystem;

// Export tables only; never save, patch, or load gameplay state.
MEPackageHandler.Initialize();
// Supplied backup first, then LE3_OODLE_DLL, then the installed game's copy.
LegendaryExplorerCore.Compression.OodleHelper.LoadOodleDll(new[] {
        Path.GetFullPath("ME3LE Backup/Binaries/Win64/oo2core_8_win64.dll"),
        Environment.GetEnvironmentVariable("LE3_OODLE_DLL") ?? "",
        @"C:\Steam\steamapps\common\Mass Effect Legendary Edition\Game\ME3\Binaries\Win64\oo2core_8_win64.dll" }
    .First(path => path.Length > 0 && File.Exists(path)));
if (args.Length > 1 && args[0] == "--state-events")
{
    // Binary state-event data is not exposed by ExportEntry.GetProperties().
    // Serialize only the converter's own data members, excluding ObjectBinary's
    // package/export back-reference. This mode never saves a package.
    foreach (var path in args.Skip(1))
    {
        using var package = MEPackageHandler.OpenMEPackage(Path.GetFullPath(path), forceLoadFromDisk: true);
        foreach (var export in package.Exports.Where(e => e.ClassName is "BioStateEventMap" or "BioConsequenceMap"))
        {
            var map = LegendaryExplorerCore.Unreal.BinaryConverters.ObjectBinary
                .From<LegendaryExplorerCore.Unreal.BinaryConverters.BioStateEventMap>(export);
            var flags = System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance
                | System.Reflection.BindingFlags.DeclaredOnly;
            var type = typeof(LegendaryExplorerCore.Unreal.BinaryConverters.BioStateEventMap);
            var fields = type.GetFields(flags).ToDictionary(f => f.Name, f => f.GetValue(map));
            foreach (var property in type.GetProperties(flags).Where(p => p.CanRead && p.GetIndexParameters().Length == 0))
                fields[property.Name] = property.GetValue(map);
            Console.WriteLine(Newtonsoft.Json.JsonConvert.SerializeObject(new {
                source = path, export = export.UIndex, class_name = export.ClassName,
                object_path = export.InstancedFullPath, data = fields
            }));
        }
    }
    return;
}
if (args.Length > 3 && args[0] == "--audit-int-block")
{
    int first = int.Parse(args[1]), count = int.Parse(args[2]);
    if (count < 1 || count > 256 || first < 0 || (first & 255) + count > 256)
        throw new ArgumentException("Block must fit within a single 256-value page");
    byte lo = (byte)first, b1 = (byte)(first >> 8), b2 = (byte)(first >> 16), b3 = (byte)(first >> 24);
    long bytes = 0; int files = 0, errors = 0, hits = 0;
    void Scan(byte[] data, string path, string export)
    {
        bytes += data.Length;
        int offset = 3;
        while (offset < data.Length)
        {
            int relative = data.AsSpan(offset).IndexOf(b3);
            if (relative < 0) break;
            int end = offset + relative;
            if (data[end - 1] == b2 && data[end - 2] == b1 && data[end - 3] >= lo && data[end - 3] < lo + count)
            {
                hits++;
                Console.WriteLine(JsonSerializer.Serialize(new { kind = "hit", source = path, export,
                    offset = end - 3, value = first + data[end - 3] - lo }));
            }
            offset = end + 1;
        }
    }
    foreach (var root in args.Skip(3))
    foreach (var path in Directory.Exists(root) ? Directory.EnumerateFiles(root, "*.pcc", SearchOption.AllDirectories).Order().AsEnumerable() : new[] { root })
    {
        try
        {
            if (Path.GetExtension(path).Equals(".pcc", StringComparison.OrdinalIgnoreCase))
            {
                using var package = MEPackageHandler.OpenMEPackage(Path.GetFullPath(path), forceLoadFromDisk: true);
                foreach (var export in package.Exports) Scan(export.Data, path, export.InstancedFullPath);
            }
            else Scan(File.ReadAllBytes(path), path, "<raw file>");
            files++;
            if (files % 250 == 0) Console.Error.WriteLine($"Audited {files} files, {bytes} export bytes, {hits} hits");
        }
        catch (Exception error) { errors++; Console.Error.WriteLine($"AUDIT ERROR {path}: {error.Message}"); }
    }
    Console.WriteLine(JsonSerializer.Serialize(new { kind = "summary", first, count, files, bytes, hits, errors }));
    if (errors != 0) Environment.ExitCode = 1;
    return;
}
if (args.Contains("--api"))
{
    var apiPattern = args.Length > 1 ? args[1] : "Oodle|Coalesced|LegendaryExplorerCoreLib";
    foreach (var type in typeof(MEPackageHandler).Assembly.GetTypes().Where(t => Regex.IsMatch(t.Name, apiPattern)))
    {
        Console.WriteLine(type.FullName);
        foreach (var ctor in type.GetConstructors()) Console.WriteLine(ctor);
        foreach (var method in type.GetMethods(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static)) Console.WriteLine(method);
        foreach (var method in type.GetMethods(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.DeclaredOnly)) Console.WriteLine(method);
    }
    return;
}
if (args.Length == 2 && args[0] == "--review-int-block")
{
    var records = File.ReadLines(args[1]).Select(line => JsonDocument.Parse(line).RootElement.Clone()).ToArray();
    var summary = records.Single(r => r.GetProperty("kind").GetString() == "summary");
    int first = summary.GetProperty("first").GetInt32(), count = summary.GetProperty("count").GetInt32();
    IEnumerable<string> Matches(Property property, string path)
    {
        if (property is IntProperty integer && integer.Value >= first && integer.Value < first + count) yield return path;
        if (property is StructProperty structure)
            foreach (var child in structure.Properties)
                foreach (var found in Matches(child, path + "." + child.Name.Instanced)) yield return found;
        if (property is ArrayProperty<IntProperty> integers)
            for (int i = 0; i < integers.Count; i++)
                foreach (var found in Matches(integers[i], path + $"[{i}]")) yield return found;
        if (property is ArrayProperty<StructProperty> structures)
            for (int i = 0; i < structures.Count; i++)
                foreach (var found in Matches(structures[i], path + $"[{i}]")) yield return found;
    }
    foreach (var group in records.Where(r => r.GetProperty("kind").GetString() == "hit").GroupBy(r => r.GetProperty("source").GetString()))
    {
        var names = group.Select(r => r.GetProperty("export").GetString()).ToHashSet();
        using var package = MEPackageHandler.UnsafePartialLoad(Path.GetFullPath(group.Key), e => names.Contains(e.InstancedFullPath));
        foreach (var export in package.Exports.Where(e => names.Contains(e.InstancedFullPath)))
            Console.WriteLine(JsonSerializer.Serialize(new { source = group.Key, export = export.InstancedFullPath,
                class_name = export.ClassName, int_properties = export.GetProperties().SelectMany(p => Matches(p, p.Name.Instanced)).ToArray() }));
    }
    return;
}
if (args.Length > 1 && (args[0] == "--objects" || args[0] == "--scan-objects"))
{
    var matcher = new Regex(args[1], RegexOptions.IgnoreCase);
    var paths = args[0] == "--scan-objects"
        ? args.Skip(2).SelectMany(root => Directory.EnumerateFiles(root, "*.pcc", SearchOption.AllDirectories))
            .Where(path => !Path.GetFileName(path).Contains("_LOC_", StringComparison.OrdinalIgnoreCase)).Order()
        : args.Skip(2);
    int visited = 0, matched = 0, errors = 0;
    foreach (var path in paths)
    {
        try
        {
        using var package = MEPackageHandler.UnsafePartialLoad(Path.GetFullPath(path), e => matcher.IsMatch(e.ClassName));
        foreach (var export in package.Exports.Where(e => matcher.IsMatch(e.ClassName)))
        {
            if (export.InstancedFullPath.Contains("Default__")) continue;
            Console.WriteLine(JsonSerializer.Serialize(new {
                source = path, export = export.UIndex, class_name = export.ClassName,
                object_path = export.InstancedFullPath,
                properties = export.GetProperties().ToDictionary(p => p.Name.Instanced, p => Project(p, package))
            }));
            matched++;
        }
        }
        catch (Exception error)
        {
            errors++;
            Console.Error.WriteLine($"ERROR {path}: {error.Message}");
        }
        visited++;
        if (visited % 100 == 0) Console.Error.WriteLine($"Scanned {visited} packages; {matched} matching exports; {errors} errors");
    }
    Console.Error.WriteLine($"Finished {visited} packages; {matched} matching exports; {errors} errors");
    Environment.ExitCode = errors == 0 ? 0 : 1;
    return;
}
if (args.Length > 1 && args[0] == "--mounts")
{
    foreach (var path in Directory.EnumerateFiles(args[1], "Mount.dlc", SearchOption.AllDirectories).Order())
    {
        var mount = new MountFile(path);
        Console.WriteLine(JsonSerializer.Serialize(new { source = path, priority = mount.MountPriority, game = mount.Game.ToString() }));
    }
    return;
}
if (args.Length > 2 && args[0] == "--strings")
{
    var ids = JsonSerializer.Deserialize<int[]>(File.ReadAllText(args[1])).ToHashSet();
    foreach (var path in args.Skip(2))
    {
        var tlk = new LegendaryExplorerCore.TLK.ME2ME3.ME2ME3TalkFile(path);
        foreach (var item in tlk.StringRefs.Where(s => ids.Contains(s.StringID)))
            Console.WriteLine(JsonSerializer.Serialize(new { source = path, id = item.StringID, text = item.Data }));
    }
    return;
}
if (args.Length > 2 && args[0] == "--script")
{
    var matcher = new Regex(args[1], RegexOptions.IgnoreCase);
    foreach (var path in args.Skip(2))
    {
        using var package = MEPackageHandler.OpenMEPackage(Path.GetFullPath(path), forceLoadFromDisk: true);
        using var library = new LegendaryExplorerCore.UnrealScript.FileLib(package);
        foreach (var export in package.Exports.Where(e => e.ClassName == "Function" && matcher.IsMatch(e.InstancedFullPath)))
        {
            try
            {
            var (_, text) = LegendaryExplorerCore.UnrealScript.UnrealScriptCompiler.DecompileExport(export, library, null);
            if (text.StartsWith("Error occurred") || text.StartsWith("Could not decompile"))
                throw new InvalidOperationException(text);
            Console.WriteLine(JsonSerializer.Serialize(new { source = path, export = export.UIndex, function = export.InstancedFullPath, text }));
            }
            catch (Exception error)
            {
                Console.Error.WriteLine($"Cannot decompile {export.InstancedFullPath}: {error.Message}");
                Environment.ExitCode = 1;
            }
        }
    }
    return;
}
if (args.Length > 0 && (args[0] == "--config" || args[0] == "--config-matching"))
{
    bool custom = args[0] == "--config-matching";
    var sectionMatcher = new Regex(custom ? args[1] : "GAWAssetsHandler|TreasureData", RegexOptions.IgnoreCase);
    foreach (var path in args.Skip(custom ? 2 : 1))
    {
        using var stream = File.OpenRead(path);
        var files = CoalescedConverter.DecompileGame3ToMemory(stream);
        foreach (var file in files)
        {
            var xml = XDocument.Parse(file.Value);
            foreach (var section in xml.Descendants("Section"))
                if (sectionMatcher.IsMatch((string)section.Attribute("name") ?? ""))
                    Console.WriteLine(System.Text.Json.JsonSerializer.Serialize(new {
                        source = path, file = file.Key, section = section.ToString()
                    }));
        }
    }
    return;
}

static object Project(Property property, IMEPackage package) => property switch
{
    IntProperty p => p.Value,
    BoolProperty p => p.Value,
    FloatProperty p => p.Value,
    NameProperty p => p.Value.Instanced,
    StrProperty p => p.Value,
    StringRefProperty p => p.Value,
    ObjectProperty p => new { index = p.Value, path = package.GetEntry(p.Value)?.InstancedFullPath },
    EnumProperty p => p.Value.Instanced,
    StructProperty p => p.Properties.ToDictionary(v => v.Name.Instanced, v => Project(v, package)),
    ArrayProperty<IntProperty> p => p.Select(v => Project(v, package)).ToArray(),
    ArrayProperty<StructProperty> p => p.Select(v => Project(v, package)).ToArray(),
    ArrayProperty<ObjectProperty> p => p.Select(v => Project(v, package)).ToArray(),
    ArrayProperty<NameProperty> p => p.Select(v => Project(v, package)).ToArray(),
    ArrayProperty<StrProperty> p => p.Select(v => Project(v, package)).ToArray(),
    _ => new { property_type = property.GetType().Name, text = property.ToString() }
};
foreach (var path in args)
{
    using var package = MEPackageHandler.UnsafePartialLoad(Path.GetFullPath(path), _ => false);
    Console.WriteLine($"PACKAGE {path} {package.Game} exports={package.Exports.Count}");
    foreach (var export in package.Exports)
        if (System.Text.RegularExpressions.Regex.IsMatch(export.InstancedFullPath,
            "GAW|WarAsset|Readiness|Codex|Treasure|Medigel|Salvage|GiveItem|Inventory|Store|GalaxyMap", 
            System.Text.RegularExpressions.RegexOptions.IgnoreCase))
            Console.WriteLine($"{export.UIndex}\t{export.ClassName}\t{export.InstancedFullPath}");
}
