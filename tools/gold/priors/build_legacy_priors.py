"""Build auditable, reference-only priors from the pinned CMaNGOS SQL dump.

Questie inputs are used only to mark entity IDs as changed. No Questie facts,
values, names, coordinates, or relations are read into the priors.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "tools"
OUT = Path(__file__).resolve().parent
SOURCE_MANIFEST = OUT / "source_manifest.json"
PINS = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
CMANGOS_COMMIT = PINS["cmangos"]["commit"]
CMANGOS_PATH = PINS["cmangos"]["path"]
CMANGOS_SHA256 = PINS["cmangos"]["sha256"]
QUESTIE_COMMIT = PINS["questieChangedIdFlags"]["commit"]
QUESTIE_MANIFEST = TOOLS / "forever_source_manifest.json"
QUESTIE_FILES = {
    kind: (value["path"], value["sha256"])
    for kind, value in PINS["questieChangedIdFlags"]["files"].items()
}
NOTICE = PINS["copyrightNotice"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _lua_tokens(source: str) -> Iterable[tuple[str, str]]:
    """Small tokenizer sufficient to identify only top-level numeric table keys."""
    i, size = 0, len(source)
    while i < size:
        char = source[i]
        if char.isspace():
            i += 1
            continue
        if source.startswith("--", i):
            if source.startswith("--[[", i):
                end = source.find("]]", i + 4)
                if end < 0:
                    raise ValueError("Unclosed Lua long comment")
                i = end + 2
            else:
                end = source.find("\n", i + 2)
                i = size if end < 0 else end + 1
            continue
        if char in "'\"":
            quote = char
            i += 1
            while i < size:
                if source[i] == "\\":
                    i += 2
                elif source[i] == quote:
                    i += 1
                    break
                else:
                    i += 1
            else:
                raise ValueError("Unclosed Lua string")
            yield "string", ""
            continue
        if char.isalpha() or char == "_":
            start = i
            i += 1
            while i < size and (source[i].isalnum() or source[i] == "_"):
                i += 1
            yield "identifier", source[start:i]
            continue
        if char.isdigit():
            start = i
            i += 1
            while i < size and source[i].isdigit():
                i += 1
            yield "number", source[start:i]
            continue
        yield char, char
        i += 1


def extract_fix_ids(path: Path) -> set[int]:
    """Return only integer keys at depth one in a module's returned table."""
    tokens = list(_lua_tokens(path.read_text(encoding="utf-8")))
    result: set[int] = set()
    i = 0
    while i + 1 < len(tokens):
        if tokens[i] == ("identifier", "return") and tokens[i + 1] == ("{", "{"):
            depth = 1
            i += 2
            while i < len(tokens) and depth:
                if depth == 1 and i + 4 < len(tokens):
                    a, b, c, d, e = tokens[i : i + 5]
                    if a[0] == "[" and b[0] == "number" and c[0] == "]" and d[0] == "=" and e[0] == "{":
                        result.add(int(b[1]))
                kind, _ = tokens[i]
                if kind == "{":
                    depth += 1
                elif kind == "}":
                    depth -= 1
                i += 1
            if depth:
                raise ValueError(f"Unclosed returned table in {path}")
            return result
        i += 1
    raise ValueError(f"No returned table found in {path}")


