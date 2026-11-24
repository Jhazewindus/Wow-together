"""The skilling path: an independent reference of its cost model and its optimisation.

The planner decides which recipe to craft at every skill point. These tests
re-implement its cost model in Python from the bundled recipe data alone,
check the addon's numbers against it, and check that the path the addon
returns is the cheapest one under that model.
"""
import math
import random
import re
import unittest

from test_addon import Client

PROFESSIONS = (171, 164, 333, 202, 165, 197, 129, 185)  # The six crafting professions, First Aid and Cooking.
UNKNOWN_UNIT, SECONDS, DEPTH = 1000, 4, 2
TIME_VALUE = {'gold': 0, 'balanced': 100, 'speed': 1000}
VISIT = {'trainer': 20, 'vendor': 120}


def convert(value):
    if hasattr(value, 'items') and not isinstance(value, dict):
        keys = list(value.keys())
        if keys and all(isinstance(key, int) for key in keys) and sorted(keys) == list(range(1, len(keys) + 1)):
            return [convert(value[key]) for key in range(1, len(keys) + 1)]
        return {str(key): convert(value[key]) for key in keys}
    return value


_SHARED = {}


def make(prices=None, sell=None, options=None, mining=None):
    """One host client for the whole module (each one holds the full addon and its data).

    The market and the options are swapped in place between tests.
    """
    if 'client' not in _SHARED:
        client = Client(quests=(), default_guide=True, use_lazy_data=True)
        client.lua.execute('''
            local ns = ...
            ns.profile = ns.profile or {}; ns.profile.faction = "Horde"
            ns.marketQuotes, ns.professionVendorQuotes = {}, {}
            testPrices, testSell, testOptions = {}, {}, {}
            realSellValue = ns.ProfessionSellValue
            ns.AuctionUnitPrice = function(id) return testPrices[id] end
            ns.ProfessionSellValue = function(id) return testSell[id] end
            ns.ItemOwned = function() return 0 end
            local option = ns.Option
            ns.Option = function(key) if testOptions[key] ~= nil then return testOptions[key] end return option(key) end
            function setMarket(prices, sell, options) testPrices, testSell, testOptions = prices, sell, options end
        ''', client.ns)
        _SHARED['client'] = client
    client = _SHARED['client']
    client.lua.globals().setMarket(client.lua.table_from(prices or {}), client.lua.table_from(sell or {}),
                                   client.lua.table_from(options or {}))
    # A second profession: with Mining the character can smelt bars from ore.
    client.lua.execute('local ns, skill = ...; ns.gatheringData[186] = skill and {id = 186, skill = skill, maximum = 300} or nil',
                       client.ns, mining)
    return client


def recipes(client, profession):
    cache = _SHARED.setdefault('recipes', {})
    if profession not in cache:
        client.ns.ProfessionPathPlan(profession, 1, 2, False)  # Loads the reference with its hotfixes applied.
        cache[profession] = convert(client.ns.ProfessionFacts(profession)['recipes'])
    return cache[profession]


SMELTING = (  # spell, Mining skill, bar, bars made, reagents
    (2657, 1, 2840, 1, ((2770, 1),)), (3304, 65, 3576, 1, ((2771, 1),)), (2659, 65, 2841, 2, ((2840, 1), (3576, 1))),
    (2658, 75, 2842, 1, ((2775, 1),)), (3307, 125, 3575, 1, ((2772, 1),)), (3308, 155, 3577, 1, ((2776, 1),)),
    (3569, 165, 3859, 1, ((3575, 1), (3857, 1))), (10097, 175, 3860, 1, ((3858, 1),)),
    (10098, 230, 6037, 1, ((7911, 1),)), (16153, 250, 12359, 1, ((10620, 1),)),
)
ORES = (2770, 2771, 2775, 2772, 2776, 3857, 3858, 7911, 10620)


