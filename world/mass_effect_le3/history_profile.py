"""Resolved seed-history schema and an offline native-bundle compilation preview.

Production generation does not expose these options yet. Source coverage and
runtime initialization are separate from validating a player's requested story.
"""
from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
import json
from typing import Mapping

PROFILE_VERSION = 1
SQUAD = ("miranda", "jacob", "garrus", "mordin", "grunt", "jack", "thane",
         "tali", "legion", "mystic", "kasumi", "zaeed")


@dataclass(frozen=True)
class ChoiceSpec:
    values: tuple[str | bool, ...]
    default: str | bool


CHOICES = {
    "shepard.origin": ChoiceSpec(("spacer", "colonist", "earthborn"), "spacer"),
    "shepard.service_history": ChoiceSpec(("sole_survivor", "war_hero", "ruthless"), "war_hero"),
    "me1.virmire_survivor": ChoiceSpec(("ashley", "kaidan"), "ashley"),
    "me1.wrex": ChoiceSpec(("alive", "dead", "never_recruited"), "alive"),
    "me1.rachni": ChoiceSpec(("saved", "killed"), "saved"),
    "me1.council": ChoiceSpec(("saved", "sacrificed"), "saved"),
    "me1.human_councilor": ChoiceSpec(("anderson", "udina"), "anderson"),
    "me1.romance": ChoiceSpec(("none", "ashley", "kaidan", "liara"), "none"),
    "me2.collector_base": ChoiceSpec(("destroyed", "preserved"), "destroyed"),
    "me2.heretics": ChoiceSpec(("destroyed", "rewritten", "not_completed"), "destroyed"),
    "me2.maelon_data": ChoiceSpec(("saved", "destroyed", "not_completed"), "saved"),
    "me2.crew_rescue": ChoiceSpec(("all_saved", "half_saved", "doctor_only"), "all_saved"),
    "me2.mystic_identity": ChoiceSpec(("samara", "morinth", "none"), "samara"),
    "me2.romance": ChoiceSpec(("none", "miranda", "garrus", "jacob", "thane", "jack", "tali"), "none"),
    "me2.liara_relationship": ChoiceSpec(("not_set", "continued", "ended"), "not_set"),
}
for _member in SQUAD:
    for _fact in ("recruited", "survived", "loyal"):
        CHOICES[f"me2.squad.{_member}.{_fact}"] = ChoiceSpec((False, True), True)


def _validate(choices: Mapping) -> dict[str, str | bool]:
    if not isinstance(choices, Mapping): raise ValueError("History choices must be a mapping")
    unknown = choices.keys() - CHOICES.keys()
    missing = CHOICES.keys() - choices.keys()
    if unknown or missing:
        raise ValueError(f"History keys: unknown={sorted(unknown, key=str)}, missing={sorted(missing)}")
    resolved = dict(choices)
    for key, value in resolved.items():
        spec = CHOICES[key]
        if not any(type(value) is type(candidate) and value == candidate for candidate in spec.values):
            raise ValueError(f"Invalid history value for {key}: {value!r}; expected {spec.values}")
    for member in SQUAD:
        recruited = resolved[f"me2.squad.{member}.recruited"]
        if not recruited and (resolved[f"me2.squad.{member}.survived"] or resolved[f"me2.squad.{member}.loyal"]):
            raise ValueError(f"{member}: survival/loyalty requires recruitment")
    mystic_recruited = resolved["me2.squad.mystic.recruited"]
    if mystic_recruited == (resolved["me2.mystic_identity"] == "none"):
        raise ValueError("Mystic identity must agree with Samara/Morinth recruitment")
    romance = resolved["me2.romance"]
    if romance != "none" and not resolved[f"me2.squad.{romance}.recruited"]:
        raise ValueError(f"{romance}: a past romance requires recruitment")
    # A later death does not erase the fact of a past relationship or loyalty.
    # Sex/romance compatibility and Liara DLC timeline rules need native mapping;
    # do not invent restrictions or claim complete game-history validation here.
    return resolved


