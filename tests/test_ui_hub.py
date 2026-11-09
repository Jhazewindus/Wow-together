"""Hub navigation and click-budget controls under the host UI mock."""
import unittest

from test_addon import Client


class HubTests(unittest.TestCase):
    def test_title_icon_uses_generated_menu_icon_with_safe_fallback(self):
        client = Client(quests=(), default_guide=True)
        ns = client.ns
        ns.StepIconTexture = None
        ns.CreateUI()
        self.assertEqual(ns.ui.titleIcon.texture, "Interface\\Icons\\INV_Misc_Map_01")
        client.lua.execute('''
            local ns=...
            ns.StepIconTexture=function(name)
                assert(name=="menu")
                return "generated/menu-icon.blp"
            end
        ''', ns)
        ns.CreateUI()
        self.assertEqual(ns.ui.titleIcon.texture, "generated/menu-icon.blp")

    def test_left_rail_switches_play_group_browse_and_settings(self):
        client = Client(quests=(), default_guide=True)
        ns = client.ns
        ui = ns.ui
        self.assertEqual(ui.hubTab, "Play")
        self.assertFalse(ui.subtitle.IsShown(ui.subtitle))
        for index in range(1, 4):
            metric = ui.metrics[index]
            self.assertFalse(metric.IsShown(metric))

        ui.hubButtons.Browse.OnClick()
        self.assertEqual(ui.hubTab, "Browse")
        self.assertTrue(ui.browseRow.IsShown(ui.browseRow))
        self.assertTrue(ui.hubBrowseSearch.IsShown(ui.hubBrowseSearch))
        ui.browseButtons.dungeons.OnClick()
        self.assertEqual(ns.filter, "dungeons")
        self.assertEqual(ui.hubTab, "Browse")

        ui.hubButtons.Group.OnClick()
        self.assertEqual(ui.hubTab, "Group")
        self.assertTrue(ui.groupPage.IsShown(ui.groupPage))
        self.assertFalse(ui.scroll.IsShown(ui.scroll))

        ui.hubButtons.Settings.OnClick()
        self.assertEqual(ui.hubTab, "Settings")
        self.assertTrue(ui.settingsPage.IsShown(ui.settingsPage))

    def test_play_has_active_guide_controls_and_follow_card_action(self):
        client = Client(quests=(), default_guide=True)
        ns = client.ns
        client.lua.execute('''
            local ns = ...
            ns.routeSelection = {key="test", title="Test guide"}
            ns.selectedRoute = {stops={{id=1}}}
            ns.RecommendedItems = function()
                return {{kind="leveling", title="Next guide", category="LEVELING",
                    detail="One available route", start=function() followed=true end}}, {}
            end
        ''', ns)
        ns.RenderRecommended(ns.NewQuestQuery())
        home = ns.ui.home
        self.assertTrue(home.resume.IsShown(home.resume))
        self.assertTrue(home.resume.continueControl.IsShown(home.resume.continueControl))
        self.assertTrue(home.resume.orderControl.IsShown(home.resume.orderControl))
        self.assertTrue(home.resume.stopControl.IsShown(home.resume.stopControl))
        self.assertEqual(home.title.text, "Next for you")
        self.assertTrue(home.leveling.follow.IsShown(home.leveling.follow))
        home.leveling.follow.OnClick()
        self.assertTrue(client.lua.globals().followed)

    def test_next_for_you_is_capped_at_five_cards(self):
        client = Client(quests=(), default_guide=True)
        ns = client.ns
        client.lua.execute('''
            local ns=...
            ns.RecommendedItems=function()
                local items={{kind="leveling", title="Route", start=function() end}}
                for index=1,7 do items[#items+1]={kind="professions", title="Profession "..index,
                    start=function() end} end
                return items, {}
            end
        ''', ns)
        ns.RenderRecommended(ns.NewQuestQuery())
        home = ns.ui.home
        self.assertEqual(1 + home.professionCount + home.extraCount, 5)
        self.assertEqual(home.professionCount + home.extraCount, 4)
        self.assertTrue(home.leveling.follow.IsShown(home.leveling.follow))
        for index in range(1, 5):
            self.assertTrue(home.cards[index].follow.IsShown(home.cards[index].follow))

    def test_footer_includes_sync_data_age_and_version(self):
        client = Client(quests=(), default_guide=True)
        status = client.ns.ui.status.text
        self.assertIn("sync:", status)
        self.assertIn("quest data:", status)
        self.assertIn(str(client.ns.VERSION), status)

    def test_browse_card_exposes_only_the_follow_action(self):
        client = Client(quests=(), default_guide=True)
        ns = client.ns
        client.lua.execute('''
            local ns=...
            ns.DungeonGroups=function() return {{name="Test dungeon", ids={}, definition={runLevelLow=10,runLevelHigh=15}}} end
            ns.DungeonCollectionReadiness=function() return {count=0, unknown=0, pickupLevel=10} end
            dungeonFollowed, dungeonViewed = false, false
            ns.ShowDungeonQuests=function(group, direct) dungeonFollowed=(group.name=="Test dungeon" and direct==true) end
            ns.ShowDungeonViewer=function() dungeonViewed=true end
        ''', ns)
        ns.SetHubTab("Browse")
        ns.SetFilter("dungeons", True)
        card = ns.ui.cards[1]
        self.assertTrue(card.detailsButton.IsShown(card.detailsButton))
        self.assertEqual(card.detailsButton.caption.text, "Follow")
        for control in (card.mapButton, card.buyButton, card.catchupButton):
            self.assertFalse(control.IsShown(control))
        card.detailsButton.OnClick()
        self.assertTrue(client.lua.globals().dungeonFollowed)
        self.assertFalse(client.lua.globals().dungeonViewed)

    def test_browse_search_hits_each_category(self):
        # Each category is searched by user-visible guide/quest/profession data.
        cases = ("guides", "classquests", "dungeons", "professions", "library")
        for category in cases:
            with self.subTest(category=category):
                client = Client(quests=(), default_guide=True)
                ns, lua = client.ns, client.lua
                lua.execute('''
                    local ns=...
                    ns.hubBrowseSearch="Hidden target"
                    ns.CatalogueQuest=function(id) return {title="Hidden target", mapID=1} end
                    ns.CatalogueZone=function() return "Other zone" end
                    ns.CatalogueAllowed=function() return true end
                    ns.ClassQuestLabel=function() return nil end
                    ns.IsClassQuest=function() return false end
                    ns.IsProfessionQuest=function() return false end
                    ns.QuestLogReview=function() return {} end
                    ns.UpdateSelectedRoute=function() end
                    local record={id=701,title="Hidden target"}
                    local guide={key="guide:test",title="Unrelated guide",zone="Other zone",kind="Zone guide",
                        records={record},target=record,hasPoint=true,reason="Available",minLevel=1,maxLevel=10}
                    ns.GuideBrowserChoices=function() return {guide} end
                    ns.BuildClassQuestsGuide=function()
                        guide.classLineGuide=true; guide.classQuestCount=1; guide.classQuestStepCount=1; guide.availableNow=1
                        return guide
                    end
                    ns.DungeonGroups=function()
                        return {{key="test",name="Unrelated dungeon",ids={701},definition={runLevelLow=10,runLevelHigh=15}}}
                    end
                    ns.DungeonCollectionReadiness=function() return {count=1,unknown=0,pickupLevel=10} end
                    ns.ProfessionChoices=function()
                        return {{title="Unrelated profession",category="CRAFTING",detail="Hidden target",profession=171}}
                    end
                    ns.LibraryPageItems=function()
                        return {{id=701,quest={title="Hidden target",level=10,minLevel=1,side="Horde"},zone="Other zone",search="hidden target"}},1,1
                    end
                    ns.CatalogueRecord=function(id) return {id=id,title="Hidden target"} end
                    ns.BuildGuideRoute=function() return {stops={{id=701}}} end
                    ns.libraryPage=1
                    ns.RequestStartRoute=function(route) followedQuest=route.key end
                    ns.StartProfessionGuide=function() followedProfession=true end
                ''', ns)
                ns.SetHubTab("Browse")
                ns.SetFilter(category, True)
                self.assertGreater(ns.ui.visibleCards, 0)
                if category == "guides":
                    self.assertEqual(ns.ui.cards[1].title.text, "Unrelated guide")
                elif category == "classquests":
                    self.assertEqual(ns.ui.cards[1].title.text, "Unrelated guide")
                    self.assertEqual(ns.ui.cards[1].detailsButton.caption.text, "Follow")
                elif category == "dungeons":
                    self.assertEqual(ns.ui.cards[1].title.text, "Unrelated dungeon")
                elif category == "professions":
                    self.assertEqual(ns.ui.cards[1].title.text, "Unrelated profession")
                    ns.ui.cards[1].detailsButton.OnClick()
                    self.assertTrue(lua.globals().followedProfession)
                else:
                    self.assertEqual(ns.ui.cards[1].title.text, "Hidden target")
                    ns.ui.cards[1].detailsButton.OnClick()
                    self.assertEqual(lua.globals().followedQuest, "quest:701")


if __name__ == "__main__":
    unittest.main()
