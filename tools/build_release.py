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

Copy this complete WowTogether folder to:
World of Warcraft\\_classic_beta_\\Interface\\AddOns\\WowTogether\\

Update EVERY party member to {version}, including ALL {len(names)} Lua files,
then /reload. Restart the client fully if a new addon folder
does not appear. No Battle.net credentials or web service are needed.

/wt opens the dashboard; drag the bottom-right grip to resize it.
/wt tracker toggles the movable party objective overlay. Mouse-wheel scroll
through all quests/objectives; player names, zones and counts appear together.
/wt config opens settings: transparent tracker, circuit budgets, class quests,
NPC hints, map legend, dungeon/zone prompts and opt-in auto-accept/turn-in.
Finish our current quests first is ON by default. Nearby ready turn-ins come first,
then eligible nearby pickups, combined objectives and their later returns.
Long delivery detours wait for local work. Mapped accepted quests stay ahead
of discovery even when current-quests-first is off.
Include eligible nearby pickups is also ON by default. The existing trip's
walking budget limits pickup/return NPCs and known objective areas. Prerequisites,
faction, level and per-player eligibility still gate new pickups. Unknown
objective locations are explicitly partial; use the game tracker for them.
Your completed quest can be handed in while a friend's objectives stay marked.
Disable nearby pickups for accepted-quests-only plans, or disable current quests
first to discover new lines. No quest IDs are hardcoded into the bundler.
Main guide cards offer Start route instead of Quest details. Show route stays
local; Start route shares up to 20 selected quest IDs with party members.
Friends choose Follow route or Keep my route. Their current route remains
until they accept. Nearby-pickup roles are retained, including when a friend
has already accepted the quest. Explicit Follow route accepts that selection
even with automatic nearby pickups off. Each client uses its own party stages;
missing prerequisite/history data waits for sync. Solo Start route stays local.
The native resize gesture reflows cards without rebuilding plans per pixel.
/wt arrow toggles the small direction arrow for your selected route. Drag it
to move it; its position is saved. The arrow turns relative to your character
and shows straight-line yards when public position, map scale and facing exist.
The arrow also has Skip step, Skip quest and Scan guide. Skips persist per
character and do not complete quests, unlock prerequisites or change friends'
guides. Reset guide skips in settings or /wt guide reset restores them.
Guide start/Scan guide reads the selected quests, known series and prerequisite
history (bounded to 512 IDs); unknown results stay unknown. Friends' completion
waits for their own received snapshots. /wt guide scan opens the scan report.
Test turning and walking toward a route stop on your beta build. Unknown data
shows a status. Cross-zone stops name the zone until you enter it.
Two small context lines explain pickup/objectives/hand-in, the zone and whose
progress needs the stop. The selected active route can advance to another
zone when its next destination changes; unrelated zone coordinates never join.
On arrival it keeps the quest name, points downward, and says Talk to the
known NPC. Friendly quest-giver nameplates can show quest names and a pointer
when public NPC IDs are visible; all nameplate hints hide in combat.
Reaching a point does not accept or complete a quest. Follow roads and terrain.
Route lines draw on the WORLD MAP ONLY; the minimap button opens the addon.
Map preview defaults to the current place and two ahead. Use Show full route /
Focus next steps and the 0/1/2 ahead control on the map overlay. The complete
plan stays selected; quest progress advances the preview, not arrival alone.
Consecutive steps at a shared NPC stay grouped. The first leg follows your
current public position. Viewing another zone keeps the route and shows a
View route zone button. Controls remain when the text legend is disabled.
/wt sync requests fresh party data. Let the send queue drain.
/wt probe opens diagnostics; Ctrl+C copies the selected text and closes it.
/wt route clear clears the route overlay. /wt minimap toggles the minimap icon.

Check item/kill counts on both clients. Select Show route, finish objectives
or turn in on only one client, and confirm unfinished friends retain their
objective/turn-in markers. Complete it on the last player to finish the route.
Repeat with three players. A pending snapshot keeps the last confirmed route
dimmed. Each client must select Show route for the route it wants to display.

