# Native UI adapters — 9 October 2026

The tester supplied a GetAuraDataByIndex secret/taint error attributed to
WowTogether, inside ShouldShowMawBuffs → ScenarioObjectiveTracker LayoutContents.
They also reported a missing player in Ragefire Chasm and requested role filters
for players in Blizzard's group finder. No client probe or exact native finder
screen was supplied for this batch. These changes require beta confirmation.

Public Blizzard UI reference inspected from Gethe/wow-ui-source `live` on this
date (a reference implementation, **not** the exact Forever build):

- https://github.com/Gethe/wow-ui-source/blob/live/Interface/AddOns/Blizzard_MawBuffs/Blizzard_MawBuffs.lua
- https://github.com/Gethe/wow-ui-source/blob/live/Interface/AddOns/Blizzard_ObjectiveTracker/Blizzard_ScenarioObjectiveTracker.lua
- https://github.com/Gethe/wow-ui-source/blob/live/Interface/AddOns/Blizzard_FrameXMLUtil/Mainline/Blizzard_QuestSuperTracking.lua
- https://github.com/Gethe/wow-ui-source/blob/live/Interface/AddOns/Blizzard_APIDocumentationGenerated/MapDocumentation.lua
- https://github.com/Gethe/wow-ui-source/blob/live/Interface/AddOns/Blizzard_APIDocumentationGenerated/FrameAPIUnitPositionFrameDocumentation.lua
- https://github.com/Gethe/wow-ui-source/blob/live/Interface/AddOns/Blizzard_GroupFinder/Mainline/LFGList.lua
- https://github.com/Gethe/wow-ui-source/blob/live/Interface/AddOns/Blizzard_APIDocumentationGenerated/LFGListInfoDocumentation.lua

The matching reference aura call explains where the error is raised. It does
not identify the first taint propagation. Native selection/supertracking is an
avoidable integration that may schedule tracker work; it is conservatively
blocked on secret-aura clients even outside combat. No Blizzard function/frame
script is replaced, no aura exception is suppressed, and no addon reads auras.
A full restart is required to retest with previously tainted UI state removed.

The owned dungeon viewer refreshes on entry. A single exact native floor can be
identified from a confirmed instance even when GetBestMapForUnit retains the
outdoor map or returns nil. Public UnitPosition coordinates must share the
native floor's world ID, and the converter must return that exact UI map with
valid normalized coordinates. Multi-floor identity stays explicit. An owned
UnitPositionFrame can instead draw only the player with facing using documented
native methods; no restricted coordinates are returned to addon Lua. Its bounds
match the native image's letterbox/resize transform. Neither adapter borrows a
reference image's geometry or claims that arbitrary dungeon interiors work.
No Blizzard minimap/map frame is changed. The native drawing adapter is not
proof that the beta client supplies interior positions.

The role view is a separate UIParent-owned companion to LFGListFrame's search
and applicant contexts. It reads existing public results; it does not replace
native providers/filter functions, hide native rows, issue searches, invite,
decline or whisper. Newer public player-info structures provide names and
assigned roles; published role enum bits can add selected roles. The older
member API lacks other members' names, so only the publicly named leader can
be represented. Applicant roles use the documented tuple's tank/healer/damage
flags. Missing/private names are omitted; class never supplies a guessed role.
Only currently loaded/native-filtered results are represented, with a bounded
200-listing read. Exact Forever finder context/API support needs tester evidence.

Host checks in test_0864.py validate isolation, geometry, conversion rejection,
entry refresh, native-renderer configuration, declared role filtering and UI
ownership. Existing native quest-focus and dungeon viewer/player checks protect
prior supported behavior. These mocks do not establish actual in-game rendering,
absence of taint, private-data availability or finder API delivery.
