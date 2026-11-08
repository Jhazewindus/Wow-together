#!/usr/bin/env python3
"""Compare two exported quest catalogues and write a guide-focused Markdown diff."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ("level", "minLevel", "side", "raceMask", "classMask", "starts", "ends",
          "prerequisites", "previousQuest", "prerequisiteAll", "prerequisiteAny", "objectives")


def quest_rows(document: dict) -> dict[int, dict]:
    rows = document.get("quests", {})
    if isinstance(rows, list):
        return {int(row["id"] if "id" in row else row["questID"]): row for row in rows}
    if isinstance(rows, dict):
        return {int(key): value for key, value in rows.items()}
    raise ValueError("catalogue JSON must contain a quests object or list")


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _guides_for(quest: dict, guides: list[dict]) -> list[str]:
    zone = str(quest.get("zone") or quest.get("categoryPath") or "").split("/")[-1].replace("-", " ").casefold()
    side = quest.get("side")
    level = quest.get("level")
    found = []
    for guide in guides:
        if str(guide.get("zone", "")).casefold() != zone:
            continue
        if side in ("Alliance", "Horde") and guide.get("faction") != side:
            continue
        bracket = re.search(r"levels:(\d+)-(\d+)", guide.get("key", ""))
        if bracket and isinstance(level, (int, float)):
            low, high = map(int, bracket.groups())
            if level < low - 8 or level > high + 8:
                continue
        found.append(f"{guide.get('faction', 'All')}: {guide.get('zone')} ({guide.get('key')})")
    return found


def _stage_points(quest: dict):
    for role in ("starts", "ends", "objectives"):
        points = quest.get(role) or []
        if isinstance(points, dict):
            points = points.values()
        for point in points:
            if isinstance(point, dict) and isinstance(point.get("mapID"), int):
                yield role, point


def _moved_npcs(old_q: dict, new_q: dict, old_doc: dict, new_doc: dict) -> list[str]:
    before = {}
    for role, point in _stage_points(old_q):
        ident = point.get("entityID")
        if ident and (point.get("npc") or point.get("entityType") == "npc"):
            before[(role, ident, point["mapID"])] = point
    sizes = new_doc.get("mapWorldSizes") or old_doc.get("mapWorldSizes") or new_doc.get("mapSizes") or old_doc.get("mapSizes") or {}
    moved = []
    for role, point in _stage_points(new_q):
        ident = point.get("entityID")
        old = before.get((role, ident, point["mapID"]))
        if not ident or not old or not (point.get("npc") or point.get("entityType") == "npc"):
            continue
        if not all(isinstance(p.get(axis), (int, float)) for p in (old, point) for axis in ("x", "y")):
            continue
        size = sizes.get(str(point["mapID"]), sizes.get(point["mapID"]))
        if not isinstance(size, dict) or not isinstance(size.get("width"), (int, float)) or not isinstance(size.get("height"), (int, float)):
            continue  # No scale means a yard threshold cannot be claimed.
        yards = (((point["x"] - old["x"]) * size["width"]) ** 2
                 + ((point["y"] - old["y"]) * size["height"]) ** 2) ** 0.5
        if yards > 50:
            moved.append(f"NPC {ident} moved {yards:.0f} yd on map {point['mapID']}")
    return moved


def diff(old: dict, new: dict, guide_audit: dict | None = None) -> list[dict]:
    before, after = quest_rows(old), quest_rows(new)
    guides = (guide_audit or {}).get("guides", [])
    changes = []
    for quest_id in sorted(before.keys() | after.keys()):
        if quest_id not in before:
            q = after[quest_id]
            changes.append({"questID": quest_id, "title": q.get("title", f"Quest {quest_id}"),
                            "change": "added", "guides": _guides_for(q, guides)})
            continue
        if quest_id not in after:
            q = before[quest_id]
            changes.append({"questID": quest_id, "title": q.get("title", f"Quest {quest_id}"),
                            "change": "removed", "guides": _guides_for(q, guides)})
            continue
        old_q, new_q = before[quest_id], after[quest_id]
        touched = [field for field in FIELDS if _canonical(old_q.get(field)) != _canonical(new_q.get(field))]
        moves = _moved_npcs(old_q, new_q, old, new)
        if touched or moves:
            description = "fields changed: " + ", ".join(touched) if touched else ""
            description = "; ".join(filter(None, [description, *moves]))
            changes.append({"questID": quest_id, "title": new_q.get("title", old_q.get("title", f"Quest {quest_id}")),
                            "change": description,
                            "guides": _guides_for(new_q, guides)})
    return changes


def render(changes: list[dict], old: dict, new: dict) -> str:
    lines = ["# Catalogue diff", "", f"Old capture: {old.get('captured', 'unknown')}  ",
             f"New capture: {new.get('captured', 'unknown')}", ""]
    if not changes:
        lines += ["No quest changes found.", ""]
    for item in changes:
        guides = "; ".join(item["guides"]) or "No matching fixed guide identified"
        lines.append(f"- **{item['questID']} — {item['title']}**: {item['change']}. Guides: {guides}.")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("old", type=Path)
    parser.add_argument("new", type=Path)
    parser.add_argument("--guide-audit", type=Path, default=ROOT / "WowTogether" / "GuideAudit.json")
    parser.add_argument("--output", type=Path, default=Path("CatalogueDiff.md"))
    args = parser.parse_args()
    old = json.loads(args.old.read_text(encoding="utf-8"))
    new = json.loads(args.new.read_text(encoding="utf-8"))
    audit = json.loads(args.guide_audit.read_text(encoding="utf-8")) if args.guide_audit.exists() else {}
    changes = diff(old, new, audit)
    args.output.write_text(render(changes, old, new), encoding="utf-8")
    print(f"Wrote {len(changes)} quest change(s) to {args.output}")


if __name__ == "__main__":
    main()
