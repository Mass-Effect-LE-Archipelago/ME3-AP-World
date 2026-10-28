"""Write the Mass Effect AP Setup app's ME3 option schema (options-me3.json) from the ME3 world's options.

usage: python tools/export_options.py <out file>   (run with the Archipelago venv; uses the synced Archipelago-main copy)
"""
import inspect
import json
import pathlib
import sys


def options_json() -> str:
    from Options import Choice, OptionSet, Range, Toggle
    from worlds.mass_effect_le3 import data, options

    groups = []
    for group in options.option_groups:
        entries = []
        for cls in group.options:
            if cls.__module__ != options.__name__:  # Archipelago's own groups (start inventory, ...) are left out
                continue
            key = next(k for k, v in options.MassEffectLE3Options.type_hints.items() if v is cls)
            entry = {"key": key, "display": getattr(cls, "display_name", key),
                     "doc": inspect.cleandoc(cls.__doc__ or "")}
            if issubclass(cls, Toggle):
                entry.update(type="toggle", default=bool(cls.default))
            elif issubclass(cls, Choice):
                entry.update(type="choice", default=cls.name_lookup[cls.default],
                             choices=[cls.name_lookup[v] for v in sorted(cls.name_lookup)])
            elif issubclass(cls, Range):
                entry.update(type="range", default=cls.default, min=cls.range_start, max=cls.range_end)
            elif issubclass(cls, OptionSet):
                entry.update(type="set", default=sorted(cls.default), choices=sorted(cls.valid_keys))
            else:
                raise TypeError(f"{key}: unsupported option type {cls.__mro__[1].__name__}")
            entries.append(entry)
        if entries:
            groups.append({"name": group.name, "options": entries})
    meta = json.loads((pathlib.Path(options.__file__).parent / "archipelago.json").read_text(encoding="utf-8-sig"))
    return json.dumps({"game": data.GAME_NAME, "world_version": meta["world_version"],
                       "minimum_ap_version": meta["minimum_ap_version"], "groups": groups,
                       "presets": options.options_presets}, indent=1) + "\n"


if __name__ == "__main__":
    root = pathlib.Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "Archipelago-main"))
    import ModuleUpdate
    ModuleUpdate.update_ran = True
    out = pathlib.Path(sys.argv[1])
    out.write_text(options_json(), newline="\n")
    print(out)
