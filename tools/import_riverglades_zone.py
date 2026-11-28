"""Capture and normalize the published Warcraft DB Forever Riverglades quests.

The capture is resumable and paced. It writes public quest facts only; quest
descriptions, comments, rendered HTML and source addon logic are not stored.
"""
import argparse
import concurrent.futures
import datetime
import hashlib
import html
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from import_warcraftdb import BASE, normalize
from quest_enrichment import enrich, warcraftdb_map_facts, warcraftdb_objective_facts
from forever_beta_facts import merge_beta_facts

ROOT = Path(__file__).resolve().parents[1]
ZONE_MAP_ID = 2548
ZONE_AREA_ID = 16591
ZONE_NAME = "Riverglades"
CATEGORY_PATH = "eastern-kingdoms/riverglades"
USER_AGENT = "WowTogether-Riverglades-zone-guide/0.8"


def fetch_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read()
    return payload, json.loads(payload)


def fetch_with_retry(url):
    for attempt in range(3):
        try:
            return fetch_json(url)
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
            time.sleep(min(20, int(error.headers.get("Retry-After", "2")) * (attempt + 1)))


def capture_index(cache):
    cache.mkdir(parents=True, exist_ok=True)
    first_path = cache / "list-1.json"
    if first_path.exists():
        first = json.loads(first_path.read_text())
    else:
        payload, first = fetch_with_retry(f"{BASE}/api/data/list/quests?page=1&per_page=100")
        first_path.write_bytes(payload)
    total, pages = first.get("total"), first.get("pages")
    if type(total) is not int or total <= 0 or type(pages) is not int or not 1 <= pages <= 1000:
        raise ValueError("Unexpected public quest list pagination")

    def load(page):
        path = cache / f"list-{page}.json"
        if path.exists():
            data = json.loads(path.read_text())
        else:
            time.sleep(0.2)
            payload, data = fetch_with_retry(f"{BASE}/api/data/list/quests?page={page}&per_page=100")
            path.write_bytes(payload)
        if data.get("page") != page or data.get("total") != total or not isinstance(data.get("rows"), list):
            raise ValueError(f"Quest list page {page} does not match the verified index")
        return data["rows"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        rows = list(first["rows"])
        for index, page_rows in enumerate(pool.map(load, range(2, pages + 1)), 2):
            rows.extend(page_rows)
            if index % 10 == 0:
                print(f"Quest list pages: {index}/{pages}", flush=True)
    ids = [row.get("record_id") for row in rows]
    if len(rows) != total or any(type(ident) is not int or ident <= 0 for ident in ids) or len(set(ids)) != total:
        raise ValueError("Quest list changed or contains duplicate/invalid IDs")
    riverglades = [row for row in rows if row.get("zone_id") == ZONE_MAP_ID
                   or str(row.get("zone", "")).strip().casefold() == ZONE_NAME.casefold()]
    if not riverglades or any(row.get("zone_id") != ZONE_MAP_ID for row in riverglades):
        raise ValueError("Riverglades list membership has conflicting source identities")
    return total, pages, riverglades


def references(raw, role):
    value = raw.get("data", {}).get(role)
    if not isinstance(value, str):
        return []
    result = []
    for kind, ident, label in re.findall(
            r"/data/(npc|object|item)/(\d+)[^\"]*\"[^>]*>(.*?)</a>", value, re.I | re.S):
        result.append({"entityType": kind.lower(), "entityID": int(ident),
                       "name": html.unescape(re.sub(r"<[^>]+>", "", label)).strip()})
    return result


def normalize_quest(row, raw, source_hash):
    ident = row["record_id"]
    data = raw.get("data", {})
    if data.get("name") != row.get("name") or data.get("zone_id") != ZONE_MAP_ID:
        raise ValueError(f"Quest {ident} detail identity does not match the Riverglades index")
    quest = normalize(row, raw)
    quest.update({"areaID": ZONE_AREA_ID, "mapID": ZONE_MAP_ID,
                  "zone": ZONE_NAME, "categoryPath": CATEGORY_PATH})
    refs = {"starts": references(raw, "starts"), "ends": references(raw, "ends"),
            "requirements": [], "provided": []}
    refs["requirements"], refs["provided"] = warcraftdb_objective_facts(raw)
    quest["startRefs"], quest["endRefs"] = refs["starts"], refs["ends"]
    quest["worldReferences"] = refs
    if refs["provided"]:
        quest["providedItems"] = refs["provided"]
    if refs["requirements"]:
        quest["requirements"] = refs["requirements"]
    quest["objectives"] = []
    warcraftdb_map_facts(raw, quest, refs, {"npc": {}, "object": {}, "item": {}}, {ZONE_MAP_ID})
    quest["sourceFact"] = {
        "source": f"{BASE}/api/data/node/quest/{ident}",
        "sha256": source_hash,
        "captured": datetime.date.today().isoformat(),
    }
    return quest


def capture(cache, output, questie_checkout=None):
    total, pages, rows = capture_index(cache)
    print(f"Verified {total} quest rows across {pages} pages; Riverglades rows: {len(rows)}", flush=True)

    def load(row):
        ident = row["record_id"]
        path = cache / f"quest-{ident}.json"
        if path.exists():
            payload = path.read_bytes()
            raw = json.loads(payload)
        else:
            time.sleep(0.25)
            payload, raw = fetch_with_retry(f"{BASE}/api/data/node/quest/{ident}")
            path.write_bytes(payload)
        return row, raw, hashlib.sha256(payload).hexdigest()

    captures = []
    failures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(load, row) for row in rows]
        for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
            try:
                captures.append(future.result())
            except Exception as error:
                failures.append(str(error))
            if index % 25 == 0:
                print(f"Quest details: {index}/{len(rows)}", flush=True)
    if failures:
        raise RuntimeError(f"{len(failures)} quest details could not be captured: {failures[:5]}")

    list_hashes = {}
    for page in range(1, pages + 1):
        file = cache / f"list-{page}.json"
        list_hashes[str(page)] = hashlib.sha256(file.read_bytes()).hexdigest()
    quests = []
    for row, raw, digest in sorted(captures, key=lambda item: item[0]["record_id"]):
        quests.append({"questID": row["record_id"], "title": row["name"],
                       "facts": normalize_quest(row, raw, digest)})
    questie_source = None
    if questie_checkout:
        records = {row["questID"]: row["facts"] for row in quests}
        refs = {ident: facts.get("worldReferences", {"starts": [], "ends": [],
                "requirements": [], "provided": []}) for ident, facts in records.items()}
        entities = {kind: {} for kind in ("npc", "object", "item")}
        metadata_path = ROOT / "WowTogether/QuestCatalogue.json"
        catalogue_metadata = json.loads(metadata_path.read_text())
        area_maps = {int(area): map_id for area, map_id in catalogue_metadata.get("area_ui_maps", {}).items()}
        area_maps[ZONE_AREA_ID] = ZONE_MAP_ID
        beta = merge_beta_facts(records, refs, entities, area_maps, questie_checkout)
        for ident in sorted(row["questID"] for row in quests):
            facts = records[ident]
            relation = refs.setdefault(ident, {"starts": [], "ends": [], "requirements": [], "provided": []})
            facts["startRefs"], facts["endRefs"] = relation["starts"], relation["ends"]
            facts["worldReferences"] = relation
            enrich(facts, relation, entities)
            if not facts.get("starts"):
                facts["pickupRequiresOffer"] = True
        questie_source = {key: beta[key] for key in (
            "source", "commit", "files_sha256", "parsed_records", "limitations")}
        questie_source["riverglades_quests_with_facts"] = sum(
            bool(records[row["questID"]].get("betaFactsSource")) for row in quests)
        questie_source["riverglades_objective_points"] = sum(
            len(records[row["questID"]].get("objectives", [])) for row in quests)
        questie_source["riverglades_unresolved_objectives"] = [
            row["questID"] for row in quests
            if records[row["questID"]].get("objectiveLocationsIncomplete")]
        for row in quests:
            row["facts"] = records[row["questID"]]
    result = {
        "schema": 1,
        "captured": datetime.date.today().isoformat(),
        "source": BASE,
        "listURL": f"{BASE}/api/data/list/quests",
        "listTotal": total,
        "listPages": pages,
        "listPageSHA256": list_hashes,
        "zone": ZONE_NAME,
        "zoneMapID": ZONE_MAP_ID,
        "sourceAreaID": ZONE_AREA_ID,
        "categoryPath": CATEGORY_PATH,
        "questieSource": questie_source,
        "inventoryCount": len(quests),
        "quests": quests,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"inventory": len(quests),
                      "startPoints": sum(bool(q["facts"].get("starts")) for q in quests),
                      "endPoints": sum(bool(q["facts"].get("ends")) for q in quests),
                      "objectivePoints": sum(bool(q["facts"].get("objectives")) for q in quests),
                      "incompleteObjectives": sum(bool(q["facts"].get("objectiveLocationsIncomplete")) for q in quests),
                      "output": str(output)}, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path("/tmp/wow-together-riverglades-warcraftdb"))
    parser.add_argument("--output", type=Path, default=ROOT / "tools/riverglades_zone_quests.json")
    parser.add_argument("--questie-checkout", type=Path,
                        help="Pinned QuestieDB checkout validated by tools/forever_source_manifest.json")
    args = parser.parse_args()
    capture(args.cache, args.output, args.questie_checkout)


if __name__ == "__main__":
    main()