def verify_questie_pin(questie_root: Path) -> dict[str, set[int]]:
    manifest = json.loads(QUESTIE_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("commit") != QUESTIE_COMMIT:
        raise ValueError("Questie source manifest commit differs from pinned revision")
    ids = {}
    for kind, (relative, expected_hash) in QUESTIE_FILES.items():
        if manifest.get("files_sha256", {}).get(relative) != expected_hash:
            raise ValueError(f"Questie manifest checksum mismatch for {relative}")
        path = questie_root / relative
        if sha256(path) != expected_hash:
            raise ValueError(f"Questie fix list differs from pinned source: {relative}")
        ids[kind] = extract_fix_ids(path)
    return ids


def read_facts(snapshot: Path) -> dict:
    if sha256(snapshot) != CMANGOS_SHA256:
        raise ValueError("CMaNGOS snapshot differs from pinned checksum")
    sys.path.insert(0, str(TOOLS))
    import legacy_quest_facts as legacy

    # The pinned schema has min/max respawn fields rather than one spawntimesecs.
    legacy.SELECTION["creature"].update({"spawntimesecsmin", "spawntimesecsmax"})
    legacy.SELECTION["gameobject"].update({"spawntimesecsmin", "spawntimesecsmax"})
    return legacy.read_snapshot(snapshot)


def provenance(table: str) -> dict:
    return {
        "source": f"{PINS['cmangos']['repository']}/blob/{CMANGOS_COMMIT}/{CMANGOS_PATH}",
        "commit": CMANGOS_COMMIT,
        "snapshot": CMANGOS_PATH,
        "snapshotSha256": CMANGOS_SHA256,
        "license": "GPL-3.0",
        "table": table,
        "transform": "Selected numeric/name facts only; SQL was parsed as data and never executed.",
    }


def envelope(table: str, rows: list[dict], changed_kind: str | None = None) -> dict:
    source = provenance(table)
    if changed_kind:
        path, checksum = QUESTIE_FILES[changed_kind]
        source["changedFlag"] = {
            "source": f"{PINS['questieChangedIdFlags']['repository']}/blob/{QUESTIE_COMMIT}/{path}",
            "commit": QUESTIE_COMMIT,
            "sha256": checksum,
            "use": "ID membership only; no Questie fact values are imported.",
        }
    return {
        "schema": 1,
        "provenance": source,
        "copyrightNotice": NOTICE,
        "count": len(rows),
        "rows": rows,
    }


def _get(row: dict, *keys: str):
    for key in keys:
        if key in row:
            return row[key]
    return None


def build_outputs(facts: dict, questie_ids: dict[str, set[int]]) -> dict[str, dict]:
    creatures = {row["Entry"]: row for row in facts["creature_template"]}
    objects = {row["entry"]: row for row in facts["gameobject_template"]}
    items = {row["entry"]: row for row in facts["item_template"]}
    creature_spawns: dict[int, list[dict]] = {}
    object_spawns: dict[int, list[dict]] = {}
    for source, target, id_key in (
        (facts["creature"], creature_spawns, "id"),
        (facts["gameobject"], object_spawns, "id"),
    ):
        for row in source:
            target.setdefault(row[id_key], []).append(
                {
                    "map": row["map"],
                    "worldX": row["position_x"],
                    "worldY": row["position_y"],
                    "respawnSecondsMin": _get(row, "spawntimesecsmin"),
                    "respawnSecondsMax": _get(row, "spawntimesecsmax"),
                }
            )
    npc_changed = questie_ids["npc"]
    creatures_rows = [
        {
            "id": ident,
            "name": row["Name"],
            "minLevel": row["MinLevel"],
            "maxLevel": row["MaxLevel"],
            "rank": row["Rank"],
            "lootId": row["LootId"],
            "changed": ident in npc_changed,
            "spawns": sorted(spawn_rows, key=lambda s: (s["map"], s["worldX"], s["worldY"], s["respawnSecondsMin"] or 0)),
        }
        for ident, row in sorted(creatures.items())
        for spawn_rows in [creature_spawns.get(ident, [])]
    ]
    object_rows = [
        {
            "id": ident,
            "name": row["name"],
            "type": row["type"],
            "lootId": row["data1"] if row["type"] == 3 else None,
            "spawns": sorted(spawn_rows, key=lambda s: (s["map"], s["worldX"], s["worldY"], s["respawnSecondsMin"] or 0)),
        }
        for ident, row in sorted(objects.items())
        for spawn_rows in [object_spawns.get(ident, [])]
    ]
    item_rows = [
        {
            "id": ident,
            "name": row["name"],
            "startQuest": row["startquest"],
            "buyPrice": row["BuyPrice"],
            "changed": ident in questie_ids["item"],
        }
        for ident, row in sorted(items.items())
    ]

    def loot_rows(source: list[dict]) -> list[dict]:
        return [
            {
                "ownerLootId": row["entry"],
                "itemId": row["item"],
                "chanceOrQuestChance": row["ChanceOrQuestChance"],
                "minCountOrReference": row["mincountOrRef"],
            }
            for row in sorted(source, key=lambda r: (r["entry"], r["item"], r["mincountOrRef"]))
        ]

    return {
        "creatures.json": envelope("creature_template + creature", creatures_rows, "npc"),
        "gameobjects.json": envelope("gameobject_template + gameobject", object_rows),
        "items.json": envelope("item_template", item_rows, "item"),
        "creature_loot.json": envelope("creature_loot_template", loot_rows(facts["creature_loot_template"])),
        "gameobject_loot.json": envelope("gameobject_loot_template", loot_rows(facts["gameobject_loot_template"])),
    }


def write_outputs(outputs: dict[str, dict], destination: Path = OUT) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for filename, payload in outputs.items():
        path = destination / filename
        path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


def build(snapshot: Path, questie_root: Path, destination: Path = OUT) -> dict[str, dict]:
    facts = read_facts(snapshot)
    changed_ids = verify_questie_pin(questie_root)
    outputs = build_outputs(facts, changed_ids)
    write_outputs(outputs, destination)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--questie-root", type=Path, required=True, help="Pinned QuestieDB checkout root")
    parser.add_argument("--output-dir", type=Path, default=OUT)
    args = parser.parse_args()
    outputs = build(args.snapshot, args.questie_root, args.output_dir)
    print(json.dumps({name: item["count"] for name, item in outputs.items()}, sort_keys=True))


if __name__ == "__main__":
    main()