class Reference:
    """The cost model, written again from its description."""

    def __init__(self, data, prices, sell, mode='balanced', recoup=True, perk=False, faction='Horde', learned=(), mining=None):
        self.data, self.prices, self.sell = data, prices, sell
        self.time, self.recoup, self.perk, self.faction = TIME_VALUE[mode], recoup, perk, faction
        self.learned = set(learned)
        self.only = None  # Restrict the recipes considered (exhaustive checks need a small set).
        self.mining = mining
        self.producers = {}
        for recipe in data:
            if recipe.get('outputID'):
                self.producers.setdefault(recipe['outputID'], []).append(recipe)
        for spell, skill, bar, made, reagents in SMELTING:
            self.producers.setdefault(bar, []).append({
                'id': spell, 'name': 'smelt', 'external': skill, 'source': 'smelting', 'learn': 0, 'yellow': 0, 'grey': 0,
                'outputID': bar, 'outputQuantity': made, 'materials': [list(pair) for pair in reagents]})

    def allowed(self, recipe, skill, widen):
        if recipe.get('external') is not None:
            return self.mining is not None and self.mining >= recipe['external']
        known = recipe['id'] in self.learned
        if recipe.get('faction') and recipe['faction'] != self.faction and not known:
            return False
        if not isinstance(recipe.get('learn'), int) or recipe['learn'] > skill:
            return False
        if not known and recipe['source'] not in ('start', 'trainer') and not (widen and recipe['source'] == 'vendor'):
            return False
        return len(recipe['materials']) > 0

    def chance(self, recipe, skill, widen):
        if not self.allowed(recipe, skill, widen):
            return 0
        grey, yellow = recipe.get('grey'), recipe.get('yellow')
        if not isinstance(grey, int) or grey <= skill:
            return 0
        if yellow and skill < yellow:
            value = 1
        elif yellow and grey > yellow:
            value = max(0.05, min(1, (grey - skill) / (grey - yellow)))
        else:
            value = 0.5
        if self.perk and 0 < value < 1:
            value = min(1, value * 1.10)
        return value

    def candidates(self, skill, widen):
        out = []
        for recipe in self.data:
            if self.only is not None and recipe['id'] not in self.only:
                continue
            if re.match(r'^Runed .* Rod$', recipe['name']) and skill != recipe.get('learn'):
                continue
            if self.chance(recipe, skill, widen) > 0:
                out.append(recipe)
        return sorted(out, key=lambda recipe: recipe['id'])

    def unit(self, item, skill, widen, depth, visiting):
        direct = self.prices.get(item)
        best, priced, seconds, gain = direct, direct is not None, 0, 0
        crafted_total = None
        if depth < DEPTH and item not in visiting:
            for recipe in self.producers.get(item, []):
                if not self.allowed(recipe, skill, False):
                    continue
                cost, complete, inner_seconds, inner_gain = self.recipe(recipe, skill, widen, depth + 1, visiting | {item})
                made = max(1, recipe.get('outputQuantity') or 1)
                made_seconds = (inner_seconds + SECONDS) / made
                made_gain = (inner_gain + self.chance(recipe, skill, widen)) / made
                total = cost / made + made_seconds * self.time
                if (direct is None or (complete and total < direct)) and (crafted_total is None or total < crafted_total):
                    crafted_total = total
                    best, priced, seconds, gain = cost / made, complete, made_seconds, made_gain
        if best is None:
            return UNKNOWN_UNIT, False, 0, 0
        return best, priced, seconds, gain

    def recipe(self, recipe, skill, widen, depth=0, visiting=frozenset()):
        total, complete, seconds, gain = 0, True, 0, 0
        for item, quantity in recipe['materials']:
            unit, priced, unit_seconds, unit_gain = self.unit(item, skill, widen, depth, visiting)
            total, complete = total + unit * quantity, complete and priced
            seconds, gain = seconds + unit_seconds * quantity, gain + unit_gain * quantity
        return total, complete, seconds, gain

    def point(self, recipe, skill, widen):
        own = self.chance(recipe, skill, widen)
        if own <= 0:
            return None
        cost, complete, prep_seconds, prep_gain = self.recipe(recipe, skill, widen)
        resale = 0
        if self.recoup and recipe.get('outputID') and self.sell.get(recipe['outputID']) is not None:
            resale = self.sell[recipe['outputID']] * max(1, recipe.get('outputQuantity') or 1)
        gold, seconds, gain = max(0, cost - resale), SECONDS + prep_seconds, own + prep_gain
        return {'score': (gold + seconds * self.time) / gain, 'gold': gold / gain, 'crafts': 1 / gain, 'priced': complete}

    def fee(self, recipe):
        if recipe['id'] in self.learned or recipe['source'] == 'start':
            return 0
        if recipe['source'] == 'trainer':
            return (recipe.get('trainingCost') or 0) + VISIT['trainer'] * self.time
        return VISIT['vendor'] * self.time

    def cheapest(self, start, target, widen):
        """Cheapest total with a recipe's fee paid at the start of each block of its crafts."""
        best, carried = {start: 0.0}, {}
        for skill in range(start, target):
            if skill not in best:
                break
            nxt, alive = None, {}
            for recipe in self.candidates(skill, widen):
                fact = self.point(recipe, skill, widen)
                base = best[skill] + self.fee(recipe)
                if recipe['id'] in carried:
                    base = min(base, carried[recipe['id']])
                alive[recipe['id']] = base + fact['score']
                nxt = alive[recipe['id']] if nxt is None else min(nxt, alive[recipe['id']])
            carried = alive
            if nxt is not None:
                best[skill + 1] = nxt
        return best

    def cheapest_paying_once(self, start, target, widen):
        """True optimum where a recipe's fee is paid once however its crafts are spread."""
        involved = sorted({recipe['id'] for skill in range(start, target) for recipe in self.candidates(skill, widen)})
        bit = {recipe_id: 1 << index for index, recipe_id in enumerate(involved)}
        states = {0: 0.0}
        for skill in range(start, target):
            following = {}
            for recipe in self.candidates(skill, widen):
                score = self.point(recipe, skill, widen)['score']
                for paid, cost in states.items():
                    extra = 0 if paid & bit[recipe['id']] else self.fee(recipe)
                    key = paid | bit[recipe['id']]
                    value = cost + extra + score
                    if key not in following or value < following[key]:
                        following[key] = value
            states = following
            if not states:
                return None
        return min(states.values())

    def evaluate(self, steps, widen):
        """What a returned path costs under this model."""
        total, by_id = 0.0, {recipe['id']: recipe for recipe in self.data}
        for step in steps:
            recipe = by_id[step['id']]
            total += self.fee(recipe)
            for skill in range(step['start'], step['finish']):
                total += self.point(recipe, skill, widen)['score']
        return total


