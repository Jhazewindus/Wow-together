"""Instances: dungeons and raids, and the keys and attunements they need."""
import unittest

from test_addon import Client
import test_leveling_path as T


def character(faction='Horde', level=58, completed=(), quests=(), items=()):
    c = Client(quests=quests, completed=completed, use_catalogue=True, party_mode='never',
               saved_variables={'config': {'uiNext': True, 'levelingPath': False}})
    c.guide_environment(level=level)
    c.lua.execute(T.SCENE, c.ns, level, 0.4, faction, 1428, 'Burning Steppes')
    c.ns.ReadProfile(); c.drain()
    c.lua.execute('local held = ...; function GetItemCount(id) return held[id] and 1 or 0 end; C_Item = C_Item or {}; C_Item.GetItemCount = GetItemCount',
                  c.lua.table_from({item: True for item in items}))
    return c


def first(c, key):
    return list(c.ns.InstanceAccess(key).values())[0]


class ProgressTests(unittest.TestCase):
    def test_a_chain_reports_the_step_and_what_comes_next(self):
        c = character(completed=(4903, 4941, 4974), quests=(6566,))
        status = first(c, 'onyxias-lair')
        self.assertEqual((status.state, status.done, status.total), ('progress', 3, 14))
        self.assertEqual(status.nextTitle, 'What the Wind Carries')
        self.assertTrue(status.inLog)
        self.assertEqual(status.text, 'Attunement: Drakefire Amulet • step 4 of 14 • next: What the Wind Carries')

    def test_each_faction_has_its_own_chain(self):
        horde = first(character('Horde'), 'onyxias-lair')
        alliance = first(character('Alliance'), 'onyxias-lair')
        self.assertEqual((horde.total, horde.nextTitle), (14, "Warlord's Command"))
        self.assertEqual((alliance.total, alliance.nextTitle), (16, 'Dragonkin Menace'))
        self.assertEqual(horde.text, "Attunement: Drakefire Amulet • not started, 14 steps • next: Warlord's Command")

    def test_every_step_of_every_chain_is_a_quest_the_catalogue_knows_for_that_faction(self):
        c = character()
        missing = c.lua.eval('''function(ns)
            local problems = {}
            for key, entries in pairs(ns.instanceAccess) do
                for _, entry in ipairs(entries) do
                    for side, chain in pairs(entry.chains or {}) do
                        for _, id in ipairs(chain) do
                            local quest = ns.CatalogueQuest(id)
                            if not quest then problems[#problems + 1] = key .. " " .. id .. " unknown"
                            else
                                local owner = quest.faction or quest.requiredFaction or quest.side
                                if owner ~= "Both" and owner ~= side then problems[#problems + 1] = key .. " " .. id .. " is " .. tostring(owner) .. ", listed for " .. side end
                            end
                        end
                    end
                end
            end
            return table.concat(problems, "; ")
        end''')(c.ns)
        self.assertEqual(missing, '')

    def test_carrying_the_key_counts_whatever_the_quest_log_says(self):
        c = character(items=(13704,))
        status = first(c, 'scholomance')
        self.assertEqual(status.state, 'have')
        self.assertEqual(status.text, 'Key: Skeleton Key • you have it')

    def test_a_finished_chain_is_done(self):
        c = character(completed=(3801, 3802))
        self.assertEqual(first(c, 'blackrock-depths').text, 'Key: Shadowforge Key • done')

    def test_a_key_that_drops_has_no_steps(self):
        c = character()
        status = first(c, 'stratholme')
        self.assertEqual(status.state, 'drop')
        self.assertIn('Drops from Magistrate Barthilas', status.text)
        self.assertEqual(first(character(items=(12382,)), 'stratholme').state, 'have')

    def test_the_new_raids_need_nothing_and_an_unsure_requirement_says_so(self):
        c = character()
        self.assertEqual(first(c, 'hyjal-summit').state, 'open')
        self.assertIn('Guides disagree', c.ns.InstanceAccessHelp('blackrock-spire'))


