"""Optional class work is filtered after compiling an immutable zone guide.

Lua 5.1 fixtures cover route state and persistence, not live beta rendering.
"""
import unittest

from test_addon import Client
from test_061 import world_quest, run_plan
from test_063 import guide_client, zone, order, primitive
from test_routes import catalogue, map_canvas, guide


def identity(c):
    c.lua.execute('''
      function UnitClass() return 'Shaman','SHAMAN',7 end
      function UnitRace() return 'Orc','Orc',2 end
      bit = {lshift=function(value,n) return value*2^n end,
             band=function(a,b)
               local value,power=0,1
               while a>0 and b>0 do
                 if a%2==1 and b%2==1 then value=value+power end
                 a,b,power=math.floor(a/2),math.floor(b/2),power*2
               end
               return value
             end}
    ''')
    c.ns.ReadProfile()


def class_client():
    c = guide_client(2); identity(c)
    # These tests exercise the explicit opt-out -> opt-in transition, rather
    # than the default (on since 0.8.18).
    c.ns.SetOption('classQuests', False)
    catalogue(c, {900: world_quest('First', xp=100),
                  901: world_quest('Second', xp=100),
                  902: world_quest('Shaman task', classMask=64, xp=200),
                  903: world_quest('Mage task', classMask=128, xp=300),
                  904: world_quest('Other faction', side='Alliance', xp=300),
                  905: world_quest('Other race', raceMask=32, xp=300)})
    return c


def ids(stages):
    return {s.id for s in stages.values()}


def resume(c, legacy=False):
    c.ns.handlers.PLAYER_LOGOUT()
    saved = primitive(c.ns.db)
    saved_character = primitive(c.ns.char)
    if legacy:
        saved_character['guideState']['addon'] = '0.8.8'
        saved_character['guideState']['guide'].pop('classQuestScope', None)
        saved_character['guideState']['guide']['records'] = {
            i: r for i, r in saved_character['guideState']['guide']['records'].items() if r['id'] != 902}
    fresh = Client(quests=(), saved_variables=saved, saved_character=saved_character)
    fresh.guide_environment(level=12); identity(fresh)
    fresh.lua.globals().grouped, fresh.lua.globals().peer = False, None
    fresh.ns.UpdateRoster(); map_canvas(fresh)
    fresh.ns.catalogue = fresh.lua.table_from(primitive(c.ns.catalogue), recursive=True)
    fresh.ns.handlers.PLAYER_LOGIN(); run_plan(fresh)
    return fresh