def plan_steps(plan):
    return [{'id': step.recipe.id, 'name': step.recipe.name, 'start': step.start, 'finish': step.finish,
             'crafts': step.crafts, 'safe': step.safe, 'gold': step.gold, 'acquire': step.acquire, 'fee': step.fee}
            for step in plan.steps.values()]


def market(data, rng, known=0.9):
    """A random auction house: most reagents priced, some not listed."""
    prices, sell = {}, {}
    for recipe in data:
        for item, _ in recipe['materials']:
            if item not in prices and rng.random() < known:
                prices[item] = rng.choice((15, 40, 120, 350, 900, 2500, 6000)) + rng.randrange(50)
        if recipe.get('outputID') and rng.random() < 0.8:
            sell[recipe['outputID']] = rng.randrange(5, 1500)
    return prices, sell


class CostModelTests(unittest.TestCase):
    def test_points_match_the_independent_reference_on_every_profession(self):
        rng = random.Random(11)
        for profession in PROFESSIONS:
            data = recipes(make(), profession)
            prices, sell = market(data, rng)
            client = make(prices, sell)
            reference = Reference(data, prices, sell)
            find = client.lua.eval('function(ns, id, recipe) for _, r in ipairs(ns.ProfessionFacts(id).recipes) do if r.id == recipe then return r end end end')
            checked = 0
            for skill in range(1, 300, 13):
                for recipe in reference.candidates(skill, True)[:12]:
                    expected = reference.point(recipe, skill, True)
                    lua_recipe = find(client.ns, profession, recipe['id'])
                    actual = client.ns.ProfessionPathPoint(profession, lua_recipe, skill, True)
                    self.assertIsNotNone(actual, (profession, recipe['name'], skill))
                    self.assertAlmostEqual(actual.score, expected['score'], delta=1e-6 * max(1, expected['score']), msg=(recipe['name'], skill))
                    self.assertAlmostEqual(actual.crafts, expected['crafts'], places=9)
                    self.assertEqual(bool(actual.priced), expected['priced'])
                    checked += 1
            self.assertGreater(checked, 60, profession)


class OptimalityTests(unittest.TestCase):
    def test_returned_path_is_the_cheapest_under_the_reference_for_random_markets(self):
        rng = random.Random(23)
        for profession in PROFESSIONS:
            data = recipes(make(), profession)
            for mode in ('gold', 'balanced', 'speed'):
                prices, sell = market(data, rng, known=rng.choice((0.6, 0.95)))
                options = {'professionPathMode': mode, 'professionVendorRecipes': True}
                client = make(prices, sell, options)
                reference = Reference(data, prices, sell, mode=mode)
                start, target = rng.choice(((1, 300), (60, 225), (140, 300)))
                plan = client.ns.ProfessionPathPlan(profession, start, target, False)
                steps = plan_steps(plan)
                best = reference.cheapest(start, target, True)
                reached = max(best)
                self.assertEqual(target - plan.missing, reached, (profession, mode))
                self.assertEqual(steps[0]['start'], start)
                for before, after in zip(steps, steps[1:]):
                    self.assertEqual(before['finish'], after['start'])  # One unbroken path.
                self.assertEqual(steps[-1]['finish'], reached)
                cost = reference.evaluate(steps, True)
                self.assertAlmostEqual(cost, best[reached], delta=1e-6 * max(1, best[reached]), msg=(profession, mode, start, target))

    def test_paying_a_fee_per_block_is_as_good_as_paying_it_once_on_short_stretches(self):
        rng = random.Random(5)
        worst = 1.0
        for profession in PROFESSIONS:
            data = recipes(make(), profession)
            prices, sell = market(data, rng)
            reference = Reference(data, prices, sell)
            for start in (1, 40, 90, 130, 180, 215):
                target = start + 14
                # Exhaustive search is exponential in the recipes involved: keep the eight best.
                reference.only = None
                ranked = {}
                for skill in range(start, target):
                    for recipe in reference.candidates(skill, False):
                        score = reference.point(recipe, skill, False)['score']
                        ranked[recipe['id']] = min(score, ranked.get(recipe['id'], score))
                reference.only = set(sorted(ranked, key=ranked.get)[:8])
                block = reference.cheapest(start, target, False)
                if target not in block:
                    continue
                exact = reference.cheapest_paying_once(start, target, False)
                self.assertIsNotNone(exact)
                self.assertGreaterEqual(block[target] + 1e-6, exact)
                worst = max(worst, block[target] / max(exact, 1e-9))
        # The planner charges a recipe's fee again if it returns to it later;
        # in practice it never does, so the simplification costs nothing.
        self.assertLess(worst, 1.02)