@dataclass(frozen=True)
class ResolvedHistory:
    preset: str
    version: int
    choices: tuple[tuple[str, str | bool], ...]

    def to_slot_data(self) -> dict:
        return {"preset": self.preset, "version": self.version, "choices": dict(self.choices),
                "implemented_in_game": False}


def resolve_history(preset: str = "maximum_content", overrides: Mapping | None = None) -> ResolvedHistory:
    """Resolve a preset plus explicit choices once, before eventual seed placement.

    Maximum-content currently means the proposed all-recruited/alive/loyal preset;
    it is not a verified check-count optimum. Selecting overrides labels it custom.
    """
    if preset not in ("maximum_content", "custom"): raise ValueError("Unknown history preset")
    if overrides is None: overrides = {}
    if not isinstance(overrides, Mapping): raise ValueError("History overrides must be a mapping")
    resolved = {key: spec.default for key, spec in CHOICES.items()}
    resolved.update(overrides)
    resolved = _validate(resolved)
    return ResolvedHistory("custom" if overrides else preset, PROFILE_VERSION, tuple(sorted(resolved.items())))


def parse_resolved_history(payload: dict) -> ResolvedHistory:
    """Validate a complete serialized profile; never fill absent saved choices."""
    if not isinstance(payload, dict) or payload.get("preset") not in ("maximum_content", "custom"):
        raise ValueError("Invalid resolved history profile")
    if payload.keys() - {"preset", "version", "choices", "implemented_in_game"}:
        raise ValueError("Unknown resolved history fields")
    if type(payload.get("version")) is not int or payload["version"] != PROFILE_VERSION:
        raise ValueError("Unsupported history profile version")
    choices = _validate(payload.get("choices"))
    if payload["preset"] == "maximum_content" and any(choices[key] != spec.default for key, spec in CHOICES.items()):
        raise ValueError("Modified maximum-content profile must be labeled custom")
    return ResolvedHistory(payload["preset"], PROFILE_VERSION, tuple(sorted(choices.items())))


def compile_history_preview(profile: ResolvedHistory, *, bundles: dict | None = None) -> dict:
    """Compile reviewed source recipes and report every missing mapping.

    No broad Genesis reset, crew/survival-changing romance shortcut, or generic
    plot write is substituted for an unsupported requested choice. The resulting
    artifact is deliberately non-executable until initialization is implemented.
    """
    profile = parse_resolved_history(profile.to_slot_data())
    if bundles is None:
        bundles = json.loads(files(__package__).joinpath("history_bundles.json").read_text(encoding="utf-8"))
    if bundles.get("schema") != 1 or bundles.get("status") != "source_mapped_runtime_unverified":
        raise ValueError("Unsupported history bundle resource")
    recipes = bundles["recipes"]
    actions, missing = [], {}
    # Clear alternatives first; a selected romance setter only sets its partner.
    clear = recipes["me1.romance"]["none"]
    actions.append({"decision": "me1.romance.clear", **clear})
    for key, value in profile.choices:
        recipe = recipes.get(key, {}).get(value) if type(value) is str else None
        if recipe is None:
            missing[key] = value
        elif key != "me1.romance" or value != "none":
            actions.append({"decision": key, **recipe})
    target_bools, target_ints = {}, {}
    for action in actions:
        for element in action["elements"]:
            if element.get("UseParam") or element.get("Increment"):
                raise ValueError("Unreviewed parameter/increment in history recipe")
            if element["Type"] in (0, 8): target_bools[str(element["GlobalBool"])] = element["NewState"]
            elif element["Type"] == 4: target_ints[str(element["GlobalInt"])] = element["NewValue"]
            else: raise ValueError("Unreviewed history element type")
    return {"schema": 1, "profile": profile.to_slot_data(), "executable": False,
            "status": "offline_partial_source_plan", "required_map": bundles["required_map"],
            "actions": actions, "unmapped_choices": missing,
            "expected_direct_targets": {"bools": target_bools, "ints": target_ints},
            "limitations": ["Native career hook, ordering, map availability and side effects unverified",
                            "Direct targets omit native parent/substate processing; retain complete elements",
                            "Additional romance/identity/timeline compatibility remains unmapped",
                            "History-dependent check filtering is not implemented"]}
