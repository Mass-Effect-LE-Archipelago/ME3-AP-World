"""Index retained Genesis transition bundles without flattening native substates.

Consumes read-only Le3Probe exports. Does not patch packages or create playable
history options: retained DLC data does not prove reachability in Legendary Edition.
"""
from __future__ import annotations

from collections import Counter
import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / "research"
CHOICES = {
    "me1.romance": {"ashley": 5597, "kaidan": 5598, "liara": 5599, "none": 5600},
    "me1.rachni": {"killed": 5610, "saved": 5611},
    "me1.wrex": {"dead": 5612, "alive": 5613},
    "me1.virmire_survivor": {"kaidan": 5614, "ashley": 5615},
    "me1.council": {"saved": 5616, "sacrificed": 5617},
    "me1.human_councilor": {"udina": 5618, "anderson": 5619},
    "me2.collector_base": {"preserved": 5763, "destroyed": 5764},
}


def json_lines(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines()]


def build():
    inputs = [RESEARCH / name for name in (
        "le3_history_state_events.jsonl", "le3_genesis_chapters.jsonl",
        "le3_genesis_all_texts.jsonl", "le3_plot_inventory.csv")]
    with inputs[3].open(encoding="utf-8", newline="") as stream:
        database = {(r["family"], int(r["plot_id"])): r["path"] for r in csv.DictReader(stream)}
    maps = [r for r in json_lines(inputs[0]) if r["class_name"] == "BioStateEventMap"
            and "DLC_CON_DH1" in r["source"]]
    if len(maps) != 1: raise ValueError("Expected exactly one retained Genesis state-event map")
    source = maps[0]
    events = source["data"]["StateEvents"]
    if len({e["ID"] for e in events}) != len(events): raise ValueError("Duplicate Genesis transition IDs")
    text_lookup = {}
    for row in json_lines(inputs[2]):
        text_lookup.setdefault(row["id"], set()).add(row["text"])
    dialogue_refs = {}
    for row in json_lines(inputs[1]):
        if row["class_name"] != "BioConversation": continue
        for family in ("m_EntryList", "m_ReplyList"):
            for index, node in enumerate(row["properties"].get(family, [])):
                transition = node.get("nStateTransition", -1)
                if transition <= 0: continue
                text_id = node.get("srText", 0)
                dialogue_refs.setdefault(transition, []).append({
                    "source": row["source"], "conversation_export": row["export"],
                    "conversation": row["object_path"], "node_family": family, "node_index": index,
                    "text_id": text_id, "texts": sorted(text_lookup.get(text_id, ())),
                    "transition_parameter": node.get("nStateTransitionParam"),
                })
    labels = {transition: (key, choice) for key, choices in CHOICES.items() for choice, transition in choices.items()}
    catalog, types = [], Counter()
    for event in events:
        elements = []
        for element in event["Elements"]:
            kind = element["Type"]
            types[kind] += 1
            if kind not in (0, 4, 8): raise ValueError(f"Unreviewed Genesis element type: {kind}")
            if element.get("UseParam"): raise ValueError("Parameterized transition needs a reviewed argument")
            if kind == 4 and element.get("Increment"): raise ValueError("Incrementing history transition needs ordering review")
            family = "ints" if kind == 4 else "bools"
            index = element["GlobalInt"] if kind == 4 else element["GlobalBool"]
            related = [{"role": "target", "family": family, "index": index,
                        "path": database[(family, index)]}]
            if kind == 8:
                # Keep parent/sibling metadata verbatim. Writing just GlobalBool
                # would silently lose the native substate operation's semantics.
                for role, indices in (("parent", [element["ParentIndex"]]),
                                      ("sibling", element["SiblingIndices"])):
                    related.extend({"role": role, "family": "bools", "index": i,
                                    "path": database[("bools", i)]} for i in indices)
            elements.append({"native": element, "plots": related})
        decision = labels.get(event["ID"])
        catalog.append({"id": event["ID"], "decision": {"key": decision[0], "value": decision[1]} if decision else None,
                        "elements": elements, "dialogue_refs": dialogue_refs.get(event["ID"], [])})
    missing_choices = labels.keys() - {e["id"] for e in catalog}
    if missing_choices: raise ValueError(f"Choice transitions missing: {missing_choices}")
    # These two independent vanilla setters must agree exactly.
    by_id = {e["ID"]: e for e in events}
    for transition, expected in (
        (5614, {13827: False, 13828: True, 13940: False, 13939: True}),
        (5615, {13827: True, 13828: False, 13940: True, 13939: False}),
    ):
        actual = {e["GlobalBool"]: e["NewState"] for e in by_id[transition]["Elements"] if e["Type"] == 0}
        if actual != expected: raise ValueError("Genesis and new-character Virmire setters disagree")
    return {"schema": 1, "status": "retained_vanilla_bundle_reference_not_runtime_verified",
            "source": {k: source[k] for k in ("source", "export", "object_path")},
            "required_map": "PlotManagerAutoDLC_CON_DH1.StateTransitionMap",
            "constraints": ["Fresh-career ordering and map availability need runtime verification",
                            "Do not flatten substate elements into raw bool writes",
                            "Romance choices rely on clearing previous alternatives before selection",
                            "Reset event 5915 also clears broad ME2 state; never apply as an isolated ME1 reset",
                            "Unresolved dialogue text and retained branches do not prove LE3 reachability"],
            "counts": {"transitions": len(catalog), "elements": sum(types.values()),
                       "element_types": dict(sorted(types.items())), "labeled_choices": len(labels),
                       "labeled_me1_choices": sum(key.startswith("me1.") for key, _ in labels.values()),
                       "transitions_with_dialogue_refs": sum(bool(e["dialogue_refs"]) for e in catalog),
                       "transitions_with_resolved_dialogue": sum(any(r["texts"] for r in e["dialogue_refs"]) for e in catalog)},
            "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
            "transitions": catalog}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sync-world", action="store_true", help="Export annotated source recipes for the offline profile compiler")
    args = parser.parse_args()
    result = build()
    output = RESEARCH / "le3_genesis_transition_catalog.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["counts"], indent=2))
    print(output)
    if args.sync_world:
        recipes = {}
        for transition in result["transitions"]:
            decision = transition["decision"]
            if decision is None: continue
            recipes.setdefault(decision["key"], {})[decision["value"]] = {
                "transition": transition["id"], "elements": [e["native"] for e in transition["elements"]]}
        resource = {"schema": 1, "status": "source_mapped_runtime_unverified",
                    "required_map": result["required_map"], "source": result["source"],
                    "source_sha256": result["source_sha256"], "recipes": recipes}
        target = ROOT / "world/mass_effect_le3/history_bundles.json"
        target.write_text(json.dumps(resource, indent=2) + "\n", encoding="utf-8")
        print(target)