class SmeltingTests(unittest.TestCase):
    """A character with Mining can make bars; one without has to buy them."""

    def market(self, data, bar=1000, ore=100):
        prices = {item: 300 for recipe in data for item, _ in recipe['materials']}
        for _, _, made, _, _ in SMELTING:
            prices[made] = bar
        for item in ORES:
            prices[item] = ore
        return prices

    def test_bars_are_priced_as_ore_only_when_mining_skill_allows_the_smelt(self):
        data = recipes(make(), 164)
        prices = self.market(data)
        options = {'professionPathMode': 'gold'}
        bought = make(prices, {}, options).ns.ProfessionPathPlan(164, 1, 225, False)
        smelted = make(prices, {}, options, mining=300).ns.ProfessionPathPlan(164, 1, 225, False)
        self.assertLess(smelted.gold, bought.gold * 0.6)          # Ore at a tenth of the bar price.
        partial = make(prices, {}, options, mining=100).ns.ProfessionPathPlan(164, 1, 225, False)
        self.assertLess(partial.gold, bought.gold)                # Copper, tin, bronze and silver only...
        self.assertGreater(partial.gold, smelted.gold)            # ...iron, steel and mithril still bought.

    def test_cost_model_and_optimum_match_the_reference_with_smelting(self):
        rng = random.Random(41)
        for profession in (164, 202):
            data = recipes(make(), profession)
            prices, sell = market(data, rng, known=1.0)
            for item in ORES:
                prices[item] = rng.randrange(20, 400)
            for mining in (120, 300):
                client = make(prices, sell, {'professionVendorRecipes': True}, mining=mining)
                reference = Reference(data, prices, sell, mining=mining)
                plan = client.ns.ProfessionPathPlan(profession, 1, 300, False)
                steps = plan_steps(plan)
                best = reference.cheapest(1, 300, True)
                self.assertEqual(300 - plan.missing, max(best))
                self.assertAlmostEqual(reference.evaluate(steps, True), best[max(best)], delta=1e-6 * best[max(best)], msg=(profession, mining))

    def test_path_and_shopping_list_both_show_the_smelting(self):
        data = recipes(make(), 164)
        client = make(self.market(data), {}, {'professionPathMode': 'gold'}, mining=300)
        plan = client.ns.ProfessionPathPlan(164, 1, 150, False)
        text = client.ns.ProfessionPathText(164, plan)
        self.assertIn('Make first:', text)
        self.assertIn('Smelt Copper', text)
        forecast = client.ns.ProfessionMaterialForecast(164, plan, False)
        bought = {row.itemID for row in forecast.materials.values() if (row.missing or 0) > 0}
        self.assertIn(2770, bought)                                # Copper Ore is on the list...
        self.assertNotIn(2840, bought)                             # ...Copper Bars are not.
        prepared = {prep.recipe.name for group in forecast.groups.values() for prep in group.preparations.values()}
        self.assertIn('Smelt Copper', prepared)

    def test_without_mining_nothing_is_smelted(self):
        data = recipes(make(), 164)
        client = make(self.market(data), {}, {'professionPathMode': 'gold'})
        plan = client.ns.ProfessionPathPlan(164, 1, 150, False)
        self.assertNotIn('Smelt', client.ns.ProfessionPathText(164, plan))
        forecast = client.ns.ProfessionMaterialForecast(164, plan, False)
        bought = {row.itemID for row in forecast.materials.values() if (row.missing or 0) > 0}
        self.assertTrue(bought & {2840, 2841, 3575, 2842})        # Bars are bought as bars...
        self.assertFalse(bought & set(ORES))                       # ...and no ore is.


