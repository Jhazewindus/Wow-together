#!/usr/bin/env python3
"""Copy sufficiently corroborated, non-conflicting observations to review corrections."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def position_conflicts(candidate: dict, correction: dict) -> list[str]:
    facts = candidate.get("facts", {})
    rule = correction.get("stageCorrection", {})
    conflicts = []
    if candidate.get("kind") == "npc-location":
        for role in rule.get("roles", []):
            old = rule.get("after")
            if isinstance(old, dict) and old.get("mapID") == facts.get("mapID"):
                delta = (((old.get("x", 0) - facts.get("x", 0)) * 1.4) ** 2
                         + (old.get("y", 0) - facts.get("y", 0)) ** 2) ** 0.5
                if delta > 0.0001:
                    conflicts.append(f"existing {role} correction at map {old['mapID']} ({old.get('x')}, {old.get('y')})")
    elif candidate.get("kind") == "objective-facts" and rule.get("kind") == "objective-facts":
        conflicts.append("quest already has a reviewed objective-facts correction")
    elif candidate.get("kind") == "offer-fact" and (correction.get("previousQuest")
            or correction.get("prerequisiteAll") or correction.get("prerequisiteAny")
            or correction.get("prerequisitesUnverified")):
        conflicts.append("offer evidence intersects existing prerequisite facts")
    return conflicts


def promote(candidate_doc: dict, corrections: list[dict], min_observers: int) -> tuple[list[dict], list[str]]:
    by_id = {row.get("questID"): row for row in corrections}
    existing_ids = {row.get("promotedFrom") for row in corrections if row.get("promotedFrom")}
    result, conflicts = list(corrections), []
    for candidate in candidate_doc.get("candidates", []):
        if candidate.get("id") in existing_ids:
            continue
        confidence = candidate.get("confidence", {})
        if int(confidence.get("observers", 0)) < min_observers:
            continue
        existing = by_id.get(candidate.get("questID"), {})
        conflict = list(candidate.get("conflictsWith", [])) + position_conflicts(candidate, existing)
        if conflict:
            conflicts.append(f"Quest {candidate.get('questID')} {candidate.get('title')}: " + "; ".join(conflict))
            continue
        result.append({"questID": candidate["questID"], "title": candidate.get("title"),
                       "source": candidate["source"], "promotedFrom": candidate["id"],
                       "observationCandidate": {key: candidate[key] for key in
                           ("id", "kind", "facts", "confidence", "conflictsWith") if key in candidate}})
        existing_ids.add(candidate.get("id"))
    return result, conflicts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, default=ROOT / "tools" / "correction_candidates.json")
    parser.add_argument("--corrections", type=Path, default=ROOT / "tools" / "quest_corrections.json")
    parser.add_argument("--min-observers", type=int, default=2)
    args = parser.parse_args()
    if args.min_observers < 1:
        parser.error("--min-observers must be positive")
    candidates = json.loads(args.candidates.read_text(encoding="utf-8"))
    corrections = json.loads(args.corrections.read_text(encoding="utf-8"))
    result, conflicts = promote(candidates, corrections, args.min_observers)
    promoted = len(result) - len(corrections)
    if promoted:
        args.corrections.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Added {promoted} review-only correction record(s). No observation was applied to the addon dataset.")
    for conflict in conflicts:
        print("CONFLICT: " + conflict)


if __name__ == "__main__":
    main()