class SameRunTests(unittest.TestCase):
    """A dungeon says which steps of another instance's chain are done inside it."""

    def test_blackrock_spire_lists_the_onyxia_steps_still_ahead(self):
        c = character(completed=(4903,))
        also = list(c.ns.InstanceAlsoHere('blackrock-spire').values())
        amulet = next(entry for entry in also if entry.title == 'Drakefire Amulet')
        self.assertEqual(amulet.owner, 'onyxias-lair')
        self.assertGreaterEqual(len(list(amulet.steps.values())), 1)
        self.assertNotIn(4903, list(amulet.steps.values()))                         # Already done.
        lines = list(c.ns.InstanceAccessLines('blackrock-spire').values())
        self.assertTrue(lines[0].startswith('Key: Seal of Ascension'))
        self.assertTrue(any(line.startswith('Also: ') and 'Drakefire Amulet here' in line for line in lines))

    def test_nothing_is_listed_once_the_amulet_is_carried(self):
        c = character(items=(16309,))
        self.assertFalse(any(entry.title == 'Drakefire Amulet' for entry in c.ns.InstanceAlsoHere('blackrock-spire').values()))


class ViewTests(unittest.TestCase):
    def cards(self, c):
        return [(card.category.text, card.title.text, card.reason.text) for card in c.ns.ui.cards.values() if card.IsShown(card)]

    def open(self, c):
        ns = c.ns
        if not ns.window.IsShown(ns.window):
            ns.ToggleWindow()
        ns.SetHubTab('Browse'); ns.ui.browseFilter = 'dungeons'; ns.SetFilter('dungeons', True); c.drain(); ns.Refresh(); c.drain()

    def test_the_tab_is_called_instances_and_has_a_dungeons_and_raids_switch(self):
        c = character(completed=(4903, 4941, 4974)); ns = c.ns
        self.open(c)
        self.assertEqual(ns.ui.browseButtons.dungeons.caption.text, 'Instances')
        self.assertTrue(ns.ui.instanceSwitch.dungeons.IsShown(ns.ui.instanceSwitch.dungeons))
        self.assertTrue(ns.ui.instanceSwitch.dungeons.primary)
        self.assertTrue(all(category == 'DUNGEON' for category, _, _ in self.cards(c)))
        ns.ui.instanceSwitch.raids.OnClick(ns.ui.instanceSwitch.raids); c.drain()
        self.assertTrue(ns.ui.instanceSwitch.raids.primary)
        self.assertFalse(ns.ui.instanceSwitch.dungeons.primary)
        shown = self.cards(c)
        self.assertEqual([title for _, title, _ in shown], ["Onyxia's Lair", 'The Barrow Deeps', 'Hyjal Summit'])
        self.assertIn('Attunement: Drakefire Amulet • step 4 of 14', shown[0][2])
        self.assertIn('No attunement', shown[1][2])

    def test_the_switch_is_only_on_the_instances_view(self):
        c = character(); ns = c.ns
        self.open(c)
        ns.ui.browseFilter = 'professions'; ns.SetFilter('professions', True); c.drain()
        self.assertFalse(ns.ui.instanceSwitch.raids.IsShown(ns.ui.instanceSwitch.raids))

    def test_a_dungeon_card_carries_its_key_line(self):
        c = character(completed=(838, 964)); ns = c.ns
        self.open(c)
        scholomance = next(reason for _, title, reason in self.cards(c) if title == 'Scholomance')
        self.assertIn('Key: Skeleton Key • step 3 of 6', scholomance)

    def test_a_raid_with_steps_left_offers_the_next_one_and_a_raid_without_offers_nothing(self):
        c = character(); ns = c.ns
        self.open(c)
        c.lua.execute('local ns = ...; shownQuest = nil; ns.ShowQuestDetails = function(id) shownQuest = id end', ns)
        ns.SetInstanceKind('raids'); c.drain()
        cards = [card for card in ns.ui.cards.values() if card.IsShown(card)]
        onyxia = next(card for card in cards if card.title.text == "Onyxia's Lair")
        self.assertEqual(onyxia.detailsButton.caption.text, 'Next step')
        onyxia.detailsButton.OnClick(onyxia.detailsButton)
        self.assertEqual(c.lua.globals().shownQuest, 4903)                          # Warlord's Command.
        hyjal = next(card for card in cards if card.title.text == 'Hyjal Summit')
        self.assertFalse(hyjal.detailsButton.IsShown(hyjal.detailsButton))


if __name__ == '__main__':
    unittest.main()