class FirstAidTests(unittest.TestCase):
    """First Aid is planned like the crafting professions, with its own way of ranking up."""

    def test_recipe_table_is_complete_and_consistent(self):
        data = recipes(make(), 129)
        self.assertEqual(len(data), 31)                              # Every craftable recipe of build 70862.
        names = {recipe['name']: recipe for recipe in data}
        linen = names['Linen Bandage']
        self.assertEqual((linen['learn'], linen['yellow'], linen['green'], linen['grey'], linen['source']), (1, 30, 45, 60, 'start'))
        potion = names['Minor Healing Potion']                       # A First Aid recipe in Forever.
        self.assertEqual((potion['yellow'], potion['grey'], potion['trainingCost']), (55, 95, 105))
        self.assertEqual(sorted(potion['materials']), [[2447, 1], [2678, 1], [3371, 1]])
        self.assertEqual(names['Anti-Venom']['outputQuantity'], 3)
        for recipe in data:
            self.assertLessEqual(recipe['learn'], recipe['yellow'], recipe['name'])
            self.assertLessEqual(recipe['yellow'], recipe['green'], recipe['name'])
            self.assertLessEqual(recipe['green'], recipe['grey'], recipe['name'])
            self.assertTrue(recipe['materials'], recipe['name'])
        self.assertEqual(len({recipe['id'] for recipe in data}), len(data))

    def test_path_reaches_300_and_needs_vendor_manuals_only_between_210_and_240(self):
        client = make()
        plan = client.ns.ProfessionPathPlan(129, 1, 300, False)
        self.assertEqual(plan.missing, 0)
        self.assertTrue(plan.widened)                                # No trainer recipe gives skill from 210 to 240.
        vendor = [step for step in plan_steps(plan) if step['acquire'] == 'vendor']
        self.assertTrue(vendor)
        self.assertTrue(all(step['start'] >= 175 for step in vendor))
        text = client.ns.ProfessionPathText(129, plan)
        self.assertIn('Manual sold by Deneb Walker', text)           # Where the manual comes from, from the reference.
        trainer_only = Reference(recipes(client, 129), {}, {}).cheapest(1, 300, False)
        self.assertEqual(max(trainer_only), 210)                     # Silk Bandage turns grey at 210.

    def test_rank_ups_go_to_the_book_vendor_and_the_triage_doctor_not_to_ordinary_trainers(self):
        client = make(); ns = client.ns
        client.lua.execute('local ns = ...; ns.profile.faction = "Horde"; ns.profile.mapID = 1454', ns)
        self.assertIn('Expert First Aid book', ns.ProfessionTrainer(129, 225).name)
        self.assertIn('Triage', ns.ProfessionTrainer(129, 300).name)
        ordinary = ns.ProfessionTrainer(129, 150)
        self.assertNotIn('book', ordinary.name); self.assertNotIn('Triage', ordinary.name)
        learn = lambda spell, cap: ns.ProfessionTrainer(129, cap, spell)
        self.assertNotIn('(', learn(3276, 75).name)                  # Heavy Linen Bandage: a normal trainer.
        self.assertIn('Triage', learn(18629, 300).name)              # Runecloth Bandage: only the doctor teaches it.

    def test_secondary_professions_are_read_from_any_slot_after_the_two_primaries(self):
        client = make(); ns = client.ns
        client.lua.execute('''
            savedGetProfessions, savedGetProfessionInfo = GetProfessions, GetProfessionInfo
            function GetProfessions() return nil, nil, nil, nil, 5, 6 end
            function GetProfessionInfo(slot)
                if slot == 6 then return "First Aid", "icon", 140, 150, 0, 0, 129 end
                return "Cooking", "icon", 60, 75, 0, 0, 185
            end
        ''')
        try:
            self.assertTrue(ns.ReadProfessionSkills())
            self.assertEqual((ns.professionData[129].skill, ns.professionData[129].maximum), (140, 150))
            titles = [choice.title for choice in ns.ProfessionChoices().values()]
            self.assertIn('First Aid', titles)
        finally:
            client.lua.execute('GetProfessions, GetProfessionInfo = savedGetProfessions, savedGetProfessionInfo')
            client.lua.execute('local ns = ...; ns.professionData[129] = nil', ns)

    def test_a_wrong_spell_id_in_the_reference_is_still_matched_by_name(self):
        client = make(); ns = client.ns
        client.lua.execute('''
            local ns = ...
            ns.professionData[129] = {skill = 45, maximum = 75, recipes = {}, known = {
                [999001] = {id = 999001, name = "Heavy Linen Bandage", learned = true, canSkillUp = true}}}
            ns.professionRevision = (ns.professionRevision or 0) + 1
        ''', ns)
        try:
            bandage = next(step for step in plan_steps(ns.ProfessionPathPlan(129, 45, 50, False)) if step['name'] == 'Heavy Linen Bandage')
            self.assertIsNone(bandage['acquire'])                    # Known to the client under another ID: not "learn it".
        finally:
            client.lua.execute('local ns = ...; ns.professionData[129] = nil; ns.professionRevision = ns.professionRevision + 1', ns)

    def test_a_recipe_without_a_known_spell_id_is_matched_to_the_client_by_name(self):
        client = make(); ns = client.ns
        client.lua.execute('''
            local ns = ...
            ns.professionData[129] = {skill = 95, maximum = 150, recipes = {}, known = {
                [1259342] = {id = 1259342, name = "Simple Poultice", learned = true, canSkillUp = true}}}
            ns.professionRevision = (ns.professionRevision or 0) + 1
        ''', ns)
        try:
            plan = ns.ProfessionPathPlan(129, 95, 110, False)
            poultice = [step for step in plan_steps(plan) if step['name'] == 'Simple Poultice']
            for step in poultice:
                self.assertIsNone(step['acquire'])                   # Already learned: nothing to buy or train.
            names = [step['name'] for step in plan_steps(plan)]
            self.assertEqual(len(names), len(set(zip(names, [s['start'] for s in plan_steps(plan)]))))
        finally:
            client.lua.execute('local ns = ...; ns.professionData[129] = nil; ns.professionRevision = ns.professionRevision + 1', ns)


