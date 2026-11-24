# OPTIONAL GOLD TAB AND PRICES AND OBSERVATIONS

For players:
- Add the optional Gold tab and `/wt gold` command when Gold is installed.
- View vendor values and optional TSM/auction quotes with age and confidence.
- Record loot, gathering and dungeon visits; choose whether to share anonymous observations with your party.

Please check:
- With Gold installed, open its tab and run `/wt gold`; without it, confirm the core addon still loads.
- Check vendor, auction and optional TSM price sources, including missing-source behavior.
- Record loot and gathering, inspect `/wt probe`, and confirm party sharing contains no names or chat text.

Developer notes:
Register the optional addon through the versioned public module API. Keep prices feature-probed and scoped by realm, faction and build. Keep observations build-scoped, capped, anonymous, and marked with provenance and sample size; exports remain review candidates only.
