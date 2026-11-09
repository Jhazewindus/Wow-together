# XP calculation and diagnostics responsiveness

## Why

Players still see long freezes after route calculation and when running `/wt probe`. Guide activation calculates a full-guide XP estimate synchronously, and the probe recomputes a destination decision that can enter quest-chain and zone-policy planning.

## What changes

- Keep `/wt probe` read-only and cached-only for the current destination; report route step metadata without recomputing policy.
- Move full-guide XP estimates to a cancellable, timer-driven coroutine. Limit each callback to one guide record and return a clear pending label until it completes.
- Keep existing XP estimate eligibility and reward behavior, but run per-quest policy work in timer-driven cooperative slices.
- Only update `GuideXP.lua`, `GuideReasons.lua`, `tests/test_xp_model.py`, this brief, and `changes/core-xp-model-probe-freeze.md`.

## Tests

- A probe with an active guide step does not call destination planning, XP projection, or chain-value functions.
- XP projection yields while visiting a large guide; timer-driven capture advances in bounded record slices and eventually records a result.
- Calling the XP text renderer while no result is cached returns immediately and queues background work.
- Lua 5.1 compile, full host suite, boundary check, and release build.

## Acceptance

No XP estimate or `/wt probe` path performs a full guide projection or destination-planning pass synchronously. The XP model remains display-only and route behavior is unchanged.
