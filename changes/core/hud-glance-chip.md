# HUD GLANCE AND SUGGESTION CHIPS

For players:
- Show the current task at a glance, with the next two tasks and quiet suggestions inside the guide card.
- Use a compact HUD bar to pause, open the Hub, close, or switch between the full guide and Glance.

Please check:
- Toggle Glance from the step count and verify the current task and next two remain visible.
- Trigger and dismiss a suggestion chip; confirm it is non-modal and does not return.
- Pause, stop and close from the HUD; confirm each action does what its label says.

Developer notes:
- Add the icon-table texture probe with the specified glyph fallback and preserve saved frame names.
- Keep chips non-modal, single-visible, time-limited and dismissed until their trigger changes.
