"""Hub navigation and click-budget controls under the host UI mock."""
import unittest

from test_addon import Client


class HubTests(unittest.TestCase):
    def hub_client(self, **kwargs):
        kwargs.setdefault("saved_variables", {"config": {"uiNext": True}})
        return Client(**kwargs)

    def test_new_hub_is_opt_in_and_removes_the_title_menu_icon(self):
        legacy = Client(quests=(), default_guide=True)
        self.assertFalse(legacy.ns.Option("uiNext"))
        self.assertFalse(legacy.ns.ui.hubRail.IsShown(legacy.ns.ui.hubRail))
        self.assertTrue(legacy.ns.ui.viewChoice.IsShown(legacy.ns.ui.viewChoice))
        self.assertIsNone(legacy.ns.ui.titleIcon)
        self.assertEqual(legacy.ns.ui.settingsButton.caption.text, "⚙")

    def test_hub_rail_uses_full_height_selected_rows_and_settings_tab(self):
        client = self.hub_client(quests=(), default_guide=True)
        ns = client.ns
        self.assertTrue(ns.ui.hubRail.IsShown(ns.ui.hubRail))
        self.assertEqual(ns.ui.hubButtons.Play.height, 40)
        self.assertEqual(ns.ui.hubButtons.Play.selectedBar.IsShown(ns.ui.hubButtons.Play.selectedBar), True)
        self.assertIsNotNone(ns.ui.hubButtons.Settings)
        self.assertTrue(ns.ui.hubButtons.Settings.IsShown(ns.ui.hubButtons.Settings))

    def test_left_rail_switches_play_group_browse_and_settings(self):
        client = self.hub_client(quests=(), default_guide=True)
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

        ui.settingsButton.OnClick()
        self.assertTrue(ns.settings.IsShown(ns.settings))

    def test_group_tab_uses_synced_party_facts_and_shows_mockup_panels(self):
        client = self.hub_client(quests=(), default_guide=True)
        ns = client.ns
        client.lua.execute('''
            local ns=...
            ns.profile={level=26,zone="Crossroads",mapID=501}
            ns.partyNames={"Bob"}
            ns.members={Bob={active=true,syncPending=false,profile={level=24,zone="Ashenvale",mapID=502}}}
            ns.PartyFeaturesEnabled=function() return true end
            ns.PartyPlanMissingLine=function() return "Missing vs party: Bob lacks Test quest" end
            ns.partyRouteStatus="Route updated after Bob skipped the giver"
        ''', ns)
        ns.SetHubTab("Group")
        page = ns.ui.groupPage
        self.assertIn("1 synced", page.summary.text)
        self.assertEqual(page.memberRows[1].name.text, "You (you)")
        self.assertEqual(page.memberRows[2].name.text, "Bob")
        self.assertEqual(page.memberRows[2].level.text, "24")
        self.assertEqual(page.memberRows[2].zone.text, "Ashenvale")
        self.assertIn("lacks Test quest", page.missing.text)
        self.assertIn("Route updated", page.lastChange.text)
        self.assertEqual(page.missingTitle.text, "MISSING VS PLAN")
        self.assertEqual(page.readyTitle.text, "READY TO TURN IN")

    def test_play_has_active_guide_controls_and_follow_card_action(self):
        client = self.hub_client(quests=(), default_guide=True)
        ns = client.ns
        client.lua.execute('''
            local ns = ...
            ns.profile.level = 22
            ns.routeSelection = {key="test", title="Test guide", enabledCount=8, rangeHigh=25}
            ns.selectedRoute = {stops={{id=1, guideStep=2}}}
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
        self.assertTrue(home.resume.glanceControl.IsShown(home.resume.glanceControl))
        self.assertEqual(home.resume.detail.text, "step 2 of 8 · 3 levels left · exit at 25")
        self.assertAlmostEqual(home.resume.fraction, 0.125)
        self.assertEqual(home.nextCount, 1)
        self.assertEqual(home.nextRows[1].action.caption.text, "Follow")
        home.nextRows[1].action.OnClick()
        self.assertTrue(client.lua.globals().followed)

    def test_browse_filter_labels_fit_and_cards_use_mockup_grid(self):
        client = self.hub_client(quests=(), default_guide=True)
        ns = client.ns
        ui = ns.ui
        ns.SetHubTab("Browse")
        widths = [ui.browseButtons[key].width for key in ("guides", "classquests", "dungeons", "professions", "library")]
        self.assertGreaterEqual(widths[3], 96)
        if ui.visibleCards >= 2:
            first, second = ui.cards[1], ui.cards[2]
            self.assertLess(first.width, ns.ui.contentWidth)
            self.assertNotEqual(first.point, second.point)

    def test_next_for_you_is_capped_at_five_cards(self):
        client = self.hub_client(quests=(), default_guide=True)
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
        self.assertEqual(home.nextCount, 5)
        for index in range(1, 6):
            self.assertTrue(home.nextRows[index].IsShown(home.nextRows[index]))
            self.assertIn(home.nextRows[index].action.caption.text, ("Follow", "Open"))
            self.assertIsNone(home.nextRows[index].follow)

    def test_footer_includes_sync_data_age_and_version(self):
        client = self.hub_client(quests=(), default_guide=True)
        status = client.ns.ui.status.text
        self.assertIn("sync:", status)
        self.assertIn("quest data:", status)
        self.assertIn(str(client.ns.VERSION), status)
        self.assertTrue(client.ns.ui.reportProblem.IsShown(client.ns.ui.reportProblem))
        client.ns.VERSION = "0.8.112-beta.23.4b0eeca12345678"
        client.ns.UpdateHubFooter()
        self.assertIn("0.8.112-beta.23+4b0eeca", client.ns.ui.status.text)
        self.assertNotIn("4b0eeca12345678", client.ns.ui.status.text)

    def test_scroll_child_width_tracks_viewport_at_supported_and_wide_sizes(self):
        client = self.hub_client(quests=(), default_guide=True)
        ns = client.ns
        for width in (860, 1100, 1400):
            with self.subTest(width=width):
                ns.window.SetSize(ns.window, width, 620)
                ns.ui.scroll.SetWidth(ns.ui.scroll, width - 168)
                ns.Layout()
                self.assertLessEqual(ns.ui.content.width, ns.ui.scroll.width)
                self.assertEqual(ns.ui.content.width, ns.ui.scroll.width - 22)
                ns.RenderRecommended(ns.NewQuestQuery())
                for index in range(1, ns.ui.home.nextCount + 1):
                    self.assertLessEqual(ns.ui.home.nextRows[index].width, ns.ui.scroll.width)

    def test_browse_card_exposes_only_the_follow_action(self):
        client = self.hub_client(quests=(), default_guide=True)
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
                client.ns.SetOption("uiNext", True)
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
