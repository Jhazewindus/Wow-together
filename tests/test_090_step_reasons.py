"""Step reason gating and one-of prerequisite regression checks."""
import unittest

from test_addon import Client
from test_routes import catalogue, guide, quest, route_client


def mage_bit_api(client):
    client.lua.execute('''
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
    client.ns.profile.classID, client.ns.profile.raceID, client.ns.profile.faction = 8, 1, 'Alliance'


class StepReasonTests(unittest.TestCase):
    def test_generic_reason_stays_in_later_and_never_becomes_current(self):
        client = route_client()
        generic = client.lua.table_from({'kind': 'status', 'label': 'Level work'})
        can_be_current, decision = client.ns.GuideReasonCanBeCurrent(generic, None)
        self.assertFalse(can_be_current)
        self.assertFalse(decision.specificBenefit)
        self.assertEqual(decision.code, 'guide-status')

    def test_normal_pickup_has_a_specific_data_derived_start_reason(self):
        client = route_client()
        catalogue(client, {900: quest('Independent leveling quest')})
        selected = guide(client, (900,))
        selected.mapID = 501
        route = client.ns.BuildLevelingRoute(selected, False, False)
        self.assertGreater(len(route.stops), 0)
        decision = client.ns.GuideDestinationDecision(route.stops[1], selected, route)
        self.assertEqual(decision.code, 'quest-start')
        self.assertIn('Accept Independent leveling quest', decision.why)
        self.assertTrue(decision.specificBenefit)
        self.assertTrue(client.ns.GuideReasonCanBeCurrent(route.stops[1], selected)[0])

    def test_research_access_routes_exactly_one_book_with_data_derived_reason(self):
        client = Client(quests=(), use_catalogue=True)
        client.guide_environment(level=26)
        mage_bit_api(client)
        client.ns.SetOption('classQuests', True)
        guide = client.ns.BuildClassQuestsGuide()

        research = client.ns.CatalogueQuest(97286)
        alternatives = {int(research.prerequisiteAny[i]) for i in range(1, len(research.prerequisiteAny) + 1)}
        chosen_list = guide.collectionDependencies[97286]
        chosen = int(chosen_list[1])
        listed = {int(record.id) for record in guide.records.values()} & alternatives
        self.assertEqual(listed, {chosen})
        self.assertEqual(guide.collectionAlternatives[chosen], 40)

        stages = client.ns.RouteStages(client.ns.CatalogueRecord(chosen), client.ns.self)
        pickup = stages[1]
        decision = client.ns.GuideDestinationDecision(pickup, guide)
        self.assertEqual(decision.code, 'chosen-branch')
        self.assertIn('One of 40 quest-start objects that unlock Research Access', decision.why)
        self.assertTrue(decision.specificBenefit)
        self.assertTrue(client.ns.GuideReasonCanBeCurrent(pickup, guide))
        self.assertEqual(client.ns.GuideStepRequirement(pickup, 1439, 212, guide),
                         'Required now for this quest chain')
        action = client.ns.GuideStepAction(pickup)
        self.assertIn('(ground object)', action)
        self.assertTrue(action.startswith('Read the '))

        client.ns.routeSelection = guide
        client.ns.SaveSelectedGuide()
        saved = client.ns.db.guideState[client.ns.self].guide
        self.assertEqual(int(saved.collectionDependencies[97286][1]), chosen)
        self.assertEqual(saved.collectionAlternatives[chosen], 40)

        client.ns.db.guideSkips[client.ns.self].quests[chosen] = True
        client.ns.profile.mapID = 1439
        client.ns.BuildLevelingRoute(guide, False, False)
        replacement = int(guide.collectionDependencies[97286][1])
        self.assertIn(replacement, alternatives)
        self.assertNotEqual(replacement, chosen)


if __name__ == '__main__':
    unittest.main()