class CookingTests(unittest.TestCase):
    """Cooking: complete to skill 125, the source's route dishes above it."""

    def test_dish_table_is_consistent_and_flags_what_is_estimated(self):
        data = recipes(make(), 185)
        self.assertEqual(len(data), 60)                                      # 55 to skill 125, five above.
        self.assertEqual(len({dish['id'] for dish in data}), len(data))
        self.assertEqual(len({dish['name'] for dish in data}), len(data))   # Names are how most are matched to the client.
        for dish in data:
            self.assertLessEqual(dish['learn'], dish['yellow'], dish['name'])
            self.assertLessEqual(dish['yellow'], dish['green'], dish['name'])
            self.assertLessEqual(dish['green'], dish['grey'], dish['name'])
            self.assertTrue(dish['materials'], dish['name'])
            self.assertTrue(dish['outputID'], dish['name'])
        estimated = sorted(dish['name'] for dish in data if dish.get('estimated'))
        self.assertEqual(estimated, ['Barbecued Buzzard Wing', 'Filet of Redgill', 'Mithril Headed Trout',
                                     'Poached Sunscale Salmon', 'Spider Sausage'])
        self.assertTrue(all(dish['learn'] > 125 for dish in data if dish.get('estimated')))
        self.assertTrue(all(not dish.get('estimated') for dish in data if dish['learn'] <= 125))
        names = {dish['name']: dish for dish in data}
        clams = names['Goblin Deviled Clams']
        self.assertEqual((clams['learn'], clams['yellow'], clams['green'], clams['grey'], clams['trainingCost']), (125, 165, 185, 205, 300))
        self.assertEqual(names['Seasoned Wolf Kabob']['outputQuantity'], 3)
        self.assertEqual(names['Tasty Raptor Bites']['materials'], [[3685, 1], [2678, 4]])

    def test_estimated_thresholds_agree_with_the_sources_craft_counts(self):
        # The source's trainer route gives 49 crafts of Barbecued Buzzard Wing
        # from 198 to 237 and 22 of Poached Sunscale Salmon from 280 to 300.
        reference = Reference(recipes(make(), 185), {}, {})
        names = {dish['name']: dish for dish in reference.data}
        crafts = lambda name, start, finish: sum(1 / reference.chance(names[name], skill, True) for skill in range(start, finish))
        self.assertAlmostEqual(crafts('Barbecued Buzzard Wing', 198, 237), 49, delta=2)
        self.assertAlmostEqual(crafts('Poached Sunscale Salmon', 280, 300), 22, delta=2)

    def test_path_reaches_300_and_never_suggests_a_winter_veil_dish(self):
        client = make()
        plan = client.ns.ProfessionPathPlan(185, 1, 300, False)
        self.assertEqual(plan.missing, 0)
        steps = plan_steps(plan)
        self.assertNotIn('Gingerbread Cookie', [step['name'] for step in steps])
        self.assertNotIn('Egg Nog', [step['name'] for step in steps])
        self.assertEqual(max(Reference(recipes(client, 185), {}, {}).cheapest(1, 300, False)), 280)  # Trainer dishes end with Spider Sausage.
        self.assertEqual(steps[-1]['name'], 'Poached Sunscale Salmon')
        text = client.ns.ProfessionPathText(185, plan)
        self.assertIn('Recipe sold by Gikkix', text)
        self.assertIn('Above skill 125 only a few recipes are known to the guide', text)
        early = client.ns.ProfessionPathText(185, client.ns.ProfessionPathPlan(185, 1, 100, False))
        self.assertNotIn('only a few recipes are known', early)            # Below 125 the list is complete.

    def test_cheap_fish_wins_when_vendor_recipes_are_allowed(self):
        data = recipes(make(), 185)
        prices = {item: 500 for dish in data for item, _ in dish['materials']}
        for fish in (6291, 6289, 6308, 8365, 13758, 13760):
            prices[fish] = 5
        allowed = make(prices, {}, {'professionPathMode': 'gold', 'professionVendorRecipes': True})
        names = [step['name'] for step in plan_steps(allowed.ns.ProfessionPathPlan(185, 1, 300, False))]
        for dish in ('Brilliant Smallfish', 'Longjaw Mud Snapper', 'Bristle Whisker Catfish', 'Mithril Headed Trout'):
            self.assertIn(dish, names)
        trainer_only = make(prices, {}, {'professionPathMode': 'gold'})
        names = [step['name'] for step in plan_steps(trainer_only.ns.ProfessionPathPlan(185, 1, 250, False))]
        self.assertNotIn('Longjaw Mud Snapper', names)                      # Not without the player's say-so.

    def test_rank_ups_go_to_the_cookbook_vendor_and_dirge(self):
        client = make(); ns = client.ns
        client.lua.execute('local ns = ...; ns.profile.faction = "Horde"; ns.profile.mapID = 1454', ns)
        self.assertIn('Wulan', ns.ProfessionTrainer(185, 225).name)
        self.assertIn('Dirge Quikcleave', ns.ProfessionTrainer(185, 300).name)
        self.assertNotIn('(', ns.ProfessionTrainer(185, 150).name)
        client.lua.execute('local ns = ...; ns.profile.faction = "Alliance"', ns)
        try:
            self.assertIn('Shandrina', ns.ProfessionTrainer(185, 225).name)
        finally:
            client.lua.execute('local ns = ...; ns.profile.faction = "Horde"', ns)