class OptionalClassGuideTests(unittest.TestCase):
    def test_level_26_mage_class_guide_renders_with_incomplete_shopping_metadata(self):
        c = Client(quests=(), use_catalogue=True)
        c.guide_environment(level=26)
        c.lua.execute('''
          bit = {lshift=function(value,n) return value*2^n end,
            band=function(a,b)
              local result,power=0,1
              while a>0 and b>0 do
                if a%2==1 and b%2==1 then result=result+power end
                a,b,power=math.floor(a/2),math.floor(b/2),power*2
              end
              return result
            end}
        ''')
        c.ns.profile.classID, c.ns.profile.raceID, c.ns.profile.faction = 8, 1, 'Alliance'

        # Quest 8928 is in the shipped Mage line and has a buyable item with
        # no published quantity. It must not prevent the guide card rendering.
        c.ns.SetFilter('classquests')
        self.assertEqual(c.ns.ui.visibleCards, 1)
        card = c.ns.ui.cards[1]
        self.assertEqual(card.title.GetText(card.title), 'Mage class quest guide')
        self.assertGreater(card.guide.availableNow, 0)
        self.assertNotIn(21939, {row.itemID for row in c.ns.QuestShoppingList(card.guide.records).values()})

    def test_class_category_paths_filter_the_class_view_without_a_mask(self):
        c = class_client()
        classes = {1: 'warrior', 2: 'paladin', 3: 'hunter', 4: 'rogue', 5: 'priest',
                   7: 'shaman', 8: 'mage', 9: 'warlock', 11: 'druid'}
        quests = {1000 + class_id: world_quest('Class ' + name, level=12, xp=100,
                  classMask=0, categoryPath='classes/' + name)
                  for class_id, name in classes.items()}
        catalogue(c, quests)
        for class_id, name in classes.items():
            with self.subTest(class_name=name):
                c.ns.profile.classID = class_id
                self.assertTrue(c.ns.CatalogueClassCategoryAllowed(1000 + class_id, c.ns.profile))
                other_class = next(value for value in classes if value != class_id)
                c.ns.profile.classID = other_class
                self.assertFalse(c.ns.CatalogueClassCategoryAllowed(1000 + class_id, c.ns.profile)[0])

    def test_class_quests_view_lists_only_the_current_class_across_zones(self):
        c = class_client(); identity(c); c.ns.SetOption('classQuests', True)
        catalogue(c, {
            900: world_quest('Shaman line', level=12, xp=200, classMask=0, categoryPath='classes/shaman'),
            901: world_quest('Mage line', level=12, xp=200, classMask=0, categoryPath='classes/mage'),
            902: world_quest('Ordinary quest', level=12, xp=200, classMask=0, categoryPath='kalimdor/test-coast'),
        })
        c.ns.SetFilter('classquests')
        self.assertEqual({item.id for item in c.ns.LibraryItems().values()}, {900})
        self.assertEqual(c.ns.LibraryItems()[1].quest.title, 'Shaman line')
        c.ns.Render()
        self.assertEqual(c.ns.ui.visibleCards, 1)
        self.assertEqual(c.ns.ui.cards[1].detailsButton.caption.GetText(c.ns.ui.cards[1].detailsButton.caption),
                         'Follow')
        self.assertEqual(c.ns.ui.cards[1].guide.classLineGuide, True)

    def test_class_guide_unifies_known_class_quests_and_reports_next_level(self):
        c = class_client(); identity(c); c.ns.SetOption('classQuests', False)
        catalogue(c, {
            900: world_quest('Shaman Initiation', level=12, minLevel=12, xp=200, classMask=0,
                categoryPath='classes/shaman', seriesRoot=900, series=[900, 901]),
            901: world_quest('Shaman Trial', level=15, minLevel=15, xp=200, classMask=0,
                categoryPath='classes/shaman', seriesRoot=900, series=[900, 901]),
            902: world_quest('Mage Initiation', level=12, minLevel=12, xp=200, classMask=0,
                categoryPath='classes/mage'),
        })
        c.ns.profile.level = 3
        c.lua.globals().playerLevel = 3
        guide = c.ns.BuildClassQuestsGuide()
        self.assertEqual(guide.classLineGuide, True)
        self.assertEqual(guide.classQuestCount, 2)
        self.assertEqual({record.id for record in guide.records.values()}, {900, 901})
        self.assertEqual(guide.availableNow, 0)
        self.assertEqual(guide.nextLevel, 12)
        c.ns.SetFilter('classquests'); c.ns.Render()
        self.assertEqual(c.ns.ui.visibleCards, 1)
        self.assertEqual(c.ns.ui.cards[1].title.GetText(c.ns.ui.cards[1].title), 'Shaman class quest guide')
        self.assertIn('Reach level 12', c.ns.ui.cards[1].reason.GetText(c.ns.ui.cards[1].reason))
        c.ns.ui.cards[1].detailsButton.OnClick(); run_plan(c)
        self.assertTrue(c.ns.routeSelection.classLineGuide)
        self.assertIn('Reach level 12', c.ns.routePaused)
        route = c.ns.BuildGuideRoute(guide, False, False)
        self.assertEqual(len(route.stops), 0)
        self.assertIn('Reach level 12', route.pendingReason)
        c.ns.profile.level = 15
        guide = c.ns.BuildClassQuestsGuide()
        first = c.ns.BuildLevelingRoute(guide, False, False)
        self.assertEqual({stop.id for stop in first.stops.values()}, {900})
        c.lua.globals().finished[900] = True
        later = c.ns.BuildLevelingRoute(guide, False, False)
        self.assertEqual({stop.id for stop in later.stops.values()}, {901})

    def test_class_quests_put_available_steps_first_and_label_them(self):
        c = class_client(); identity(c); c.ns.SetOption('classQuests', True)
        catalogue(c, {
            900: world_quest('Shaman Initiation', level=12, xp=200, classMask=0,
                categoryPath='classes/shaman', seriesRoot=900, series=[900, 901]),
            901: world_quest('Shaman Trial', level=12, xp=200, classMask=0,
                categoryPath='classes/shaman', previousQuest=900, seriesRoot=900, series=[900, 901]),
        })
        c.ns.SetFilter('classquests'); c.ns.Render()
        items = c.ns.LibraryItems()
        self.assertEqual([item.id for item in items.values()], [900, 901])
        self.assertTrue(items[1].availableNow)
        self.assertFalse(items[2].availableNow)
        self.assertEqual(c.ns.ui.visibleCards, 1)
        self.assertIn('available now', c.ns.ui.cards[1].reason.GetText(c.ns.ui.cards[1].reason).lower())

    def test_class_questline_routes_the_full_known_series_for_the_current_class(self):
        c = class_client(); identity(c); c.ns.SetOption('classQuests', True)
        catalogue(c, {
            900: world_quest('Shaman Initiation', level=12, xp=200, classMask=0,
                categoryPath='classes/shaman', seriesRoot=900, seriesName='Shaman Initiation', series=[900, 901]),
            901: world_quest('Shaman Trial', level=12, xp=200, classMask=0,
                categoryPath='classes/shaman', previousQuest=900, seriesRoot=900,
                seriesName='Shaman Initiation', series=[900, 901]),
        })
        guide = c.ns.BuildClassQuestGuide(900)
        self.assertEqual(guide.mode, 'chain')
        self.assertTrue(guide.personal)
        self.assertEqual([record.id for record in guide.records.values()], [900, 901])
        first = c.ns.BuildLevelingRoute(guide, False, False)
        self.assertEqual({stop.id for stop in first.stops.values()}, {900})
        c.lua.globals().finished[900] = True
        later = c.ns.BuildLevelingRoute(guide, False, False)
        self.assertEqual({stop.id for stop in later.stops.values()}, {901})
        c.ns.profile.classID = 8
        self.assertIsNone(c.ns.BuildClassQuestGuide(900))

    def test_disabled_class_work_remains_in_compiled_scope_but_not_route(self):
        c = class_client(); g = zone(c)
        self.assertFalse(c.ns.Option('classQuests'))
        self.assertEqual({r.id for r in g.records.values()}, {900, 901, 902})
        self.assertEqual(g.coverage.quests, 2)
        route = c.ns.BuildFixedGuideRoute(g, False)
        self.assertEqual(ids(g.fixedPlan), {900, 901, 902})
        self.assertEqual(ids(route.stops), {900, 901})
        self.assertEqual(ids(route.previewStops), {900, 901})
        self.assertFalse(c.ns.GuideQuestSkipped(902))
        self.assertFalse(c.ns.Completed(902))

    def test_initial_checkbox_state_does_not_change_compiled_order(self):
        a, b = class_client(), class_client()
        b.ns.SetOption('classQuests', True)
        ga, gb = zone(a), zone(b)
        a.ns.GenerateFixedGuide(ga, False); b.ns.GenerateFixedGuide(gb, False)
        self.assertEqual(order(ga), order(gb))

    def test_class_category_joins_its_mapped_pickup_zone(self):
        c = class_client(); q = c.ns.catalogue.quests[902]
        q.categoryPath, q.mapID, q.zone = 'classes/shaman', None, None
        g = zone(c)
        self.assertIn(902, {r.id for r in g.records.values()})
        c.ns.ActivateRoute(g)
        self.assertNotIn(902, ids(c.ns.selectedRoute.stops))
        c.ns.SetOption('classQuests', True)
        self.assertIn(902, ids(c.ns.selectedRoute.stops))
        self.assertEqual(c.ns.routeSelection.zone, 'Test Coast')

    def test_class_category_without_primary_pickup_is_not_assigned_by_guess(self):
        c = class_client(); q = c.ns.catalogue.quests[902]
        q.categoryPath, q.mapID, q.zone, q.starts = 'classes/shaman', None, None, c.lua.table()
        self.assertNotIn(902, {r.id for r in zone(c).records.values()})

    def test_shipped_parchment_enters_durotar_scope_for_an_orc_shaman(self):
        c = Client(quests=(), use_catalogue=True); c.guide_environment(level=3); identity(c)
        c.ns.SetOption('classQuests', False)
        c.lua.globals().grouped = False; c.ns.UpdateRoster()
        records = c.ns.LevelingGuideRecords('level-zone:kalimdor/durotar')
        self.assertIn(3089, {r.id for r in records.values()})
        self.assertFalse(c.ns.ClassQuestEnabled(3089))
        c.ns.db.config.classQuests = True
        self.assertTrue(c.ns.ClassQuestEnabled(3089))

    def test_toggle_updates_arrow_map_and_preview_without_reordering(self):
        c = class_client(); g = zone(c); c.ns.ActivateRoute(g)
        before = order(g)
        c.lua.globals().WorldMapFrame.SetMapID(c.lua.globals().WorldMapFrame, 501)
        c.ns.ShowGuideQuestList(g)
        c.ns.SetOption('classQuests', True)
        self.assertIn(902, ids(c.ns.selectedRoute.stops))
        self.assertEqual(c.ns.selectedRoute.eligibleMappedQuests, 3)
        self.assertIn(902, ids(c.ns.guideQuestList.visiblePlan))
        self.assertIn('3 quests', c.ns.guideQuestList.summary.text)
        c.ns.SetOption('classQuests', False)
        self.assertNotIn(902, ids(c.ns.selectedRoute.stops))
        self.assertNotIn(902, ids(c.ns.guideQuestList.visiblePlan))
        self.assertIn('2 quests', c.ns.guideQuestList.summary.text)
        self.assertEqual(order(g), before)
        self.assertEqual(ids(c.ns.guideQuestList.plan), {900, 901, 902})
        self.assertFalse(c.ns.GuideQuestSkipped(902))

    def test_toggle_applies_even_while_dashboard_resize_defers_render(self):
        c = class_client(); g = zone(c); c.ns.ActivateRoute(g)
        c.ns.ui.resizing = True
        c.ns.SetOption('classQuests', True)
        self.assertIn(902, ids(c.ns.selectedRoute.stops))
        c.ns.SetOption('classQuests', False)
        self.assertNotIn(902, ids(c.ns.selectedRoute.stops))
        self.assertTrue(c.ns.ui.resizeDirty)

    def test_checked_box_never_overrides_class_faction_or_race_requirements(self):
        c = class_client(); c.ns.SetOption('classQuests', True)
        g = zone(c); c.ns.ActivateRoute(g)
        self.assertEqual(ids(g.fixedPlan), {900, 901, 902})
        self.assertEqual(ids(c.ns.selectedRoute.stops), {900, 901, 902})

    def test_ready_accepted_class_quest_still_requires_checkbox(self):
        c = class_client(); g = zone(c); c.ns.ActivateRoute(g)
        c.ns.active[902], c.ns.readyToTurnIn[902] = 'Shaman task', True
        self.assertFalse(c.ns.LevelingWorkAllowed(902, c.ns.self))
        c.ns.SetOption('classQuests', True)
        stages = [s.kind for s in c.ns.selectedRoute.stops.values() if s.id == 902]
        self.assertEqual(stages, ['t'])
        c.ns.SetOption('classQuests', False)
        self.assertNotIn(902, ids(c.ns.selectedRoute.stops))

    def test_disabled_class_quest_does_not_get_catchup_override(self):
        c = class_client(); g = zone(c)
        g.catchupRequired = c.lua.table_from({902: True})
        self.assertNotIn(902, ids(c.ns.BuildFixedGuideRoute(g, False).stops))

    def test_completed_normal_work_can_reopen_remaining_optional_class_steps(self):
        c = class_client(); g = zone(c); c.ns.ActivateRoute(g)
        c.lua.execute('finished[900]=true;finished[901]=true')
        c.ns.Refresh(); self.assertTrue(c.ns.selectedRoute.complete)
        before = order(g)
        c.ns.SetOption('classQuests', True)
        self.assertEqual(ids(c.ns.selectedRoute.stops), {902})
        self.assertEqual(c.ns.navigation.state.stop.id, 902)
        self.assertEqual(order(g), before)

    def test_manual_class_skip_survives_toggle_without_completion_credit(self):
        c = class_client(); c.ns.SetOption('classQuests', True)
        c.lua.execute('finished[900]=true;finished[901]=true')
        g = zone(c); c.ns.ActivateRoute(g); c.ns.UpdateNavigation()
        self.assertEqual(c.ns.selectedRoute.stops[1].id, 902)
        c.ns.SkipGuide('quest')
        c.ns.SetOption('classQuests', False); c.ns.SetOption('classQuests', True)
        self.assertTrue(c.ns.GuideQuestSkipped(902))
        self.assertFalse(c.ns.Completed(902))
        self.assertFalse(ids(c.ns.selectedRoute.stops))

    def test_disabling_class_work_does_not_complete_a_normal_childs_prerequisite(self):
        c = class_client(); c.ns.catalogue.quests[901].previousQuest = 902
        g = zone(c); c.ns.ActivateRoute(g)
        self.assertNotIn(901, ids(c.ns.selectedRoute.stops))
        self.assertNotIn(902, ids(c.ns.selectedRoute.stops))
        c.ns.SetOption('classQuests', True)
        self.assertIn(902, ids(c.ns.selectedRoute.stops))
        self.assertNotIn(901, ids(c.ns.selectedRoute.stops))
        c.lua.globals().finished[902] = True; c.ns.Refresh()
        self.assertIn(901, ids(c.ns.selectedRoute.stops))

    def test_class_followup_still_requires_an_efficient_chain(self):
        c = class_client(); c.ns.catalogue.quests[900].level = 1
        c.ns.catalogue.quests[902].previousQuest = 900
        self.assertFalse(c.ns.LevelingValue(900)[0])
        c.ns.SetOption('classQuests', True)
        value, reason = c.ns.LevelingValue(900)
        self.assertFalse(value); self.assertIn('Chain worth', reason)

    def test_npc_autoaccept_respects_checkbox_even_for_personal_guide(self):
        c = class_client(); g = zone(c); c.ns.ActivateRoute(g)
        c.lua.execute("function UnitGUID() return 'Creature-0-1-2-3-123-ABC' end")
        c.ns.catalogue.quests[902].starts[1].entityID = 123
        c.ns.RecordNPCOfferAvailability(c.lua.table_from([{'questID': 902}], recursive=True), True)
        self.assertFalse(c.ns.CanAutoAcceptGuideQuest(902))
        g.personal = True
        self.assertFalse(c.ns.CanAutoAcceptGuideQuest(902))
        c.ns.SetOption('classQuests', True)
        self.assertTrue(c.ns.CanAutoAcceptGuideQuest(902))

    def test_unstarted_preview_and_xp_follow_checkbox_without_deleting_steps(self):
        c = class_client(); g = zone(c); c.ns.ShowGuideQuestList(g); c.drain()
        self.assertIsNone(c.ns.routeSelection)
        self.assertEqual(ids(c.ns.guideQuestList.plan), {900, 901, 902})
        self.assertEqual(ids(c.ns.guideQuestList.visiblePlan), {900, 901})
        self.assertEqual(c.ns.GuideXPProjection(g).reward, 200)
        c.ns.SetOption('classQuests', True)
        self.assertEqual(ids(c.ns.guideQuestList.visiblePlan), {900, 901, 902})
        self.assertEqual(c.ns.GuideXPProjection(g).reward, 400)
        for row in c.ns.guideQuestList.rows.values():
            if row.IsShown(row): self.assertEqual(int(row.number.text), row.stop.guideStep)

    def test_reload_keeps_optional_scope_and_saved_order_with_checkbox_off(self):
        c = class_client(); g = zone(c); c.ns.ActivateRoute(g)
        before = order(g)
        fresh = resume(c)
        self.assertFalse(fresh.ns.Option('classQuests'))
        self.assertEqual(order(fresh.ns.routeSelection), before)
        self.assertNotIn(902, ids(fresh.ns.selectedRoute.stops))
        fresh.ns.SetOption('classQuests', True)
        self.assertIn(902, ids(fresh.ns.selectedRoute.stops))
        self.assertEqual(order(fresh.ns.routeSelection), before)

    def test_older_saved_zone_scope_recovers_class_work_once(self):
        c = class_client(); c.ns.ActivateRoute(zone(c))
        fresh = resume(c, legacy=True)
        self.assertEqual(ids(fresh.ns.routeSelection.fixedPlan), {900, 901, 902})
        self.assertTrue(fresh.ns.routeSelection.classQuestScope)
        self.assertNotIn(902, ids(fresh.ns.selectedRoute.stops))
        fresh.ns.SetOption('classQuests', True)
        self.assertIn(902, ids(fresh.ns.selectedRoute.stops))

    def test_adaptive_guide_also_keeps_records_but_filters_active_work(self):
        c = class_client(); c.ns.db.config.fixedZoneGuides = False
        g = zone(c); c.ns.ActivateRoute(g)
        self.assertIn(902, {r.id for r in c.ns.routeSelection.records.values()})
        self.assertNotIn(902, ids(c.ns.selectedRoute.stops))
        c.ns.SetOption('classQuests', True)
        self.assertIn(902, ids(c.ns.selectedRoute.previewStops))
        c.ns.SetOption('classQuests', False)
        self.assertNotIn(902, ids(c.ns.selectedRoute.stops))
        self.assertNotIn(902, ids(c.ns.selectedRoute.previewStops))

    def test_disabled_optional_quests_cannot_make_a_single_quest_into_a_zone_guide(self):
        c = class_client()
        catalogue(c, {900: world_quest('Normal'), 902: world_quest('Class', classMask=64)})
        self.assertEqual(len(c.ns.LevelingGuideChoices()), 0)
        c.ns.SetOption('classQuests', True)
        self.assertEqual(len(c.ns.LevelingGuideChoices()), 1)

    def test_adaptive_completion_ignores_disabled_class_work_without_credit(self):
        c = class_client(); c.ns.db.config.fixedZoneGuides = False
        c.ns.ActivateRoute(zone(c))
        c.lua.execute('finished[900]=true;finished[901]=true')
        c.ns.Refresh()
        self.assertTrue(c.ns.selectedRoute.complete)
        self.assertFalse(c.ns.Completed(902))
        c.ns.SetOption('classQuests', True)
        self.assertIn(902, ids(c.ns.selectedRoute.stops))

    def test_disabled_class_progress_does_not_choose_party_focus(self):
        c = class_client(); c.lua.execute('finished[900]=true;finished[901]=true')
        profile = primitive(c.ns.profile)
        c.ns.members['Bob-TestRealm'] = c.lua.table_from({'active': {}, 'completed': {901: True, 902: True},
            'historyChecked': {900: True, 901: True, 902: True}, 'historyRevision': 1,
            'activeRevision': 1, 'completionRevision': 1, 'profile': profile}, recursive=True)
        profiles = c.lua.table_from([{'key': c.ns.self, 'name': 'You', 'profile': profile, 'synced': True},
            {'key': 'Bob-TestRealm', 'name': 'Bob', 'profile': profile, 'synced': True}], recursive=True)
        c.ns.PartyProfiles = c.lua.eval('function(people) return function() return people end end')(profiles)
        records = c.lua.table_from([c.ns.CatalogueRecord(i) for i in (900, 901, 902)])
        self.assertEqual(c.ns.GuideFocus(records), 'Bob-TestRealm')
        c.ns.db.config.classQuests = True
        self.assertEqual(c.ns.GuideFocus(records), c.ns.self)


