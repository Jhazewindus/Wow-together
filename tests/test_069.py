"""Behavior-preserving performance regressions; host Lua 5.1, not beta FPS."""
import json
import unittest
from pathlib import Path

from test_063 import guide_client, learner, learn
from test_061 import world_quest
from test_068 import maps, traveling
from test_routes import catalogue, guide


def history_counter(c):
    c.lua.execute('''
    historyReads={}
    C_QuestLog.IsQuestFlaggedCompleted=function(id)
      historyReads[id]=(historyReads[id] or 0)+1
      if historyPrivate then return secret end
      return finished[id] or false
    end
    ''')


class QueryTests(unittest.TestCase):
    def test_completion_reuse_is_limited_to_one_read_pass_including_unknown(self):
        c=guide_client(2);history_counter(c)
        query=c.ns.NewQuestQuery()
        self.assertFalse(c.ns.Completed(900,query))
        self.assertFalse(c.ns.Completed(900,query))
        self.assertEqual(c.lua.globals().historyReads[900],1)
        c.lua.globals().finished[900]=True
        self.assertTrue(c.ns.Completed(900,c.ns.NewQuestQuery()))
        c.lua.globals().historyPrivate=True
        query=c.ns.NewQuestQuery()
        self.assertIsNone(c.ns.Completed(900,query))
        self.assertIsNone(c.ns.Completed(900,query))
        self.assertEqual(c.lua.globals().historyReads[900],3)
        c.lua.globals().historyPrivate=False
        self.assertTrue(c.ns.Completed(900,c.ns.NewQuestQuery()))

    def test_browser_reads_each_history_once_and_refreshes_level_and_progress(self):
        c=guide_client(8);history_counter(c)
        choices=c.ns.LevelingGuideChoices()
        self.assertEqual(choices[1].completed,0)
        self.assertTrue(all(n==1 for n in c.lua.globals().historyReads.values()))
        c.lua.globals().finished[900]=True
        self.assertEqual(c.ns.LevelingGuideChoices()[1].completed,1)
        c.ns.profile.level=20
        self.assertEqual(len(c.ns.LevelingGuideChoices()),0)

    def test_fixed_progress_reads_once_per_quest_and_restores_abandoned_pickup(self):
        c=guide_client(12);g=c.ns.LevelingGuideChoices()[1]
        c.ns.GenerateFixedGuide(g,False);history_counter(c)
        first=c.ns.BuildFixedGuideRoute(g,False)
        self.assertEqual(first.remainingSteps,36)
        self.assertTrue(all(n==1 for n in c.lua.globals().historyReads.values()))
        id=first.stops[1].id;c.ns.active[id]='Accepted'
        second=c.ns.BuildFixedGuideRoute(g,False)
        self.assertNotIn((id,'a'),[(s.id,s.kind) for s in second.stops.values()])
        c.ns.active[id]=None
        third=c.ns.BuildFixedGuideRoute(g,False)
        self.assertEqual((third.stops[1].id,third.stops[1].kind),(id,'a'))

    def test_dashboard_reuses_history_for_shopping_and_route_progress(self):
        c=guide_client(8);g=c.ns.LevelingGuideChoices()[1];c.ns.ActivateRoute(g)
        c.ns.filter='guides';history_counter(c);c.ns.Render()
        self.assertTrue(all(n==1 for n in c.lua.globals().historyReads.values()))
        before=c.ns.selectedRoute.remainingSteps
        id=c.ns.selectedRoute.stops[1].id;c.lua.globals().finished[id]=True;c.ns.Render()
        self.assertEqual(c.ns.selectedRoute.remainingSteps,before-3)

    def test_shopping_keeps_quantities_and_skips_irrelevant_history(self):
        c=guide_client(3);g=guide(c,(900,901,902));history_counter(c)
        c.ns.catalogue.quests[901].requiredItems=c.lua.table_from([
            {'itemID':123,'name':'Supply','quantity':4,'buyable':True}],recursive=True)
        items=c.ns.QuestShoppingList(g.records)
        self.assertEqual(items[1].need,4)
        self.assertIsNone(c.lua.globals().historyReads[900])
        self.assertIsNone(c.lua.globals().historyReads[902])
        c.lua.globals().finished[901]=True
        self.assertEqual(len(c.ns.QuestShoppingList(g.records)),0)


