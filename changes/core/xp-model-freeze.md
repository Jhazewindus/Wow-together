# XP MODEL WATCHDOG HOTFIX

For players:
- Keep XP-based quest filtering off by default until its route estimate passes in-game testing.
- Run `/wt probe` without triggering a zone plan or loading optional dungeon data.

Please check:
- With the XP model enabled, refresh a large zone guide and confirm it does not freeze.
- Run `/wt probe` before refreshing a guide; it should report “not computed yet” and open promptly.

Developer notes:
- Build shared catalogue indexes for XP references, level candidates and follow-ups; memoize values by completion revision.
- Keep probe output cached-only and retain the XP model's off-by-default state pending in-game acceptance.
