# PLAY-FIRST GUIDE HUB AND ACTION ICONS

For players:
- Try the redesigned Play, Group and Browse tabs by enabling the new Hub beta in Settings.
- Read step and HUD icons at a glance, with a symbol fallback when a texture is unavailable.

Please check:
- Follow leveling and class-quest guides from Browse, then search for a dungeon and quest.
- Confirm Hub footer status and step icons render at HUD and Hub sizes.
- Compare 1100×620 in-game Play, Browse and Group screenshots with the adjacent mockups.

Developer notes:
- Keep the new Hub behind `uiNext` until the default flips; Settings stays in the existing settings window during this step.
- Use the scroll viewport width for all Hub content and keep its screenshot review as a pre-approval gate.
- Add generated action/HUD textures with a symbol fallback and module-tab registration through the Hub hook.