class InstancePageTests(unittest.TestCase):
    """An instance opens onto its access, its chain steps and the quests for a run: no map, bosses or loot."""

    def page(self, key, **kwargs):
        c = character(**kwargs); ns = c.ns
        instance = next((g for g in ns.DungeonGroups().values() if g.key == key), None) \
            or next(r for r in ns.instanceRaids.values() if r.key == key)
        ns.ShowInstancePage(instance)
        return c, ns.instancePage

    def rows(self, frame):
        return [row for row in frame.rows.values() if row.IsShown(row)]

    def titles(self, frame):
        return [row.title.text for row in self.rows(frame)]

    def test_a_raid_page_lists_every_step_of_its_attunement_with_the_current_one_marked(self):
        c, frame = self.page('onyxias-lair', completed=(4903, 4941, 4974), quests=(6566,))
        self.assertEqual(frame.title.text, "Onyxia's Lair")
        self.assertIn('Still needed: Drakefire Amulet', frame.summary.text)
        titles = self.titles(frame)
        self.assertEqual(titles[0], 'GETTING IN')
        self.assertEqual(titles[1], 'Drakefire Amulet')
        self.assertEqual(titles[2:6], ["1. Warlord's Command", "2. Eitrigg's Wisdom", '3. For The Horde!', '4. What the Wind Carries'])
        self.assertEqual(len(titles), 2 + 14)
        rows = self.rows(frame)
        self.assertEqual(rows[1].right.text, '3 of 14 steps')
        self.assertEqual(rows[2].right.text, 'Done')
        self.assertTrue(rows[5].go.IsShown(rows[5].go))                             # Only the current step has a button.
        self.assertFalse(rows[6].go.IsShown(rows[6].go))
        self.assertFalse(frame.collect.IsShown(frame.collect))                      # No dungeon quest route for a raid.

    def test_the_current_step_opens_its_quest(self):
        c, frame = self.page('onyxias-lair', completed=(4903,))
        c.lua.execute('local ns = ...; opened = nil; ns.ShowQuestDetails = function(id) opened = id end', c.ns)
        current = self.rows(frame)[3]
        current.go.OnClick(current.go)
        self.assertEqual(c.lua.globals().opened, 4941)

    def test_a_dungeon_page_has_its_key_the_steps_of_other_chains_and_its_quests(self):
        c, frame = self.page('blackrock-spire', completed=(4903, 4742))
        titles = self.titles(frame)
        self.assertEqual(titles[0:2], ['GETTING IN', 'Seal of Ascension'])
        self.assertIn('ALSO DONE IN HERE', titles)
        self.assertIn('QUESTS FOR A RUN', titles)
        self.assertLess(titles.index('ALSO DONE IN HERE'), titles.index('QUESTS FOR A RUN'))
        self.assertTrue(frame.collect.IsShown(frame.collect))
        self.assertIn('Guides disagree', self.rows(frame)[1].second.text)

    def test_a_quest_shown_as_a_step_is_not_listed_again_among_the_quests(self):
        c, frame = self.page('blackrock-spire')
        titles = self.titles(frame)
        after = titles[titles.index('QUESTS FOR A RUN') + 1:]
        self.assertNotIn('Seal of Ascension', after)
        self.assertEqual(titles.count('1. Seal of Ascension'), 1)

    def test_a_quest_at_the_end_of_a_chain_says_what_comes_first(self):
        c = character(); ns = c.ns
        lead = list(ns.QuestLeadIn(6602).values())                                  # Blood of the Black Dragon Champion.
        self.assertEqual(lead[0], 4903)                                             # It starts with Warlord's Command...
        self.assertEqual(lead[-1], 6601)                                            # ...and Ascension... comes just before.
        done = character(completed=(4903, 4941, 4974, 6566, 6567, 6568, 6569, 6570, 6582, 6583, 6584, 6585))
        self.assertEqual(list(done.ns.QuestLeadIn(6602).values()), [6601])          # Finished steps are not counted.

    def test_a_card_opens_this_page_and_not_the_map_and_loot_viewer(self):
        c = character(); ns = c.ns
        c.lua.execute('local ns = ...; page = 0; '
                      'local show = ns.ShowInstancePage; ns.ShowInstancePage = function(...) page = page + 1; return show(...) end', ns)
        if not ns.window.IsShown(ns.window):
            ns.ToggleWindow()
        ns.SetHubTab('Browse'); ns.ui.browseFilter = 'dungeons'; ns.SetFilter('dungeons', True); c.drain(); ns.Refresh(); c.drain()
        card = next(card for card in ns.ui.cards.values() if card.IsShown(card) and card.title.text == 'Scholomance')
        card.OnClick(card)
        self.assertEqual(c.lua.globals().page, 1)
        self.assertEqual(ns.instancePage.title.text, 'Scholomance')
        self.assertNotIn('loot', card.reason.text.lower())