Library searches commit on Enter or after a typing pause. Choose a level
bracket or Near party; use arrows for larger result sets.
Known prerequisites (including Vile Familiars variants before Burning Blade
Medallion), faction, level and identity gate catalogue pickups. Unread or
ambiguous requirements stay unknown until a live NPC offer confirms them.
Discovery prefers your current zone and suitable overland neighbours; distant
or opposing-faction starter zones do not become automatic recommendations.
Connections are map data, not road pathfinding; verify geography in this beta.

Map drawing uses the visible viewport when GetViewRect is available, clips
lines to the map, and redraws after pan/zoom/resize. Nearby stops share a pin;
hover for all steps. The legend distinguishes stops from visible places.
Combat pan/zoom redraws existing verified unprotected owned overlay frames.
Protected frames, reparenting and native map/waypoint actions still defer.
If pins/lines are still absent, copy /wt probe after Show route and include
Route drawing surface, view geometry, rendered pins/lines and GetViewRect.
The new rendering path needs testing on your actual beta build.

Sync is automatic on party, quest/objective, level and zone changes, batched
before the paced send queue. Normal play does not require repeated /wt sync.
Local XP circuits collect nearby quests, visit objectives, then group turn-ins.
Published XP and walking estimates are approximate; lines do not follow roads.
The Dungeons tab lists pickup NPCs/levels and missing prerequisites. Collect
current-zone pickups first, then a known nearby entrance. If no client map link
locates an entrance, stand outside it and use Record entrance here.
Professions is personal: open your crafting window and refresh live recipes,
choose small batches and inspect materials. Public AH prices come only from
searches you make. No automatic searching, buying or crafting takes place.
Known vendor-listed quest items have a buy list with your own bag stock.
Auto-accept is OFF by default. If enabled, only an opened quest-detail dialog
is attempted outside combat. Verify this action on your beta build.
Auto-turn-in is also OFF by default. Enable it in /wt config to attempt accepted
quest dialogs you open outside combat, only when there is no reward choice.
Reward choices remain manual. Missing/restricted IDs or reward counts stay
manual. /wt probe reports IsQuestCompletable, CompleteQuest, GetNumQuestChoices
and GetQuestReward; presence and an attempt do not prove working behavior.
Test a no-choice turn-in and a choice-reward quest on your actual beta build.

New arrow facing/scale, recipe/AH, map-link/world-position, NPC fallback and quest dialog APIs need
testing on your beta build; /wt probe reports capabilities. Restricted data
stays unknown. NPC hints include alternative published drop NPC IDs and hide
in combat. No raid-target marking.
Known completed objective targets lose their skulls; generic native quest flags
cannot restore them. Unfinished objectives for other quests/party members remain.
Known repeatable quests, including Spirit of the Wind, stay in the library but
are excluded from automatic leveling guides. Source coverage remains partial.

The catalogue contains {coverage['count']:,} listed quests and {coverage['detailed_quests']:,} detailed pages. Locations
and prerequisites are partial. Route lines show visiting order, not roads.
Read README.md for coverage, limitations, source notes, and testing steps.
TESTING.md contains the friend-testing script and copyable report template.
CHANGELOG.md has the short release history. This release adds saved skips, guide
progression scans, repeatable filtering, objective-specific skull fixes and
combat map redraws. The general Vile Familiars prerequisite correction is retained;
Burning Blade Medallion still requires its completed prerequisite.
'''
    args.output.mkdir(parents=True, exist_ok=True)
    destination = args.output / f'WowTogether-{version}.zip'
    files = ['WowTogether.toc', *names, 'QuestCatalogue.json']
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            archive.write(addon / name, 'WowTogether/' + name)
        for name in ('README.md', 'TESTING.md', 'CHANGELOG.md'):
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
