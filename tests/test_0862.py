"""Corrected geometry must not bypass complete-guide progression safeguards."""
import unittest
from test_063 import guide_client
from test_061 import world_quest
from test_routes import catalogue
from test_0853 import sequence
from test_0854 import fixture


def reward_loop():
    c=guide_client(3)
    catalogue(c,{i:world_quest('Quest '+str(i),minLevel=1,xp=100 if i==900 else 0)for i in (900,901,902)})
    # Combining two hand-ins saves walking, but delays the first reward until
    # after the next objective and raises the original one-quest log peak.
    points=[(900,'a',.4),(900,'q',.4),(900,'t',.7),
            (901,'a',0),(901,'q',.2),(901,'t',.7),
            (902,'a',.9),(902,'q',.1),(902,'t',.9)]
    p=c.lua.table_from([{'id':i,'kind':k,'mapID':501,'x':x,'y':0}for i,k,x in points],recursive=True)
    metric=c.lua.eval('function(a,b) return math.abs(a.x-b.x)*1000 end')
    return c,p,metric


class GeometricProtectionTests(unittest.TestCase):
    def test_shorter_loop_cannot_delay_rewards_or_increase_held_quests(self):
        c,p,cost=reward_loop();original=c.lua.table_from(list(p.values()))
        model=c.ns.NewGuideFlowModel(original,cost);before=model.evaluate(original)
        result=c.ns.ImproveFixedGeometry(p,cost,cost,False,None)
        after=model.evaluate(p)
        self.assertTrue(after.valid)
        self.assertGreater(result.protection.rejected,0)
        self.assertLessEqual(after.peakLog,before.peakLog)
        self.assertLessEqual(after.distance,before.distance)
        for s,r in before.workRewards.items():self.assertGreaterEqual(after.workRewards[s],r)
        self.assertCountEqual(sequence(p),sequence(original))
        self.assertEqual((sequence(p)[0],sequence(p)[-1]),(sequence(original)[0],sequence(original)[-1]))

    def test_safe_work_reordering_still_reduces_full_travel(self):
        c,p,cost=fixture();before=c.ns.NewGuideFlowModel(p,cost).evaluate(p)
        result=c.ns.ImproveFixedGeometry(p,cost,cost,False,None)
        self.assertGreater(result.moved+result.bundles,0)
        self.assertLess(result.protection.after.distance,before.distance)
        self.assertEqual(result.protection.after.peakLog,before.peakLog)
        self.assertTrue(result.protection.after.valid)

    def test_recovery_boundaries_are_preserved(self):
        for flag in ('unknownLocation','planNeedsReview'):
            c,p,cost=fixture();p[5][flag]=True;before=sequence(p)
            c.ns.ImproveFixedGeometry(p,cost,cost,False,None)
            self.assertEqual(sequence(p),before)

    def test_geometry_saving_is_rejected_when_published_trip_is_longer(self):
        c,p,geometry=fixture();old=sequence(p)
        cost=c.lua.eval("function(a,b) return (a.id==900 and b.id==901 and a.kind=='q' and b.kind=='q') and 100000 or math.abs(a.x-b.x)*1000, 'network-estimate' end")
        model=c.ns.NewGuideFlowModel(p,cost);before=model.evaluate(p)
        c.ns.ImproveFixedGeometry(p,geometry,cost,False,None)
        after=model.evaluate(p)
        self.assertLessEqual(after.distance,before.distance)
        self.assertTrue(after.valid)

    def test_bracket_replays_and_cooperative_execution_retain_the_same_order(self):
        def expand(c,plan):
            stops=list(plan.values())
            extras=[c.lua.table_from({'id':900,'kind':'q','mapID':501,'x':.8,'y':0})for _ in range(8)]
            return c.lua.table_from(stops[:4]+extras+stops[4:])
        a,p,cost=fixture();p=expand(a,p);opts=a.lua.table_from({'levelLow':11,'levelHigh':20})
        result=a.ns.ImproveFixedGeometry(p,cost,cost,False,None,opts)
        self.assertEqual(result.protection.replayStates,4)
        b,other,metric=fixture();other=expand(b,other);b.lua.globals().test_plan=other;b.lua.globals().test_metric=metric
        resume=b.lua.eval("""function(ns)
            local co=coroutine.create(function()return ns.ImproveFixedGeometry(test_plan,test_metric,test_metric,true,nil,{levelLow=11,levelHigh=20})end)
            return function()local ok,v=coroutine.resume(co);assert(ok,v);return coroutine.status(co),v end
        end""")(b.ns)
        count=0
        while True:
            state,_=resume();count+=1
            if state=='dead':break
        self.assertEqual(sequence(p),sequence(other))
        self.assertGreater(count,1)

    def test_invalid_input_is_not_rearranged_as_an_optimization(self):
        c,p,cost=reward_loop();c.ns.catalogue.quests[901].previousQuest=902;old=sequence(p)
        result=c.ns.ImproveFixedGeometry(p,cost,cost,False,None)
        self.assertEqual(sequence(p),old)
        self.assertFalse(result.protection.before.valid)
        self.assertEqual((result.moved,result.bundles),(0,0))
