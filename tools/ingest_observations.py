#!/usr/bin/env python3
"""Turn tester research exports into review-only quest correction candidates."""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "tools" / "correction_candidates.json"
DEFAULT_CORRECTIONS = ROOT / "tools" / "quest_corrections.json"


def observer_for(event: dict, source: Path) -> str:
    # The game export omits names by default. An explicitly opted-in character
    # label is retained; otherwise the export filename is a private tester key.
    return str(event.get("character") or event.get("observerID") or source.stem)


def load_exports(paths: list[Path]) -> list[dict]:
    events = []
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("format") != "wow-together-quest-research" or data.get("schema") != 1:
            raise ValueError(f"unsupported research export: {path}")
        for event in data.get("events", []):
            if isinstance(event, dict):
                value = dict(event)
                value["_observer"] = observer_for(event, path)
                value["_source_file"] = path.name
                events.append(value)
    return events


def _distance(a: dict, b: dict) -> float:
    # Public map coordinates are normalized. This conservative local radius is
    # only a grouping aid; it never writes an exact game-world yard claim.
    return (((a["x"] - b["x"]) * 1.4) ** 2 + (a["y"] - b["y"]) ** 2) ** 0.5


def _cluster(rows: list[dict], threshold: float) -> list[list[dict]]:
    groups: list[list[dict]] = []
    for row in sorted(rows, key=lambda item: (item["mapID"], item["x"], item["y"], item["_observer"])):
        group = next((g for g in groups if g[0]["mapID"] == row["mapID"] and
                      _distance(g[0], row) <= threshold), None)
        if group is None:
            groups.append([row])
        else:
            group.append(row)
    return groups


def _source(rows: list[dict], statement: str) -> str:
    builds = sorted({str(row.get("build", "unknown")) for row in rows})
    people = sorted({str(row["_observer"]) for row in rows})
    profiles = sorted({"/".join(str(row.get(key, "unknown")) for key in ("classID", "raceID", "level"))
                       for row in rows})
    return (f"{statement}; observed by {', '.join(people)} on client build(s) "
            f"{', '.join(builds)}; class/race/level profiles {', '.join(profiles)}; "
            f"source exports {', '.join(sorted({row['_source_file'] for row in rows}))}.")


def _candidate(kind: str, quest_id: int, rows: list[dict], facts: dict, statement: str) -> dict:
    sessions = sorted({f"{row['_observer']}:{row.get('session', 0)}" for row in rows})
    builds = sorted({str(row.get("build", "unknown")) for row in rows})
    observers = sorted({row["_observer"] for row in rows})
    source = _source(rows, statement)
    token = json.dumps([kind, quest_id, facts, observers, sessions, builds], sort_keys=True)
    return {"id": hashlib.sha256(token.encode()).hexdigest()[:16], "kind": kind,
            "questID": quest_id, "title": next((r.get("title") for r in rows if r.get("title")), f"Quest {quest_id}"),
            "facts": facts, "source": source,
            "confidence": {"observers": len(observers), "observerLabels": observers,
                           "sessions": len(sessions), "builds": builds},
            "conflictsWith": []}


def _valid_position(row: dict) -> bool:
    return (isinstance(row.get("questID"), int) and row["questID"] > 0
            and isinstance(row.get("mapID"), int) and row["mapID"] > 0
            and isinstance(row.get("x"), (int, float)) and isinstance(row.get("y"), (int, float))
            and 0 <= row["x"] <= 1 and 0 <= row["y"] <= 1)


def _existing_conflicts(kind: str, facts: dict, corrections: list[dict]) -> list[str]:
    conflicts = []
    for row in corrections:
        if row.get("questID") != facts.get("questID"):
            continue
        rule = row.get("stageCorrection", {})
        if kind == "npc-location" and rule.get("kind") == "npc-location":
            old = rule.get("after")
            if isinstance(old, dict) and old.get("mapID") == facts.get("mapID"):
                if abs(old.get("x", 0) - facts.get("x", 0)) > 0.0001 or abs(old.get("y", 0) - facts.get("y", 0)) > 0.0001:
                    conflicts.append(f"reviewed NPC location differs at {old.get('x')},{old.get('y')} on map {old['mapID']}")
        elif kind == "objective-facts" and rule.get("kind") == "objective-facts":
            conflicts.append("reviewed objective facts already exist")
        elif kind == "offer-fact" and any(row.get(key) for key in
                ("previousQuest", "prerequisiteAll", "prerequisiteAny", "prerequisiteCorrection")):
            conflicts.append("reviewed prerequisite facts already exist")
    return sorted(set(conflicts))