def hub_client(xs=(.20, .25, .29), scale=1000):
    c = guide_client(3)
    data = {}
    for id, x in zip((900, 901, 902), xs):
        data[id] = world_quest('Hub ' + str(id), prerequisitesRead=True,
            starts=[{'mapID': 501, 'x': x, 'y': .2, 'name': 'NPC ' + str(id), 'npc': True, 'entityID': id}],
            objectives=[{'mapID': 501, 'x': .8, 'y': .8, 'name': 'Target ' + str(id), 'action': 'kill'}])
    catalogue(c, data)
    if scale is not None:
        c.lua.globals().hubScale = scale
        c.lua.execute('C_Map.GetMapWorldSize=function() return hubScale,hubScale end')
    g = guide(c, (900, 901, 902), key='level-zone:kalimdor/test-coast')
    g.mode, g.fullGuide, g.fixedRoute, g.zone, g.mapID, g.homeMapID = 'zone', True, True, 'Test Coast', 501, 501
    plan = []
    for id in (900, 901, 902):
        q = c.ns.CatalogueQuest(id)
        for kind, points in [('a', q.starts), ('q', q.objectives), ('t', q.ends)]:
            stop = c.ns.PublishedGuideStop(c.ns.CatalogueRecord(id), points[1], kind)
            stop.guideStep = len(plan) + 1
            plan.append(stop)
    g.fixedPlan = c.lua.table_from(plan)
    return c, g


