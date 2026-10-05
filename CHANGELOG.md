# Wow Together changelog

## 0.6.0

- Keep the chosen guide through quest acceptance and zone changes. Scan guide
  now replans real progress without a report popup; optionally reconsider skips.
- Filter low-level pickups, explain useful chain/dungeon exceptions and focus
  party routes on the member behind in known progression.
- Refresh Classic-style panels with grouped settings and dropdowns. Rename
  Library to All quests and the old All quests to Party quests.
- Add a current-quests choice at guide start, previous/next previews, yards or
  metres, automatic party-panel visibility and dungeon Start route.
- Distinguish Kill, Pick up and Talk instructions. Add cross markers/item hints,
  observed NPC pickup availability and opt-in selection of the current NPC quest.
- Add observed flight-network suggestions, flight clocks and optional flight
  selection; show corpse directions while retaining the guide. Beta testing is
  required for the new APIs/actions; unknown data keeps travel manual.
- Add quest-log review suggestions and expand the friend test checklist.
  Known repeatable filtering is retained; the reported repeatable was already fixed.

## 0.5.7

- Keep known repeatable quests out of automatic leveling plans, including
  **Spirit of the Wind**. They remain available in the quest library.
- Add **Skip step**, **Skip quest** and **Scan guide** to the arrow. Skips are
  saved per character; settings can reset them. Starting a guide checks its
  quests, known series and prerequisites against real progress/history.
- Remove skulls for completed mob objectives without letting the generic
  quest-related flag restore them. Other unfinished objectives stay marked.
- Redraw unprotected addon map geometry during combat pan/zoom. Protected
  drawing and native waypoint/map actions still wait until combat ends.
- Add the recurring Discord release command with matching archive/docs and
  confirmed-post receipts to prevent duplicate uploads.

## 0.5.6

- Focus map lines and markers on the current place and two ahead. Map controls
  switch to the full route or choose zero, one or two places ahead.
- Prioritize mapped active quests over discovery; finish local work before
  distant deliveries. Improve objective walking order without moving returns
  ahead of their work.
- Keep cross-zone routes, explain the next stop under the arrow, and add
  **View route zone** when viewing another map. The first leg follows your
  current public position; quest progress advances the preview.
- Add opt-in turn-in for opened NPC quest dialogs with no reward choice.
  Reward choices remain manual; beta action compatibility needs testing.

## 0.5.5

- Fix the general **Vile Familiars** being blocked behind a Warlock-only
  introduction. Parallel class variants now keep their own prerequisites;
  **Burning Blade Medallion** still requires its completed prerequisite.
- Include a friend-testing checklist and copyable bug-report template.

## 0.5.4

- Bundle eligible nearby pickups with current party quests, within the walking
  budget. Ready turn-ins stay first; missing objective locations stay partial.
- Add a nearby-pickup setting and retain pickup stages in shared party routes.

## 0.5.3

- Smooth main-window resizing and add **Start route**, with **Follow route** /
  **Keep my route** invitations for friends.
- Improve prerequisite, faction and nearby-zone checks; name NPCs on arrival.

## 0.5.2

- Add **Finish our current quests first** and prioritize ready turn-ins.
- Repair world-map projection, clipping and clustered route pins.

## 0.5.1

- Add the movable navigation arrow for a selected route.

These are beta releases. The testing script checks actual client behavior;
host tests alone do not establish that every API or drawing path works.
