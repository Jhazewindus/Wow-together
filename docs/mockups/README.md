# UI mockups (reference for the redesign)

Open any `.html` file in a browser. These boards are the visual reference for UI changes in this repository.

| file | screen |
|---|---|
| Main.html | HUD step card: step icon on the left, chip inside the card |
| HudGlance.html | HUD Glance mode: current step + next two |
| HudTravel.html | HUD travel leg borrowing the card |
| HudArrow.html | Floating guide arrow above the card, and its four states |
| HubPlay.html | Hub — Play tab |
| HubGroup.html | Hub — Group tab |
| HubBrowse.html | Hub — Browse tab |
| HubSettings.html | Hub — Settings tab |
| HubGold.html | Hub — Gold tab (module, later) |

The guide arrow is a separate frame, not part of the step card. It has no background, moves independently with its own saved position, starts just above the card, supports 75–150% scale and its own visibility setting, and reads the card's target. It shows a rotating gold arrow, distance and time while walking; orange-red when facing more than 120° off course; a green check on arrival; a transport icon while casting/flying; and hides with no target.

For this UI PR, place real in-game captures beside these boards: `Main-game.png`, `HudGlance-game.png`, `HudArrow-game.png`, `HubPlay-game.png`, `HubBrowse-game.png`, and `HubGroup-game.png`. Captures must be 1100×620. Do not use browser renders or generated images as evidence. Before approval, compare each capture side by side with its matching HTML and check clipping, readable type, the primary action, and the footer. The Hub Settings rail tab is intentionally hidden until redesign step 4; do not mark step 3 accepted without the required captures and visual comparison.
