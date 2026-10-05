"""Package the complete beta addon and installation notes; no game client needed."""
import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/workspace/artifacts'))
    parser.add_argument('--post-discord', action='store_true', help='Post the verified release and its matching changelog/test checklist.')
    args = parser.parse_args()
    addon = ROOT / 'WowTogether'
    coverage = json.loads((addon / 'QuestCatalogue.json').read_text())
    toc = (addon / 'WowTogether.toc').read_text()
    if not re.search(r'^## Interface: 16001$', toc, re.M):
        raise ValueError('Release must target Forever interface 16001')
    version = re.search(r'^## Version: ([0-9]+\.[0-9]+\.[0-9]+)$', toc, re.M).group(1)
    names = [line.strip() for line in toc.splitlines() if line.strip() and not line.startswith('#')]
    for name in names:
        if not re.fullmatch(r'[A-Za-z0-9_]+\.lua', name):
            raise ValueError('Unexpected addon source path: ' + name)
        if not (addon / name).read_text().startswith('local addonName, ns = ...\n'):
            raise ValueError('Missing namespace declaration: ' + name)
    instructions = f'''Wow Together {version} — Forever beta

Copy the complete WowTogether folder to:
World of Warcraft\\_classic_beta_\\Interface\\AddOns\\WowTogether\\

Update EVERY party member to {version}, including ALL {len(names)} Lua files,
then /reload. Restart the client fully if a new addon folder does not appear.
No Battle.net credentials or external API service are needed.

/wt opens the Classic-style resizable dashboard. Its dropdown has Leveling guides,
All quests (formerly Library), Party quests, Shared, Party progress, Dungeon quests,
Profession guides and Quest log review. All quests searches commit on Enter or pause.
Use level brackets / Near party to narrow the list.
Leveling guides has its own bracket dropdown, deferred zone/quest/NPC search
and pages. The default bracket follows the lowest synced party level. Full zone
guides appear as Recommended zone guide / Alternative zone guide; questlines stay
inside them. Path to Orgrimmar is a personal travel guide for Horde levels 1–60:
search Orgrimmar and Start route. It compares known city gates and uses crossings,
transports and confirmed flights, resumes after reload, and finishes on city entry.
No quests or invitations. An unmapped connection is explained; timing and walking
links are estimates. Explicit quest-log trips are in Party quests. Every zone must contain
useful work for your actual level, respecting known pickup/prerequisite levels.
All levels does not bypass this; future quests remain browsable in All quests.
Brackets filter browsing; a selected guide keeps later levels and known cross-zone
steps. Fixed zone guides are ON by default. Loading route appears while the complete
catalogue sequence is compiled once, independently of location and quest logs.
Progress advances without changing that order, including after abandon or Scan.
Turn Follow fixed zone guides off and restart a guide for adaptive trips, which
hold up to six quests/twenty stops; their full preview is not limited to that trip.
Optional suitable next-zone prompts offer Start zone guide / Keep my guide.
/wt config has purpose-based settings pages with dropdowns and help text.
Play mode → Solo leveling mode stops all party sends/receives, hides party
controls and uses only your character, even while grouped. Guides, local progress
and learning continue. Toggle off to request fresh party snapshots.
/wt tracker toggles the movable, scrollable party panel; it opens when joining a
normal party and hides when solo/in a raid. Closing it lasts for that party session.
/wt arrow toggles the movable direction panel. Choose yards or metres in settings.
Arrow and map settings has a separate movable standalone arrow, with its own
saved position; it can remain visible with the large direction panel hidden.
Selected guides resume after reload/login; current progress advances their steps.
Outside-guide questing and completion keep the controls visible; Clear route ends
the saved selection. Route controls sit below the world map viewport.
/wt catchup reviews an optional useful party catch-up route in the current zone.
The current guide stays selected until accepted; friends choose Follow or Keep.
Quest markers can sit beside names as Quest !, cross or skull. Nameplate hints
have a separate toggle from item tooltip hints.
Quest markers → Star above guide quest givers highlights eligible selected-guide
pickups above visible friendly nameplates. It is cosmetic, hides in combat and
does not apply real raid marks. Enable friendly NPC nameplates in the game.
/wt sync requests fresh snapshots; normal quest/party changes sync automatically.
/wt probe opens diagnostics; Ctrl+C copies and closes the report.
/wt lua opens a paste box and copyable output for read-only API checks/assertions.
Use return for tables/multiple values, print for pane output, and apiType("C_API.Method")
for actual capability presence. No action APIs or loops; compilation needs guarded
loadstring/setfenv on this beta build. Run outside combat; secret values stay hidden.
With Collect useful quests nearby enabled, actual NPC lists collect useful
selected-guide pickups in one visit. Optional quest selection and acceptance work
as each native list returns; a closed NPC is never reopened remotely. Objective
and hand-in order stays fixed. Observed approximate pickup positions persist per
build, fill missing pickups, and appear in /wt findings; they grant no availability
or completion credit. Pending pickup instructions resume after reload.
Flight unlock recognition uses public GetTaxiNodesForMap discovery flags where
supported, refreshed on login/zone/unlock events and saved for this character.
Open a flight master to confirm reachable connections. The reader uses the global
GetTaxiMapID(), falling back to the visible native flight frame's map ID. It never
guesses from a taxi-system event or passes nil to GetAllTaxiNodes. Late map data
gets bounded retries that cancel on close. Unlock flags do not create flights.
Probe now reports Flight paths, Flight unlock scan and Flight map read; send these
lines after opening a master if a known path is still missing. Unsupported/private
data, missing positions or native slots keep flight actions manual.
/wt research opens local quest-data JSON; Select all, Ctrl+C, then save as a text
file labeled with your tester name for feedback. Settings → Quest data for testing
has the recording toggle and Export quest data. The latest 300 local observations
persist per character: actual NPC offers, acceptance/hand-in, build and relevant
history/context and manual skips. Observed temporary deferrals/restorations and
manual skips include exact guide/step context for level-specific tester review.
Skips never imply an unlock or missing offer.
Visit the same NPC before/after a hand-in. Exports omit character
names/chat and are never uploaded automatically.
One clean full-list/one-hand-in/new-offer pair can create a tentative prerequisite.
Use observed prerequisite patterns controls reuse on this account, matched by
build/faction for ordinary quests, across classes and races. Class/race-specific
quests or prerequisites keep that dimension restricted. Existing findings migrate;
contradictory merged predecessors remain disabled for review.
Changed level means review-only; published alternatives
are never narrowed and live contradictions disable a learned pattern. Playing UI
keeps source labels out; optional exports retain evidence. Fixed order stays stable.
/wt findings or Export guide findings includes account-wide patterns and proofs.
Include source names in guide findings is optional, OFF by default. Send labeled
files for review to improve the bundled guides; no automatic upload or sync.
/wt questlines inspects native questline fields and optional GetQuestLineQuests IDs
in a copyable window. This is a capability test, not a prerequisite contract.
The Hunt Continues (750) requires handing in The Hunt Begins (747), from a tester
report preserved separately from published source facts. Restart selected guides
after upgrading to compile improved generic partial-objective ordering.
Confirmed unavailable pickups temporarily defer their stages while other available
work continues. Progress and actual NPC offers restore them in the fixed order;
unknown data and manual skips are separate. A missing offer alone is not shared
with other Horde characters; clean learned unlock requirements can be reused.
/wt route clear clears the map route. /wt minimap toggles its dashboard button.

Show route is local. Start route invites friends with Follow route / Keep my route.
Leveling cards instead have Show quest list: the complete scrollable pickup,
objective and turn-in order, including later steps and current progress. This
preview does not start/switch a route; started fixed guides reuse their order.
Fixed and adaptive guides with current quests offer Start selected guide or Include current quests, with
a warning about detours. Explicit quest-log routes remain
selectable in Party quests. Quest acceptance/zone updates retain the selection.
Full zone/questline invitations share guide identity and bracket, allowing friends
to reconstruct the full catalogue scope beyond the twenty transmitted quest IDs.
Low-level pickups need a known useful later quest/dungeon exception, explained
under the arrow. Party stages focus on the member behind in confirmed progress.
Unknown prerequisites/history stay unknown. Include current quests also filters
unfinished low-level work; ready hand-ins and useful prerequisites are kept.
Fixed guides also apply the value filter without rewriting the compiled order.
The preferred band is three levels below to three above the lowest synced player.
At level 23, Centaur Bracers does not qualify as a new pickup or unfinished work
unless a useful known prerequisite exception applies. Diagnostics show the band.
Skip quest/step updates the arrow and map immediately, even with the dashboard
hidden/resizing; manual skips remain personal and never grant completion credit.
Collector's Edition Welcome! rewards are excluded
from all leveling guides, but remain in All quests.
Brackets must match useful work at your actual level in leveling areas, rather
than sparse later handoffs or capital pickup hubs. Cards show the main quest
band derived from catalogue data; missing objective geography remains unknown.

Left/right arrow buttons preview previous/later steps without changing quest credit.
History previews use published locations, not a recorded travel timeline.
Skip step / Skip quest persist for this character and do not change friends' credit.
Scan guide reads real progress without changing fixed order; adaptive mode replans.
A rotating loop replaces both arrow displays while scanning/calculating, then
directions return. History reads yield between batches; changing/clearing a guide
cancels its pending scan. Flight observations refresh the arrow and map immediately,
including the Orgrimmar gate choice. Walking to a flight master explains the flight
that follows; automatic flight selection uses the same travel decision. Actual
flights hide ground lines until landing; no airborne terrain route is invented.
The extra Guide replanned footer is removed. Diagnostics distinguish the full
guide's quest scope from its current trip's quests and map stop counts.
Reconsider skips when scanning is off by default; on clears selected-guide quest skips.
Reset guide skips or /wt guide reset restores ALL guides' skips for this character.
/wt guide scan performs the same progress refresh from the command line.

Map lines show the current place plus two ahead, or use Show full route for ALL
currently eligible mapped quests. Locked future quests remain in the sequence.
Coverage counts distinguish known quest facts from actual map coordinates.
Shared NPC steps stay grouped. View route zone opens the current destination map.
The first line follows your live position, including toward another zone. Public
world coordinates project onto the viewed zone/continent; zone views clip at edges.
The arrow continues across borders without changing the fixed guide sequence.
Missing/private coordinates or different continents leave gaps and travel text.
The current travel leg can use Dijkstra crossing/gate/transport directions;
later quest markers remain visiting previews. Walks are point estimates, not
collision-safe roads. Transport rides break the walking line. No minimap lines.
The addon no longer sets extra Blizzard waypoint pins. Numbered route markers
and the arrow remain; unrelated manual waypoints are untouched. Clear older pins
manually if one remains from a previous version.
Follow roads/terrain. Pan/zoom redraws verified unprotected addon geometry in combat;
protected frames and native map actions wait. Actual beta rendering needs testing.

Open flight-master maps to learn this character's network. Useful known flights
compare estimated walk/flight/walk costs; timed rides improve their duration.
Nearby observed unconfirmed paths may get a short check stop. There is no complete
flight-path database. Select the suggested flight is optional and OFF by default;
only the open matching source's public reachable slot is requested outside combat.
While flying, elapsed/approximate remaining time replaces distance. As a ghost,
corpse directions temporarily replace the guide; missing corpse data is explicit.
Travel routing settings enables our own Dijkstra search over an attributed
Forever geographic snapshot (256 points, 1,620 directed links) plus this
character's observed usable flights. No upstream addon engine/UI is included.
Fixed quest order stays unchanged. Zone changes and detours refresh travel;
boarding points never grant quest credit. Read TRAVEL_DATA.md and the bundled
THIRD_PARTY_NOTICES.md for source license, coverage and beta-testing limits.
Missing-coordinate generation errors are fixed; retired UNUSED/zzOLD entries
are excluded from leveling guides and ignored in retained fixed steps.

Kill / Pick up / Talk instructions name known targets. Cross markers (or optional
kill skulls) and quest-item tooltip hints require public data and hide in combat.
Finished objective types lose hints unless another unfinished quest/member needs them.
NPC gossip and quest-greeting lists can confirm/block offers in the current progress context; a single dialog
confirms that quest only. Every pickup checks known prerequisites before positive
NPC evidence. Accepting, objective completion or skipping is not a prerequisite
hand-in. Unknown history stays unknown. Actual offers can confirm missing source
requirements but cannot bypass known unfinished chains or identity/level restrictions.
IsPushableQuest is sharing only; IsQuestCompletable is opened-dialog turn-in only.
Neither is a pickup gate. The old beta setting/packets are removed.
Normal event sync rechecks progress; locked quests stay in the full guide and
accepted work remains. Diagnostics show per-quest reasons and NPC evidence.
Published-data candidates can still have hidden beta gates; visit the NPC to verify.
Quest-dialog selection, auto-accept and no-choice auto-turn-in are separate opt-ins,
all OFF by default. Reward choices stay manual. Presence/attempts do not prove beta
protected-action behavior. New flight, gossip, item-hook and corpse APIs need testing.
Quest greeting probes must also be retested on Forever. Missing fields cannot
prove absence, and unpublished prerequisites are not guessed from quest IDs.

Dungeon Start route collects known eligible pickups then a nearby located entrance.
Missing prerequisites/coordinates remain explicit; Record entrance here is available.
Collection prompts wait for YOUR highest known pickup level for all relevant regular
quests, with identity/category filters. Unknown requirements prevent a full-level
claim. These personal routes work without party snapshots; an unmapped collection
opens its entire quest list. A popup does not silently replace the selected guide.
Quest log review only suggests reviewing low-value unfinished work; it never abandons.
Personal professions use your opened recipes/materials, configurable small batches,
and AH searches YOU perform. No automatic buying, searching or crafting.
Profession/flight/skip state is not sent to peers.

The partial snapshot has {coverage['count']:,} quest records and
{coverage['detailed_quests']:,} detailed pages; most objective coordinates are missing.
Known repeatables remain excluded from automatic leveling. Live offers/history
are authoritative; published facts can differ from the beta.

Read README.md for full behavior and limits, CHANGELOG.md for this release,
and TESTING.md for the labeled friend-testing checklist. Host checks alone do not
establish actual WoW Forever API, protected-action or rendering compatibility.
'''
    args.output.mkdir(parents=True, exist_ok=True)
    destination = args.output / f'WowTogether-{version}.zip'
    files = ['WowTogether.toc', *names, 'QuestCatalogue.json', 'TravelData.json']
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            archive.write(addon / name, 'WowTogether/' + name)
        for name in ('README.md', 'TESTING.md', 'CHANGELOG.md'):
            archive.write(ROOT / name, 'WowTogether/' + name)
        for name in ('PERFORMANCE.md', 'TRAVEL_DATA.md', 'THIRD_PARTY_NOTICES.md'):
            if (ROOT / name).exists():
                archive.write(ROOT / name, 'WowTogether/' + name)
        archive.write(ROOT / 'LICENSE', 'WowTogether/LICENSE')
        archive.writestr('WowTogether/INSTALL.md', instructions)
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise ValueError('Release archive failed verification')
    print(f'{destination}: {len(names)} Lua files, {destination.stat().st_size} bytes')
    print('SHA256 ' + hashlib.sha256(destination.read_bytes()).hexdigest())
    if args.post_discord:
        from post_discord_release import PublicationError, configured_webhook, post_release
        try:
            post_release(destination, configured_webhook())
        except (PublicationError, ValueError) as error:
            print(str(error), file=sys.stderr)
            raise SystemExit(1) from None


if __name__ == '__main__':
    main()