class BehaviourTests(unittest.TestCase):
    def test_every_profession_has_a_complete_path_to_300_without_any_prices(self):
        client = make()
        for profession in PROFESSIONS:
            plan = client.ns.ProfessionPathPlan(profession, 1, 300, False)
            self.assertEqual(plan.missing, 0, profession)
            self.assertIsNone(plan.gold)  # Unknown prices are never shown as a cost.
            self.assertFalse(plan.priced)

    def test_trainer_only_path_is_widened_with_vendor_recipes_only_where_it_has_to_be(self):
        client = make()
        plan = client.ns.ProfessionPathPlan(197, 1, 300, False)  # Tailoring: no trainer recipe above 225.
        self.assertTrue(plan.widened)
        vendor = [step for step in plan_steps(plan) if step['acquire'] == 'vendor']
        self.assertTrue(vendor)
        alchemy = client.ns.ProfessionPathPlan(171, 1, 300, False)  # Trainer recipes reach 300.
        self.assertFalse(alchemy.widened)
        self.assertFalse([step for step in plan_steps(alchemy) if step['acquire'] == 'vendor'])

    def test_a_large_training_fee_is_weighed_against_what_the_recipe_saves(self):
        data = recipes(make(), 164)
        prices = {item: 100 for recipe in data for item, _ in recipe['materials']}
        cheap = make(prices, {}, {'professionPathMode': 'gold'})
        baseline = plan_steps(cheap.ns.ProfessionPathPlan(164, 1, 150, False))
        used = {step['id'] for step in baseline if step['acquire'] == 'trainer'}
        self.assertTrue(used)
        costly = make(prices, {}, {'professionPathMode': 'gold'})
        swap = costly.lua.eval('''function(ns, used, restore)
            for _, recipe in ipairs(ns.ProfessionFacts(164).recipes) do
                if used[recipe.id] then
                    if restore then recipe.trainingCost = recipe.savedCost
                    else recipe.savedCost = recipe.trainingCost; recipe.trainingCost = 5000000 end
                end
            end
        end''')
        flags = costly.lua.table_from({recipe: True for recipe in used})
        swap(costly.ns, flags, False)
        try:
            avoided = plan_steps(costly.ns.ProfessionPathPlan(164, 1, 150, False))
        finally:
            swap(costly.ns, flags, True)
        self.assertLess(len({step['id'] for step in avoided} & used), len(used))  # 500 g lessons are skipped where anything else works.

    def test_vendor_value_of_crafts_changes_the_choice_and_can_be_switched_off(self):
        data = recipes(make(), 197)
        prices = {item: 200 for recipe in data for item, _ in recipe['materials']}
        plain = make(prices, {}, {'professionPathMode': 'gold'})
        first = plan_steps(plain.ns.ProfessionPathPlan(197, 60, 90, False))[0]
        other = next(recipe for recipe in Reference(data, prices, {}).candidates(60, False) if recipe['id'] != first['id'] and recipe.get('outputID'))
        sell = {other['outputID']: 100000}
        resale = make(prices, sell, {'professionPathMode': 'gold'})
        self.assertEqual(plan_steps(resale.ns.ProfessionPathPlan(197, 60, 90, False))[0]['id'], other['id'])
        ignored = make(prices, sell, {'professionPathMode': 'gold', 'professionVendorResale': False})
        self.assertEqual(plan_steps(ignored.ns.ProfessionPathPlan(197, 60, 90, False))[0]['id'], first['id'])

    def test_vendor_sell_price_is_read_from_the_eleventh_item_info_return(self):
        client = make()
        client.lua.execute('''
            C_Item = C_Item or {}
            savedItemInfo = C_Item.GetItemInfo
            C_Item.GetItemInfo = function(id)
                if id == 2996 then return "Bolt of Linen Cloth", "link", 1, 10, 0, "Trade Goods", "Cloth", 20, "", 132903, 40, 7, 5 end
                if id == 4 then error("item not cached") end
            end
        ''')
        try:
            self.assertEqual(client.lua.globals().realSellValue(2996), 40)
            self.assertIsNone(client.lua.globals().realSellValue(3))   # Not loaded yet: unknown, not zero.
            self.assertIsNone(client.lua.globals().realSellValue(4))   # A failing read is unknown too.
            self.assertIsNone(client.lua.globals().realSellValue(0))
        finally:
            client.lua.execute('C_Item.GetItemInfo = savedItemInfo')

    def test_safe_counts_cover_bad_luck_and_the_perk_reduces_the_crafts(self):
        data = recipes(make(), 171)
        prices = {item: 100 for recipe in data for item, _ in recipe['materials']}
        plan = make(prices, {}).ns.ProfessionPathPlan(171, 1, 225, False)
        steps = plan_steps(plan)
        self.assertTrue(all(step['safe'] >= math.ceil(step['crafts'] - 1e-9) for step in steps))
        self.assertTrue(any(step['safe'] > math.ceil(step['crafts'] - 1e-9) for step in steps))  # Yellow stretches need spares.
        self.assertGreater(sum(step['crafts'] for step in steps), 224 * 0.8)
        perk = make(prices, {}, {'professionPerk': True}).ns.ProfessionPathPlan(171, 1, 225, False)
        self.assertLessEqual(sum(step['crafts'] for step in plan_steps(perk)), sum(step['crafts'] for step in steps))
        self.assertTrue(perk.perk)

    def test_cheapest_and_fastest_modes_pull_in_opposite_directions(self):
        rng = random.Random(3)
        data = recipes(make(), 202)
        prices, sell = market(data, rng, known=1.0)
        gold = make(prices, sell, {'professionPathMode': 'gold'}).ns.ProfessionPathPlan(202, 1, 225, False)
        speed = make(prices, sell, {'professionPathMode': 'speed'}).ns.ProfessionPathPlan(202, 1, 225, False)
        self.assertLessEqual(gold.gold, speed.gold)
        self.assertLessEqual(speed.seconds, gold.seconds)

    def test_published_hotfixes_are_applied_to_the_bundled_reference_once(self):
        client = make()
        by_name = lambda profession: {recipe['name']: recipe for recipe in recipes(client, profession)}
        stone = by_name(164)['Coarse Grinding Stone']
        self.assertEqual((stone['grey'], stone['green']), (90, 70))
        bags = by_name(197)
        expected = {'Green Woolen Bag': (2997, 5), 'Red Woolen Bag': (2997, 5), 'Green Silk Pack': (4305, 5),
                    'Black Silk Pack': (4305, 6), 'Red Mageweave Bag': (4339, 5)}
        for name, (reagent, count) in expected.items():
            self.assertIn([reagent, count], bags[name]['materials'], name)
        self.assertEqual(client.ns.ApplyProfessionHotfixes(197), 0)  # Not applied twice.
        self.assertEqual(client.ns.ApplyProfessionHotfixes(164), 0)

    def test_path_text_shows_costs_fees_spares_and_what_to_learn(self):
        data = recipes(make(), 197)
        prices = {item: 150 for recipe in data for item, _ in recipe['materials']}
        client = make(prices, {})
        plan = client.ns.ProfessionPathPlan(197, 1, 300, False)
        text = client.ns.ProfessionPathText(197, plan)
        self.assertIn('SKILLING PATH', text)
        self.assertIn('Balanced gold and crafting time', text)
        self.assertIn('Learn from a trainer', text)
        self.assertIn('Needs a recipe sold by a vendor', text)
        self.assertIn('to be safe', text)
        self.assertIn('TOTAL', text)
        self.assertIn('in training', text)
        self.assertIn('RANK TRAINING', text)
        self.assertTrue(all(ord(char) < 256 or char in '–•…' for char in text))