def steps(route):
    return [(s.id, s.kind) for s in route.stops.values()]


class NearbyPickupTests(unittest.TestCase):
    def test_groups_only_accepts_and_preserves_saved_plan_and_all_other_steps(self):
        c, g = hub_client(); before = order(g)
        route = c.ns.BuildGuideRoute(g, False)
        self.assertEqual(steps(route)[:3], [(900, 'a'), (901, 'a'), (902, 'a')])
        self.assertEqual(route.hubPickupCount, 3)
        self.assertEqual([(s.id, s.kind) for s in route.stops.values() if s.kind != 'a'],
                         [(s.id, s.kind) for s in g.fixedPlan.values() if s.kind != 'a'])
        self.assertEqual(order(g), before)
        self.assertEqual(steps(route), [(s.id, s.kind) for s in route.previewStops.values()])

    def test_anchor_radius_does_not_chain_into_a_larger_hub(self):
        c, g = hub_client((.20, .28, .35))
        route = c.ns.BuildGuideRoute(g, False)
        self.assertEqual(steps(route)[:3], [(900, 'a'), (901, 'a'), (900, 'q')])
        self.assertEqual(route.hubPickupCount, 2)
        self.assertGreater(steps(route).index((902, 'a')), steps(route).index((900, 't')))

    def test_same_coordinates_on_large_map_are_not_a_nearby_hub(self):
        for scale in (None, 6000):
            with self.subTest(scale=scale):
                c, g = hub_client(scale=scale)
                route = c.ns.BuildGuideRoute(g, False)
                self.assertEqual(steps(route), [(s.id, s.kind) for s in g.fixedPlan.values()])
                self.assertIsNone(route.hubPickupCount)

    def test_turned_off_setting_keeps_original_runtime_pickup_order(self):
        c, g = hub_client(); c.ns.db.config.nearbyPickups = False
        self.assertEqual(steps(c.ns.BuildGuideRoute(g, False)), [(s.id, s.kind) for s in g.fixedPlan.values()])
        c.ns.ActivateRoute(g); c.ns.SetOption('nearbyPickups', True)
        self.assertEqual(steps(c.ns.selectedRoute)[:3], [(900, 'a'), (901, 'a'), (902, 'a')])
        c.ns.SetOption('nearbyPickups', False)
        self.assertEqual(steps(c.ns.selectedRoute), [(s.id, s.kind) for s in g.fixedPlan.values()])

    def test_prerequisites_npc_absence_and_unknown_offers_are_not_promoted(self):
        for field, value in [('previousQuest', 999), ('prerequisitesUnverified', True)]:
            with self.subTest(field=field):
                c, g = hub_client(); c.ns.catalogue.quests[901][field] = value
                route = c.ns.BuildGuideRoute(g, False)
                self.assertNotIn((901, 'a'), steps(route)[:2])
        c, g = hub_client()
        c.lua.execute("function UnitGUID() return 'Creature-0-1-2-3-901-ABC' end")
        c.ns.RecordNPCOfferAvailability(c.lua.table(), True)
        route = c.ns.BuildGuideRoute(g, False)
        self.assertNotIn(901, ids(route.stops))
        self.assertFalse(c.ns.Completed(901))

    def test_manual_skips_and_closed_class_checkbox_cannot_return_through_grouping(self):
        c, g = hub_client(); identity(c)
        c.ns.SetOption('classQuests', False)
        c.ns.catalogue.quests[901].classMask = 64
        c.ns.char.guideSkips.quests[902] = True
        route = c.ns.BuildGuideRoute(g, False)
        self.assertEqual(ids(route.stops), {900})
        c.ns.SetOption('classQuests', True)
        route = c.ns.BuildGuideRoute(g, False)
        self.assertEqual(steps(route)[:2], [(900, 'a'), (901, 'a')])
        self.assertNotIn(902, ids(route.stops))

    def test_cross_zone_unknown_and_secret_locations_are_not_grouped(self):
        for field, value in [('mapID', 502), ('unknownLocation', True), ('x', 'secret')]:
            with self.subTest(field=field):
                c, g = hub_client()
                route = c.lua.table_from({'stops': c.lua.table_from([s for s in g.fixedPlan.values()])})
                route.stops[4][field] = c.lua.globals().secret if value == 'secret' else value
                grouped = c.ns.GroupNearbyGuidePickups(g, route)
                self.assertNotIn((901, 'a'), steps(grouped)[:2])

    def test_escort_accept_and_started_escort_are_never_interrupted(self):
        c, g = hub_client(); c.ns.catalogue.quests[900].objectives[1].action = 'escort'
        g.fixedPlan[2].action = 'escort'
        route = c.ns.BuildGuideRoute(g, False)
        self.assertEqual(steps(route)[:2], [(900, 'a'), (900, 'q')])
        c.ns.active[900] = 'Hub 900'
        g.npcVisitPickupIDs = c.lua.table_from([901, 902])
        c.ns.npcPickupLocations[901] = c.lua.table_from({'mapID': 501, 'x': .2, 'y': .2,
            'entityID': 901, 'name': 'NPC 901'})
        route = c.ns.BuildGuideRoute(g, False)
        self.assertEqual(steps(route)[0], (900, 'q'))
        c.ns.routeSelection, c.ns.selectedRoute = g, route
        self.assertFalse(c.ns.CanAutoAcceptGuideQuest(901))

    def test_accepting_bundle_resumes_unchanged_objective_and_turnin_order(self):
        c, g = hub_client(); c.ns.ActivateRoute(g); before = order(g)
        for i, id in enumerate((900, 901, 902), start=1):
            c.lua.globals().entries[i] = c.lua.table_from({'questID': id, 'title': 'Hub ' + str(id)})
            c.ns.handlers.QUEST_ACCEPTED(i, id)
        c.drain()  # Process the coalesced personal quest-log refresh.
        self.assertEqual(steps(c.ns.selectedRoute), [(s.id, s.kind) for s in g.fixedPlan.values() if s.kind != 'a'])
        self.assertEqual(order(g), before)

    def test_npc_dialog_refresh_does_not_regenerate_the_route(self):
        c, g = hub_client(); c.ns.ActivateRoute(g); before = order(g)
        c.lua.execute("function UnitGUID() return 'Creature-0-1-2-3-900-ABC' end; C_Map.GetPlayerMapPosition=function() return {GetXY=function() return .2,.2 end} end")
        c.ns.offered[900] = True
        c.ns.RecordNPCOfferAvailability(c.lua.table_from([{'questID': 900}], recursive=True), True)
        c.ns.UpdateSelectedRoute(None, c.ns.NewQuestQuery())
        self.assertEqual(steps(c.ns.selectedRoute)[:3], [(900, 'a'), (901, 'a'), (902, 'a')])
        self.assertEqual(order(g), before)
        self.assertIsNone(c.ns.routePlanning)

    def test_runtime_pickup_pass_is_shared_by_zone_chain_circuit_and_dungeon_guides(self):
        for mode in ('zone', 'chain', 'circuit', 'dungeon'):
            with self.subTest(mode=mode):
                c, g = hub_client(); g.mode = mode
                before = order(g)
                route = c.ns.BuildGuideRoute(g, False)
                self.assertEqual(steps(route)[:3], [(900, 'a'), (901, 'a'), (902, 'a')])
                self.assertEqual(order(g), before)

    def test_nonfixed_generic_guides_use_same_pickup_pass_without_new_scope(self):
        c, g = hub_client(); g.fixedRoute, g.fullGuide = False, False
        route = c.ns.BuildGuideRoute(g, False)
        self.assertEqual(route.hubPickupCount, 3)
        self.assertEqual(ids(route.stops), {900, 901, 902})


if __name__ == '__main__': unittest.main()
