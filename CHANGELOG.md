# Wow Together changelog

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