def ingest(events: list[dict], corrections: list[dict] | None = None) -> dict:
    corrections = corrections or []
    candidates = []
    pickups: dict[tuple, list[dict]] = defaultdict(list)
    areas: dict[tuple, list[dict]] = defaultdict(list)
    offers: dict[tuple, list[dict]] = defaultdict(list)
    skips: dict[int, list[dict]] = defaultdict(list)
    for row in events:
        kind = row.get("event")
        if kind == "pickup-location" and _valid_position(row):
            pickups[(row["questID"], row["build"], row["mapID"])].append(row)
        elif kind == "objective-area" and _valid_position(row) and isinstance(row.get("objectiveIndex"), int):
            areas[(row["questID"], row["objectiveIndex"], row["build"], row["mapID"])].append(row)
        elif kind == "offers" and isinstance(row.get("npcID"), int):
            offers[(row["npcID"], row.get("build"))].append(row)
        elif kind in ("skip-step", "skip-quest") and isinstance(row.get("questID"), int):
            skips[row["questID"]].append(row)

    for (quest_id, build, map_id), rows in sorted(pickups.items()):
        for group in _cluster(rows, 0.012):
            if len(group) < 2:
                continue
            facts = {"build": build, "mapID": map_id,
                     "x": statistics.median(r["x"] for r in group),
                     "y": statistics.median(r["y"] for r in group),
                     "npcIDs": sorted({r["npcID"] for r in group if isinstance(r.get("npcID"), int)}),
                     "observations": len(group)}
            candidate = _candidate("npc-location", quest_id, group, facts,
                "NPC pickup position median from at least two nearby observations")
            candidate["conflictsWith"] = _existing_conflicts("npc-location", {**facts, "questID": quest_id}, corrections)
            candidates.append(candidate)

    for (quest_id, index, build, map_id), rows in sorted(areas.items()):
        for group in _cluster(rows, 0.012):
            observers = {r["_observer"] for r in group}
            sessions = {(r["_observer"], r.get("session", 0)) for r in group}
            if sum(max(1, int(r.get("n", 1))) for r in group) < 3 or (len(observers) < 2 and len(sessions) < 2):
                continue
            facts = {"build": build, "objectiveIndex": index, "mapID": map_id,
                     "x": statistics.median(r["x"] for r in group),
                     "y": statistics.median(r["y"] for r in group),
                     "samples": sum(max(1, int(r.get("n", 1))) for r in group)}
            candidate = _candidate("objective-facts", quest_id, group, facts,
                "Objective location cluster observed on multiple characters or sessions")
            candidate["conflictsWith"] = _existing_conflicts("objective-facts", {**facts, "questID": quest_id}, corrections)
            candidates.append(candidate)

    offer_groups: dict[tuple, list[dict]] = defaultdict(list)
    for (npc_id, build), rows in sorted(offers.items()):
        for event in rows:
            if event.get("completeList") is not True:
                continue
            completed = set(event.get("completed", []))
            offered = set(event.get("offered", []))
            absent = set(event.get("notCompleted", []))
            for quest_id in sorted(offered):
                offer_groups[(npc_id, build, quest_id, True, tuple(sorted(completed)))].append(event)
            for quest_id in sorted(absent - offered):
                if completed:
                    offer_groups[(npc_id, build, quest_id, False, tuple(sorted(completed)))].append(event)
    for (npc_id, build, quest_id, offered, completed), rows in sorted(offer_groups.items()):
        facts = {"npcID": npc_id, "build": build, "offered": offered,
                 "completedAtOffer": list(completed),
                 "availabilityClaim": "review-prerequisite-free" if offered and not completed else "review-chain-or-offer"}
        candidate = _candidate("offer-fact", quest_id, rows, facts,
            (f"Quest was offered by NPC {npc_id} with no recorded quest completions; review prerequisite requirements"
             if offered and not completed else f"Quest was offered by NPC {npc_id}" if offered else
             f"Quest was absent from NPC {npc_id}'s complete offer list after recorded hand-ins"))
        candidate["conflictsWith"] = _existing_conflicts("offer-fact", {**facts, "questID": quest_id}, corrections)
        candidates.append(candidate)

    for quest_id, rows in sorted(skips.items()):
        observers = {r["_observer"] for r in rows}
        if len(observers) >= 3:
            facts = {"skipEvents": len(rows), "observers": len(observers)}
            candidates.append(_candidate("skip-signal", quest_id, rows, facts,
                "Quest was skipped by multiple testers; review only, never exclude automatically"))
    return {"format": "wow-together-correction-candidates", "schema": 1,
            "candidateCount": len(candidates), "candidates": candidates}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exports", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    corrections = json.loads((ROOT / "tools" / "quest_corrections.json").read_text(encoding="utf-8"))
    result = ingest(load_exports(args.exports), corrections)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {result['candidateCount']} review candidate(s) to {args.output}")


if __name__ == "__main__":
    main()