if __name__ == '__main__':
    unittest.main()


class IntegrationTests(unittest.TestCase):
    """The new planner behind the existing viewer, shopping forecast and settings."""

    def client(self):
        data = recipes(make(), 197)
        prices = {item: 150 for recipe in data for item, _ in recipe['materials']}
        client = make(prices, {})
        client.lua.execute('''
            local ns = ...
            ns.professionData[197] = ns.professionData[197] or {}
            ns.professionData[197].skill, ns.professionData[197].maximum = 1, 75
            ns.professionData[197].known = ns.professionData[197].known or {}
        ''', client.ns)
        return client

    def drain(self, client):
        for _ in range(5000):
            if not len(client.lua.globals().timers):
                break
            client.lua.eval('function() local callback = table.remove(timers, 1); callback() end')()

    def test_preview_uses_the_cost_aware_path_and_keeps_the_shape_the_forecast_reads(self):
        client = self.client(); ns = client.ns
        plan = ns.PlanProfessionPreview(197, 150, False)
        steps = plan_steps(plan)
        self.assertEqual((plan.start, plan.target, plan.missing), (1, 150, 0))
        self.assertEqual(steps[0]['start'], 1)
        self.assertEqual(steps[-1]['finish'], 150)
        forecast = ns.ProfessionMaterialForecast(197, plan, False)
        self.assertEqual(len(list(forecast.groups.values())), len(steps))
        self.assertGreater(len(list(forecast.materials.values())), 0)
        self.assertEqual((forecast.start, forecast.target), (1, 150))

    def test_viewer_shows_the_priced_path_after_its_background_calculation(self):
        client = self.client(); ns = client.ns
        ns.ShowProfessionViewer(197)
        self.drain(client)
        frame = ns.professionViewer
        self.assertIsNotNone(frame.plan)
        text = frame.body.text
        self.assertIn('SKILLING PATH', text)
        self.assertIn('TOTAL', text)
        self.assertNotIn('Calculating', text)

    def test_the_current_step_counts_vendor_value_like_the_path_does(self):
        data = recipes(make(), 197)
        reference = Reference(data, {}, {})
        pair = [recipe for recipe in reference.candidates(80, False) if recipe.get('outputID') and recipe['source'] == 'trainer'
                and recipe.get('yellow') and recipe['yellow'] > 80]
        self.assertGreaterEqual(len(pair), 2)
        prices = {item: 200 for recipe in data for item, _ in recipe['materials']}
        client = make(prices, {})
        client.lua.execute('local ns = ...; ns.auctionPriceAssessment = true', client.ns)
        plain = client.ns.ProfessionNextRecipe(197, 80)
        other = next(recipe for recipe in pair if recipe['id'] != plain.id)
        client = make(prices, {other['outputID']: 500000})
        self.assertEqual(client.ns.ProfessionNextRecipe(197, 80).id, other['id'])   # Worth far more to a vendor.
        client = make(prices, {other['outputID']: 500000}, {'professionVendorResale': False})
        self.assertEqual(client.ns.ProfessionNextRecipe(197, 80).id, plain.id)      # Unless the player keeps what they make.

    def test_settings_list_the_path_options_and_changing_one_recalculates(self):
        client = self.client(); ns = client.ns
        self.assertEqual(ns.ProfessionPathOptions().mode, 'balanced')
        ns.ToggleSettings()
        for key in ('professionVendorResale', 'professionVendorRecipes', 'professionPerk'):
            self.assertIsNotNone(ns.settings.checks[key], key)
        client.lua.globals().testOptions = client.lua.table()  # Let real options through.
        before = ns.professionRevision or 0
        ns.SetOption('professionPathMode', 'gold')
        self.assertEqual(ns.ProfessionPathOptions().mode, 'gold')
        self.assertGreater(ns.professionRevision, before)
        ns.SetOption('professionPathMode', 'nonsense')
        self.assertEqual(ns.ProfessionPathOptions().mode, 'balanced')  # An unknown preference falls back.
        ns.SetOption('professionPathMode', 'balanced')
        self.assertTrue(ns.Option('professionVendorResale'))
        self.assertFalse(ns.Option('professionVendorRecipes'))
        self.assertFalse(ns.Option('professionPerk'))
