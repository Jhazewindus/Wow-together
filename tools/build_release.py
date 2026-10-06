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
    release_name = re.search(r'^## X-ReleaseName: ([A-Za-z0-9 -]{1,80})$', toc, re.M)
    release_label = version + (' — ' + release_name.group(1) if release_name else '')
    names = [line.strip() for line in toc.splitlines() if line.strip() and not line.startswith('#')]
    for name in names:
        if not re.fullmatch(r'[A-Za-z0-9_]+\.lua', name):
            raise ValueError('Unexpected addon source path: ' + name)
        if not (addon / name).read_text().startswith('local addonName, ns = ...\n'):
            raise ValueError('Missing namespace declaration: ' + name)
    media = addon / 'Media' / 'GuideThemes'
    art = json.loads((media / 'manifest.json').read_text())
    if art.get('schema') != 1 or art.get('source') != 'source-atlas.png' or len(art.get('textures', [])) != 16:
        raise ValueError('Incomplete guide-card artwork manifest')
    if hashlib.sha256((media / art['source']).read_bytes()).hexdigest() != art['source_sha256']:
        raise ValueError('Guide artwork source checksum mismatch')
    media_names = ['ARTWORK.md', 'manifest.json', art['source']]
    for texture in art['textures']:
        name = texture['file']
        if not re.fullmatch(r'[a-z-]+\.tga', name) or name in media_names:
            raise ValueError('Unexpected guide texture path: ' + name)
        if hashlib.sha256((media / name).read_bytes()).hexdigest() != texture['sha256']:
            raise ValueError('Guide texture checksum mismatch: ' + name)
        media_names.append(name)
    instructions = f'''Wow Together {release_label} — Forever beta

Copy the complete WowTogether folder to:
World of Warcraft\\_classic_beta_\\Interface\\AddOns\\WowTogether\\

Update EVERY party member to {version}, including ALL {len(names)} Lua files
and the Media folder,
then /reload. Restart the client fully if a new addon folder does not appear.
No Battle.net credentials or external API service are needed.

Database details unpack only when used. Keep DataStore.lua and the complete
generated data files together. /wt probe reports per-compartment load counts and
client memory when its API exists. No quest/NPC/loot facts are removed; guide
order and behavior remain. Retained host Lua memory is about 28.4 MiB at startup,
versus 52 MiB before compartment loading; actual beta memory needs testing with
the same saved data. Loot items are shared across sources and load on demand.

Leveling guides -> Include convenient class training is on by default.
Even levels make a personal training check due. A matching friendly trainer must
be within 150 metres, with estimated extra walking at most 150 yards near a quest
visit or before leaving a hub. Done training / Skip training resumes the same
quest order and saves your choice until the next even level. Pending visits and
choices survive reload; no spells are bought or their availability inferred.
The active map visit is T. Standalone-only arrows provide Done/Skip controls.
151 published trainer locations cover all nine classes; retest in the beta.

Ground routes check approximate enemy settlement footprints, including Astranaar.
Use another published connection when available; otherwise crossing lines are
hidden and the guide says to go around town. Markers/order/progress/skips remain.
Friendly flights remain usable; cached enemy points cannot bypass ownership checks.
Footprints use published occupied locations plus an estimated 100-yard margin,
not measured guard boundaries, road bypasses or a terrain mesh. Retest in the beta.

Highlight the current guide quest (Arrow and map settings) selects/tracks accepted
current quests in Blizzard's log for native map highlights. It waits until combat
ends; it does not open the map or add a user waypoint. Retest native beta behavior.
Use item appears for a special item on the current accepted guide objective.
Click outside combat; select any required target yourself. The log index is
verified again on each click. No automatic use; retest native item behavior.
Unavailable NPC pickups remain pending across unrelated progress/reload until a
fresh offer; this evidence is personal/build-scoped, not an inferred prerequisite.
Our Ancient Enemy and The High Chieftain need actual offers while unlocks remain
unresolved. Documented Report to Kadrak alternatives no longer request a duplicate
pickup when one version is active/completed; the chosen turn-in remains.
Keep fixed order and manual skips. All {len(names)} Lua files are required.

/wt opens the Classic-style resizable dashboard. Its dropdown has Leveling guides,
All quests (formerly Library), Party quests, Shared, Party progress, Dungeon quests,
Profession guides and Quest log review. All quests searches commit on Enter or pause.
Guide cards use original, faint zone-themed landscape backgrounds. The fade is
baked into local textures; no downloads or animation run in the game. Scenery
crops proportionally on resize. Dungeon cards reference official Blizzard client
artwork, stretched across the full block at a faint 14% opacity. Journal images
take precedence; 19 Classic and four Forever filenames are published. Remaining
new dungeons use available journal art or a neutral client background; missing
textures stay plain. No Blizzard images or external screenshots are bundled.
See DUNGEON_ARTWORK.md for sources and beta limits. See dungeon opens a movable,
resizable atlas from anywhere: choose floors when multiple maps exist, click boss
portraits to open their loot, and click quest icons for pickups/objectives/turn-ins.
Selecting a mapped boss follows its floor. The journal opens above the main
window. Boss loot defaults to your class; its dropdown also offers other classes
and All classes. Known weapon/armor types filter by usability; shared accessories,
quest items and unclassified drops remain. This does not rank equipment by stats.
Quests toggles those markers. The floor dropdown stays hidden for single/unmapped dungeons.
Map only is a compact gameplay view; it stays open during combat. Entry asks
Open map? when enabled. Classic floor references may differ from Forever layouts;
missing boss coordinates and new-dungeon data are never guessed.
See DUNGEON_VIEWER.md for snapshot coverage and beta tests. Unknown zones have a quiet
fallback. Artwork changes appearance only, not guide logic.
Restart the client fully if new artwork remains blank after reload.
Use level brackets / Near party to narrow the list.
Leveling guides has its own bracket dropdown, deferred zone/quest/NPC search
and pages. The default bracket follows the lowest synced party level. Full zone
guides appear as Recommended zone guide / Alternative zone guide; questlines stay
inside them. Path to Orgrimmar is a personal travel guide for Horde levels 1–60:
search Orgrimmar and Start route. It compares known city gates and uses crossings,
transports and confirmed flights, resumes after reload, and finishes on city entry.
No quests or invitations. An unmapped connection is explained; timing and walking
links are estimates. Explicit quest-log trips are in Party quests. The default
bracket recommends useful work for your actual lowest level. Manual brackets and
All levels also show Upcoming zone guides. Show quest list previews their full
order without changing the running route. Starting too early warns with the
suggested entry level and a suitable unfinished current-level guide, when known.
Choose Start recommended / Start anyway / Cancel. An early guide stays selected
while locked quests wait; pickup restrictions and fixed-order persistence remain.
Brackets filter browsing; a selected guide keeps later levels and known cross-zone
steps. Fixed zone guides are ON by default. Loading route appears while the complete
catalogue sequence is compiled once, independently of location and quest logs.
Include class quests shows or hides eligible class steps in that saved sequence,
the arrow/map and Show quest list. Toggling does not reorder a fixed guide or
erase manual skips; known class/race/faction and pickup requirements still apply.
Older zone checkpoints recover previously omitted optional records once on upgrade.
Collect useful quests nearby groups eligible planned accepts within 100 yards of
the next pickup across guides. Only accepts move; objective/return order and the
saved sequence stay intact. NPC offers refresh availability, not the whole plan;
unconfirmed pickups still need checking and auto-accept requires a real offer.
Escorts, prerequisites, skips, identities and physical map/world scale are respected.
Progress advances without changing that order, including after abandon or Scan.
Turn Follow fixed zone guides off and restart a guide for adaptive trips, which
hold up to six quests/twenty stops; their full preview is not limited to that trip.
Optional suitable next-zone prompts offer Start zone guide / Keep my guide.
They can also offer an adjacent suitable zone after leveling when this guide has
no useful work ready; unresolved NPC/location steps are retained.
/wt config has purpose-based settings pages with dropdowns and help text.
Unconfirmed branching prerequisites name the NPC. The current check gets a
large addon map star, friendly-nameplate confirmation hint and directions to the
known giver. Map NPC opens that zone and optionally sets a native waypoint for
this check only when its APIs work. Ordinary routes still never set a waypoint.
Nearby accepted kill/gather/loot work shares an In this area checklist with
separate quest names and live counts. Scroll beyond three tasks; individual skips
and fixed order stay intact. Only known destinations within 250 metres in the
current uninterrupted objective phase group together, respecting pickups,
turn-ins, travel, zones and missing locations. Terrain access is not inferred.
Travel routing has optional nearby flight-path and useful hearthstone tips.
A small dismissible strip appears within 150 metres of a friendly service.
Hearthstone tips require upcoming objectives away and multiple hub turn-ins;
flight tips hide known paths and distinguish Get from Check when unlocks are
unconfirmed. Hover for the location/reason. Advice never changes the quest order,
binds a home or unlocks a flight. New inn visits can be recorded per character.
Unsupported beta events no longer stop addon loading. Inn recording uses supported
binder interactions, never INN_INFO; home binding remains manual. /wt probe lists
unavailable event subscriptions and inn recording capabilities. Event handler
errors remain visible. Keep SavedVariables when replacing the complete folder.
Play mode → Solo leveling mode stops all party sends/receives, hides party
controls and uses only your character, even while grouped. Guides, local progress
and learning continue. Toggle off to request fresh party snapshots.
/wt tracker toggles the movable, scrollable party panel; it opens when joining a
normal party and hides when solo/in a raid. Closing it lasts for that party session.
/wt arrow toggles the movable direction panel. Choose yards or metres in settings.
Its small top-right BG button switches the guide background between opaque and
see-through. Text, arrow and controls stay fully visible. The attached objective
and tip panels match. The saved choice also appears in Arrow and map settings;
it changes appearance only, without changing guide steps, skips or travel.
Arrow and map settings has a separate movable standalone arrow, with its own
saved position; it can remain visible with the large direction panel hidden.
The guide-step panel's corner handle resizes it and its attached panels; size and
position persist. BG changes opacity. ST stops the guide and leaves an empty
window; Exit (×) stops and closes it. Start a new guide to reuse the window.
Toggle the guide window separately
with /wt arrow or Show the direction arrow in settings.
When it is shown, the guide panel keeps instructions/controls without a duplicate
arrow. A travel timer appears above the standalone arrow: estimated/timed flight
duration during rides, or approximate walking/mount time to the next waypoint.
Flight descriptions separate ride time from the whole journey. Quest map pins
stay visible in flight; ground lines resume after landing. Collection steps with
known item IDs/counts advance from personal bag counts on bag updates; kill/use
steps still require objective progress. Include class quests defaults on for
new settings, respecting saved opt-outs and excluding incompatible classes.
Selected guides resume after reload/login; current progress advances their steps.
Outside-guide questing and completion keep the controls visible; Clear route ends
the saved selection. Route controls sit below the world map viewport.
/wt catchup reviews an optional useful party catch-up route in the current zone.
The current guide stays selected until accepted; friends choose Follow or Keep.
Quest markers default to stars; Quest !, cross and skull styles remain selectable. Nameplate hints
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
under the arrow. Lower-level prerequisites name the useful unlock and its level
or dungeon purpose. Party stages focus on the member behind in confirmed progress.
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
Default recommendations match useful work at your actual level. Manual brackets
preview matching leveling areas, rather than sparse later handoffs or capital
pickup hubs. Cards show the main quest
band derived from catalogue data; missing objective geography remains unknown.

Left/right arrow buttons preview previous/later steps without changing quest credit.
History previews use published locations, not a recorded travel timeline.
Skip step / Skip quest persist for this character and do not change friends' credit.
Scan guide reads real progress without changing fixed order; adaptive mode replans.
It reads a fresh quest log before objectives/history, retries temporarily missing
entries and rechecks large history scans if progress changes. Failed/cancelled
scans retain saved skips. Reconsider skips clears them only after a successful
scan. Personal quest events share a short 0.1-second refresh; a hidden/resizing
dashboard cannot stop guide progress. Party messages keep their two-second batch.
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
Normal routes do not set extra Blizzard waypoint pins. Map NPC can set one for
a branching-prerequisite confirmation only. Numbered route markers
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

Accept / Turn in / Kill / Gather / Loot / Use instructions name known targets.
Matching public objective progress shows remaining quantities beside distance.
The guide panel adds a short action hint and known zone/coordinates; remote steps
say Travel to. Hover panels or quest-order rows for full instructions and supplied
quest items. Unknown locations stay explicit; planning anchors never appear as
real coordinates. Separate drops from the same creature retain their own counts.
Quest markers and quest-item tooltip hints require public data and hide in combat.
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
Auto-accept accepts only eligible actual offers from the selected guide. Unrelated
quests remain manual; no selected guide means no automatic acceptance.
Quest-dialog selection, auto-accept and no-choice auto-turn-in are separate opt-ins,
all OFF by default. Reward choices stay manual. Presence/attempts do not prove beta
protected-action behavior. New flight, gossip, item-hook and corpse APIs need testing.
Quest greeting probes must also be retested on Forever. Missing fields cannot
prove absence, and unpublished prerequisites are not guessed from quest IDs.

Dungeon guides combines the Forever overview, 23 bounded quest category lists
and published Forever entrance areas for all 19 Classic dungeon complexes and
four new dungeons. All nine new dungeons are listed; the other five keep missing
coordinates/quest sets explicit. Cards show run levels separately from collection
pickup levels. Quest list shows compact clickable cards, giver/zone/level/status
and status filters. Select a quest for its own pickup guide; Start route collects
all suitable quests across zones and required chains, then heads to the entrance.
Already accepted quests count as collected. Both reuse the small guide window.
The Record entrance here button is removed. Previous corrections still take
precedence, then public client map links and published areas. Scheduled planning
uses directed travel/known flights and bounded dependency-safe improvements;
ordinary progress preserves the itinerary. Missing offers/locations wait.
Entrance areas are not exact portal or cave paths; walk ordering uses estimates
where the travel graph has gaps. Read DUNGEONS.md and DungeonData.json.
Collection prompts wait for YOUR highest known pickup level for all relevant regular
quests, with identity/category filters. Unknown requirements prevent a full-level
claim. These personal routes work without party snapshots; an unmapped collection
remains selected with its missing offers/locations pending. A popup does not silently replace the selected guide.
Quest log review only suggests reviewing low-value unfinished work; it never abandons.
Personal professions use your opened recipes/materials, configurable small batches,
and AH searches YOU perform. No automatic buying, searching or crafting.
Profession/flight/skip state is not sent to peers.

The partial snapshot has {coverage['count']:,} quest records and
{coverage['detailed_quests']:,} detailed Forever pages; mapped pickup / objective /
hand-in coverage is {coverage['with_starters']:,} / {coverage['with_objectives']:,} /
{coverage['with_turnins']:,} quests. QuestCoverage.json lists remaining zone gaps.
Named target/item quantities and provided-item actions improve step instructions.
The fixed compiler reduces estimated distance without reordering during play.
Older-world fallbacks apply only to identity-matched unchanged quests and proven
map transforms. Real NPC offers can contradict a marked older-world gate.
Source denials and beta changes still prevent complete coverage. Terrain lines
are visiting-order estimates, not a collision-safe road path. See QUEST_DATA.md.
Known repeatables remain excluded from automatic leveling. Live offers/history
are authoritative; published facts can differ from the beta.

Published patrol paths for the next three pickup/hand-in givers draw as thin amber
search traces. Toggle in Quest markers settings; live NPC positions are unknown.
Temporary incomplete quest logs retain the last public snapshot. Confirmed ordinary
quest completions are saved per character/build, separate from skips and peers.
Flight countdowns label estimated first trips; native connecting stops improve
estimates when public. Confirmed complete rides supply personal, directed,
build/route-specific timings to both timers and planners. Short bounded retries
handle delayed taxi state/GPS; late GPS keeps the original landing time. Interrupted
or unknown arrivals do not become samples. Older unverified timings remain saved
but need re-timing; reload during a ride loses its departure context. Walking ETA
calculation is unchanged. Probe reports timing counts and expected/actual duration.
Guide info estimates quest XP and finish level from route start. Unobserved XP
thresholds use a labeled Classic baseline; kills/exploration and party/rested effects
are excluded. Unknown rewards/thresholds remain explicit. Fixed guide order stays.
The New Horde needs an actual NPC offer while exact race eligibility is unresolved.

Read README.md for full behavior and limits, CHANGELOG.md for this release,
and TESTING.md for the labeled friend-testing checklist. Host checks alone do not
establish actual WoW Forever API, protected-action or rendering compatibility.
'''
    args.output.mkdir(parents=True, exist_ok=True)
    destination = args.output / f'WowTogether-{version}.zip'
    files = ['WowTogether.toc', *names, 'QuestCatalogue.json', 'QuestCoverage.json', 'GuideAudit.json', 'GuideSourceQueue.json', 'TravelData.json', 'GuideServiceData.json', 'DungeonData.json', 'DungeonJournalData.json', 'DungeonMapData.json']
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            archive.write(addon / name, 'WowTogether/' + name)
        for name in media_names:
            archive.write(media / name, 'WowTogether/Media/GuideThemes/' + name)
        for name in ('README.md', 'TESTING.md', 'CHANGELOG.md'):
            archive.write(ROOT / name, 'WowTogether/' + name)
        for name in ('PERFORMANCE.md', 'TRAVEL_DATA.md', 'DUNGEONS.md', 'DUNGEON_ARTWORK.md', 'DUNGEON_VIEWER.md', 'THIRD_PARTY_NOTICES.md', 'QUEST_DATA.md',
                     'LEGACY_DATA_LICENSE.txt', 'LEGACY_DATA_COPYRIGHT.md'):
            if (ROOT / name).exists():
                archive.write(ROOT / name, 'WowTogether/' + name)
        archive.write(ROOT / 'LICENSE', 'WowTogether/LICENSE')
        for name in ('build_quest_dataset.py', 'pack_data.py', 'quest_enrichment.py', 'legacy_quest_facts.py', 'collect_quest_entities.py',
                     'forever_map_geometry.py', 'quest_event_areas.py', 'lua_data_literal.py', 'forever_beta_facts.py',
                     'quest_observation_facts.py', 'capture_quest_pages.py', 'audit_quest_guides.py',
                     'import_warcraftdb.py', 'import_wowhead.py', 'import_travel_network.py', 'import_guide_services.py', 'import_dungeons.py', 'import_dungeon_journal.py', 'import_dungeon_positions.py',
                     'audit_dungeon_loot.py', 'capture_dungeon_loot.py', 'import_vanilla_loot.py', 'dungeon_encounters.json',
                     'guide_source_queue.py', 'forever_source_manifest.json', 'quest_corrections.json', 'quest_exclusions.json'):
            archive.write(ROOT / 'tools' / name, 'WowTogether/data-tools/' + name)
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