class CompilerTests(unittest.TestCase):
    def test_fixed_and_adaptive_output_match_pre_optimization_fixtures(self):
        fixtures=json.loads(Path(__file__).with_name('performance-fixtures.json').read_text())
        for fixture in fixtures['fixed']:
            c=guide_client(1);data={int(k):v for k,v in fixture['quests'].items()};catalogue(c,data)
            g=guide(c,tuple(data));g.fixedRoute=True
            c.lua.execute('C_Map.GetMapWorldSize=function() return 1000,800 end')
            c.ns.GenerateFixedGuide(g,False)
            fields=('id','kind','mapID','x','y','guideStep','unknownLocation','planNeedsReview')
            actual=[[s[k] for k in fields] for s in g.fixedPlan.values()]
            self.assertEqual(actual,fixture['stages'],fixture['seed'])
        fixture=fixtures['adaptive'];c=guide_client(1)
        data={int(k):v for k,v in fixture['quests'].items()};catalogue(c,data)
        g=guide(c,tuple(data));g.fullGuide=True;g.mode='zone';g.homeMapID=501
        route=c.ns.BuildLevelingRoute(g,False,False)
        self.assertEqual([[s[k] for k in ('id','kind','mapID','x','y')] for s in route.stops.values()],fixture['stops'])

    def test_compiler_rechecks_scale_and_prerequisites_after_cooperative_yield(self):
        c=guide_client(30);g=c.ns.LevelingGuideChoices()[1];c.lua.globals().perfNS=c.ns;c.lua.globals().perfGuide=g
        c.lua.execute('''
        scaleReads,changedScaleReads,changedLearnReads=0,0,0
        C_Map.GetMapWorldSize=function()
          scaleReads=scaleReads+1
          if perfChanged then changedScaleReads=changedScaleReads+1;return secret,secret end
          return 1000,800
        end
        local original=perfNS.LearnedPrerequisiteIDs
        perfNS.LearnedPrerequisiteIDs=function(id)
          if perfChanged then changedLearnReads=changedLearnReads+1 end
          return original(id)
        end
        perfJob=coroutine.create(function() return perfNS.GenerateFixedGuide(perfGuide,true) end)
        assert(coroutine.resume(perfJob))
        assert(coroutine.status(perfJob)=='suspended')
        perfChanged=true
        while coroutine.status(perfJob)~='dead' do assert(coroutine.resume(perfJob)) end
        ''')
        self.assertGreater(c.lua.globals().changedScaleReads,0)
        self.assertGreater(c.lua.globals().changedLearnReads,0)
        self.assertEqual(len(g.fixedPlan),90)


class LearningIndexTests(unittest.TestCase):
    def test_unrelated_rules_need_no_build_query_and_revisions_keep_contradictions(self):
        c=learner();learn(c)
        c.lua.globals().perfNS=c.ns
        c.lua.execute('''
        buildReads=0
        local original=GetBuildInfo
        GetBuildInfo=function() buildReads=buildReads+1;return original() end
        ''')
        self.assertIsNone(c.ns.LearnedQuestRule(999))
        self.assertEqual(len(c.ns.LearnedFollowers(999)),0)
        self.assertEqual(c.lua.globals().buildReads,0)
        self.assertEqual(list(c.ns.LearnedFollowers(900).values()),[901])
        c.lua.execute('''
        local saved=perfNS.db.questLearning
        local _,rule=next(saved.rules)
        local other={};for k,v in pairs(rule) do other[k]=v end
        other.previousQuest=902
        saved.rules['contradictory-fixture']=other;saved.revision=saved.revision+1
        ''')
        self.assertEqual(len(c.ns.LearnedFollowers(900)),0)
        self.assertEqual(len(c.ns.LearnedFollowers(902)),0)
        self.assertIsNone(c.ns.LearnedQuestRule(901))


class ProjectionCacheTests(unittest.TestCase):
    def test_redraw_reuses_coincident_points_but_rechecks_private_data_next_time(self):
        c=traveling();c.ns.db.config.fullRoute=True
        c.ns.selectedRoute.stops=c.lua.table_from([
            {'id':900,'kind':'q','mapID':502,'x':.2,'y':.37,'label':'Work','title':'Work'},
            {'id':900,'kind':'t','mapID':502,'x':.2,'y':.37,'label':'Return','title':'Return'}],recursive=True)
        c.lua.execute('''
        worldReads,projectionReads=0,0
        local w,p=C_Map.GetWorldPosFromMapPos,C_Map.GetMapPosFromWorldPos
        C_Map.GetWorldPosFromMapPos=function(...) worldReads=worldReads+1;return w(...) end
        C_Map.GetMapPosFromWorldPos=function(...) projectionReads=projectionReads+1;return p(...) end
        ''')
        c.ns.DrawRoute()
        self.assertEqual(c.lua.globals().worldReads,2)
        self.assertEqual(c.lua.globals().projectionReads,1)
        c.lua.execute('C_Map.GetWorldPosFromMapPos=function() return secret,secret end')
        c.ns.DrawRoute()
        self.assertEqual(c.ns.routeStats.lines,0)
        self.assertIn('unavailable',c.ns.routeStats.status)

    def test_projection_keys_preserve_nearby_distinct_coordinates(self):
        c=guide_client(2);maps(c);context=c.lua.table()
        a=c.lua.table_from({'mapID':502,'x':.2,'y':.37})
        b=c.lua.table_from({'mapID':502,'x':.200000000000001,'y':.37})
        self.assertNotEqual(c.ns.ProjectMapPoint(a,501,context).x,c.ns.ProjectMapPoint(b,501,context).x)


if __name__=='__main__': unittest.main()
