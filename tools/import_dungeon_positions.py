"""Compile dungeon-floor facts; never run downloaded Lua/SQL/web code.

Journal points must identify the same instance map and reference floor. Older
world spawns are projected only onto explicit client rectangles; ambiguous
floors remain unresolved. Quest relations come from our attributed Forever
catalogue, not proximity to a boss or to a dungeon entrance.
"""
import argparse
import collections
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import re

from build_quest_dataset import own_lua
from import_travel_network import encode

ROOT = Path(__file__).resolve().parents[1]
CLIENT_COMMIT = "ac1d02cba59374c5d599f78ede0cd3984f4312a1"
WORLD_COMMIT = "ec4f596146be6467ea93c57397858e329e2db852"


def normalized(value):
    return re.sub(r"[^a-z0-9]", "", value.lower())


def sequence(value):
    return value if isinstance(value, list) else []


def sql_spawns(path):
    """Only literal numeric creature/object spawn tuples; no SQL evaluation."""
    result = {"npc": collections.defaultdict(list), "object": collections.defaultdict(list)}
    with gzip.open(path, "rt", errors="strict") as stream:
        for line in stream:
            match = re.match(r"INSERT INTO `(creature|gameobject)` VALUES ", line)
            if not match:
                continue
            kind = "npc" if match[1] == "creature" else "object"
            for row in re.finditer(r"\(([^()]+)\)", line[match.end():]):
                fields = row[1].split(",")
                if len(fields) < 8 or not all(re.fullmatch(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", v) for v in fields):
                    raise ValueError("Nonliteral spawn tuple")
                ident, map_id = int(fields[1]), int(fields[2])
                point = {"map": map_id, "worldX": float(fields[4]), "worldY": float(fields[5])}
                if not all(math.isfinite(point[k]) for k in ("worldX", "worldY")):
                    raise ValueError("Nonfinite spawn")
                if point not in result[kind][ident]:
                    result[kind][ident].append(point)
    return result


def rectangle(row):
    # DungeonMap Min/Max[2] refer to world Y/X respectively. Map axes reverse
    # both. WorldMapArea publishes the corresponding Left/Right/Top/Bottom.
    return tuple(float(row[k]) for k in ("Unknown0_0", "Unknown1_0", "Unknown0_1", "Unknown1_1"))


def project(spawn, bounds):
    left, right, bottom, top = bounds
    if left == right or bottom == top:
        return None
    x, y = (right - spawn["worldY"]) / (right - left), (top - spawn["worldX"]) / (top - bottom)
    if not 0 <= x <= 1 or not 0 <= y <= 1:
        return None
    return {"x": round(x, 6), "y": round(y, 6)}


def targets(quest, entities):
    result, seen = [], set()

    def add(kind, ref, instruction=None):
        entity_kind, ident = ref.get("entityType"), ref.get("entityID")
        if entity_kind not in ("npc", "object") or not isinstance(ident, int):
            return
        key = (kind, entity_kind, ident, instruction)
        if key in seen:
            return
        seen.add(key)
        name = ref.get("name") or entities.get(entity_kind, {}).get(ident, {}).get("name")
        if name:
            result.append({"kind": kind, "entityType": entity_kind, "entityID": ident, "name": name,
                           "instruction": instruction or (("Pick up from " if kind == "a" else "Turn in to ") + name)})

    for kind, field in (("a", "startRefs"), ("t", "endRefs")):
        for ref in sequence(quest.get(field)):
            add(kind, ref)
    for requirement in sequence(quest.get("requirements")):
        kind, ident = requirement.get("entityType"), requirement.get("entityID")
        count, name = requirement.get("quantity"), requirement.get("name")
        quantity = str(count) + " × " if isinstance(count, int) and count > 0 else ""
        if kind == "npc":
            verb = "Kill " if requirement.get("action") != "talk" else "Talk to "
            add("q", requirement, verb + quantity + (name or "quest target"))
        elif kind == "object":
            add("q", requirement, "Collect " + quantity + (name or "quest object"))
        elif kind == "item":
            for ref in sequence(entities.get("item", {}).get(ident, {}).get("sources")):
                add("q", ref, "Collect " + quantity + (name or "quest item"))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-db", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--listfile", type=Path, required=True)
    args = parser.parse_args()
    journal = own_lua(ROOT / "WowTogether/DungeonJournalData.lua", "dungeonJournalData")
    definitions = own_lua(ROOT / "WowTogether/DungeonData.lua", "dungeonData")["dungeons"]
    catalogue = own_lua(ROOT / "WowTogether/QuestCatalogue.lua", "catalogue")["quests"]
    entities = own_lua(ROOT / "WowTogether/QuestCatalogue.lua", "questEntities")
    tables = {}
    sources = []
    for name in ("JournalEncounter", "DungeonMap", "WorldMapArea"):
        path = args.client_db / ("clientdb-" + name + ".csv")
        tables[name] = list(csv.DictReader(path.open()))
        sources.append({"url": f"https://github.com/eXPeRi91/ClientDB-Diff/blob/{CLIENT_COMMIT}/{name}.csv",
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    sources.append({"url": f"https://github.com/cmangos/classic-db/blob/{WORLD_COMMIT}/Full_DB/ClassicDB_1_12_1_z2815.sql.gz",
                    "sha256": hashlib.sha256(args.snapshot.read_bytes()).hexdigest()})
    file_ids = {path[:-4].replace("/", "\\"): int(ident) for ident, path in csv.reader(args.listfile.open(), delimiter=";") if path.endswith(".blp")}
    areas = {normalized(row["Unknown0"]): row for row in tables["WorldMapArea"]}
    floor_rows = {int(row["Id"]): row for row in tables["DungeonMap"]}
    encounters = collections.defaultdict(list)
    for row in tables["JournalEncounter"]:
        encounters[normalized(row["Unknown1"])].append(row)
    spawns = sql_spawns(args.snapshot)
    result, coverage = {}, {}
    for key, stored in journal["dungeons"].items():
        definition = definitions[key]
        entry = {"floors": [], "targets": []}
        result[key] = entry
        area, game_map, rectangles = None, None, {}
        if stored["maps"]:
            folder = stored["maps"][0]["tiles"][0].split("\\")[2]
            area = areas.get(normalized(folder))
            # Old-labelled artwork is only associated with the old game map,
            # not the redesigned journal map sharing part of its name.
            if not area and folder.lower().endswith("old"):
                area = areas.get(normalized(folder[:-3]))
            if area:
                game_map = int(area["Unknown5"])
                for row in tables["DungeonMap"]:
                    floor = int(row["Unknown4"])
                    if int(row["Unknown2"]) == game_map and 1 <= floor <= len(stored["maps"]):
                        rectangles[floor] = rectangle(row)
                if len(stored["maps"]) == 1 and not rectangles:
                    rectangles[1] = tuple(float(area[k]) for k in ("Unknown2", "Unknown1", "Unknown4", "Unknown3"))
        for index, floor in enumerate(stored["maps"], 1):
            entry["floors"].append({"tiles": [file_ids[t] for t in floor["tiles"]], "bosses": [], "quests": []})

        def positions(kind, ident):
            points = []
            for spawn in spawns[kind].get(ident, []):
                if spawn["map"] != game_map:
                    continue
                options = [(floor, point) for floor, bounds in rectangles.items() if (point := project(spawn, bounds))]
                if len(options) == 1:
                    floor, point = options[0]
                    points.append((floor, point))
            return points

        by_entity = {}
        unmapped = []
        for boss in stored["bosses"]:
            points = []
            for row in encounters[normalized(boss["name"])]:
                if not area or int(row["Unknown4"]) != int(area["Id"]):
                    continue
                dungeon_map = int(row["Unknown3"])
                floor_row = floor_rows.get(dungeon_map)
                if dungeon_map > 0 and not floor_row or dungeon_map == 0 and len(entry["floors"]) != 1:
                    continue
                floor = int(floor_row["Unknown4"]) if floor_row else 1
                if floor_row and int(floor_row["Unknown2"]) != game_map or not 1 <= floor <= len(entry["floors"]):
                    continue
                x, y = float(row["Unknown0_0"]), float(row["Unknown0_1"])
                if 0 <= x <= 1 and 0 <= y <= 1 and (x > 0 or y > 0):
                    points = [(floor, {"x": round(x, 6), "y": round(y, 6)})]
                    break
            if not points:
                points = positions("npc", boss["id"])
            if points:
                # A real representative spawn, never a centroid across rooms.
                floor, point = points[0]
                entry["floors"][floor - 1]["bosses"].append({"id": boss["id"], **point, "alternatives": len(points)})
                by_entity[("npc", boss["id"])] = [(floor, point)]
            else:
                unmapped.append({"id": boss["id"], "name": boss["name"]})
        missing_targets = 0
        mapped_quests = set()
        for ident in definition.get("questIDs", []):
            quest = catalogue.get(ident)
            if not quest:
                continue
            for target in targets(quest, entities):
                entry["targets"].append({"id": ident, **target})
                points = by_entity.get((target["entityType"], target["entityID"])) or positions(target["entityType"], target["entityID"])
                retained = []
                for floor, point in points:
                    # One actual spawn representative per target/floor keeps
                    # broad trash-mob objectives from covering the map in icons.
                    near = [p for f, p in retained if f == floor]
                    if near:
                        continue
                    retained.append((floor, point))
                    entry["floors"][floor - 1]["quests"].append({"id": ident, **target, **point})
                    mapped_quests.add(ident)
                if not retained:
                    missing_targets += 1
        coverage[key] = {"bosses": len(stored["bosses"]), "mappedBosses": len(stored["bosses"]) - len(unmapped),
                         "unmappedBosses": unmapped, "questsWithInteriorMarkers": len(mapped_quests),
                         "questMarkers": sum(len(f["quests"]) for f in entry["floors"]),
                         "unlocatedTargets": missing_targets}
    counts = {"dungeons": len(result), "referenceDungeons": sum(bool(e["floors"]) for e in result.values()),
              "mappedBosses": sum(c["mappedBosses"] for c in coverage.values()),
              "questMarkers": sum(c["questMarkers"] for c in coverage.values()),
              "questsWithInteriorMarkers": sum(c["questsWithInteriorMarkers"] for c in coverage.values())}
    data = {"schema": 1, "captured": "2026-10-06", "counts": counts, "dungeons": result}
    (ROOT / "WowTogether/DungeonMapData.lua").write_text("local addonName, ns = ...\n\n-- Reference floor facts; native coordinates take precedence. See DUNGEON_VIEWER.md.\nns.dungeonMapData = " + encode(data) + "\n")
    manifest = {"schema": 1, "captured": data["captured"], "counts": counts, "sources": sources, "coverage": coverage,
                "limitations": ["Older Classic layout/spawn references require Forever beta verification.",
                                "No guessed coordinates, ambiguous floor projections, entrance aliases or unrelated outdoor pins.",
                                "Quest targets without an interior location remain unmarked; exterior pickups/turn-ins are not interior failures.",
                                "Native exact-floor encounter positions override reference positions; reference facts are used only with matching artwork."]}
    (ROOT / "WowTogether/DungeonMapData.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(counts))
    for key, value in coverage.items():
        print(key, value["mappedBosses"], "/", value["bosses"], "bosses;", value["questMarkers"], "quest markers")


if __name__ == "__main__":
    main()
