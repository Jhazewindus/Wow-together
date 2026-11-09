#!/usr/bin/env python3
"""Turn measured Gold exports into review candidates; never promote them automatically."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


EVENTS = {"gold-drop", "gold-node", "gold-run"}


def positive(value: object) -> bool:
    return type(value) is int and value > 0


def finite(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def load_exports(paths: list[Path]) -> list[dict]:
    events = []
    for path in paths:
        document = json.loads(path.read_text(encoding="utf-8"))
        if document.get("format") != "wow-together-quest-research" or document.get("schema") != 1:
            raise ValueError(f"unsupported research export: {path}")
        for event in document.get("events", []):
            if isinstance(event, dict) and event.get("event") in EVENTS:
                row = dict(event)
                row["_observer"] = str(event.get("observerID") or path.stem)
                row["_file"] = path.name
                events.append(row)
    return events


def valid(row: dict) -> bool:
    if not isinstance(row.get("build"), str) or not row["build"]:
        return False
    if not isinstance(row.get("provenance"), str) or not row["provenance"]:
        return False
    if not positive(row.get("sampleSize")):
        return False
    kind = row["event"]
    if kind == "gold-drop":
        return (positive(row.get("npcID")) and positive(row.get("itemID"))
                and positive(row.get("looted")) and positive(row.get("n"))
                and positive(row.get("total")) and row["n"] <= row["looted"]
                and row["total"] >= row["n"] and row["sampleSize"] == row["looted"])
    if kind == "gold-node":
        return (positive(row.get("mapID")) and positive(row.get("spellID"))
                and finite(row.get("x")) and finite(row.get("y"))
                and 0 <= row["x"] <= 1 and 0 <= row["y"] <= 1
                and isinstance(row.get("items"), list))
    if kind == "gold-run":
        return (positive(row.get("dungeonID")) and finite(row.get("durationSeconds"))
                and row["durationSeconds"] > 0 and finite(row.get("lootCopper"))
                and row["lootCopper"] >= 0 and positive(row.get("memberCount")))
    return False


def candidate(kind: str, key: tuple, facts: dict, rows: list[dict]) -> dict:
    observers = sorted({row["_observer"] for row in rows})
    sources = sorted({row["_file"] for row in rows})
    provenance = sorted({row["provenance"] for row in rows})
    token = json.dumps((kind, key, observers), sort_keys=True)
    return {"id": hashlib.sha256(token.encode()).hexdigest()[:16], "kind": kind,
            "facts": facts, "sampleSize": facts["sampleSize"],
            "provenance": provenance,
            "confidence": {"observers": len(observers), "observerIDs": observers,
                           "basis": "measured local play; review only"},
            "sourceExports": sources}


def latest_by_observer(rows: list[dict]) -> list[dict]:
    latest = {}
    for row in rows:
        observer = row["_observer"]
        if observer not in latest or row["sampleSize"] > latest[observer]["sampleSize"]:
            latest[observer] = row
    return list(latest.values())


def ingest(events: list[dict]) -> dict:
    groups = defaultdict(list)
    for row in events:
        if row.get("event") not in EVENTS or not valid(row):
            continue
        kind, build = row["event"], row["build"]
        if kind == "gold-drop":
            key = (build, row["npcID"], row["itemID"])
        elif kind == "gold-node":
            # Same map, profession spell and nearby coordinates form a review cluster.
            key = (build, row["mapID"], row["spellID"], round(row["x"] / .02),
                   round(row["y"] / .02))
        else:
            key = (build, row["dungeonID"], row["memberCount"])
        groups[(kind, key)].append(row)

    candidates = []
    for (kind, key), rows in sorted(groups.items()):
        if kind == "gold-drop":
            unique = latest_by_observer(rows)
            facts = {"build": key[0], "npcID": key[1], "itemID": key[2],
                     "looted": sum(row["looted"] for row in unique),
                     "n": sum(row["n"] for row in unique),
                     "total": sum(row["total"] for row in unique),
                     "sampleSize": sum(row["sampleSize"] for row in unique)}
            facts["dropRate"] = facts["n"] / facts["looted"]
        elif kind == "gold-node":
            unique = latest_by_observer(rows)
            item_totals = defaultdict(int)
            item_sources = defaultdict(set)
            for row in unique:
                for item in row["items"]:
                    if isinstance(item, dict) and positive(item.get("itemID")) and positive(item.get("total")):
                        item_totals[item["itemID"]] += item["total"]
                        item_sources[item["itemID"]].add(str(item.get("provenance") or row["provenance"]))
            facts = {"build": key[0], "mapID": key[1], "spellID": key[2],
                     "x": statistics.median(row["x"] for row in unique),
                     "y": statistics.median(row["y"] for row in unique),
                     "items": [{"itemID": item, "total": total,
                                "sampleSize": sum(row["sampleSize"] for row in unique),
                                "provenance": sorted(item_sources[item])}
                               for item, total in sorted(item_totals.items())],
                     "sampleSize": sum(row["sampleSize"] for row in unique)}
        else:
            # Run index identifies an account's cumulative export row. Repeated
            # exports of the same run count once; distinct runs remain distinct.
            unique = {}
            for row in rows:
                run = row.get("runIndex", row.get("observedAt"))
                identity = (row["_observer"], run, row.get("observedAt"),
                            row["durationSeconds"], row["lootCopper"])
                unique[identity] = row
            values = list(unique.values())
            facts = {"build": key[0], "dungeonID": key[1], "memberCount": key[2],
                     "medianDurationSeconds": statistics.median(row["durationSeconds"] for row in values),
                     "medianLootCopper": statistics.median(row["lootCopper"] for row in values),
                     "sampleSize": len(values)}
            rows = values
        candidates.append(candidate(kind, key, facts, rows))
    return {"format": "wow-together-gold-candidates", "schema": 1,
            "candidateCount": len(candidates), "candidates": candidates}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exports", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = ingest(load_exports(args.exports))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {result['candidateCount']} review-only Gold candidates to {args.output}")


if __name__ == "__main__":
    main()
