# Brief: AzerothGPS pathing bridge

## Why
Use AzerothGPS's road-aware route planner for Wow Together guide steps while keeping Wow Together responsible for guide choice, objective order, and progress.

## What changes
- Detect AzerothGPS's public API and use `MapToWorld` plus `RouteTo` to request the active mapped guide stop, one leg at a time.
- Draw the next mapped guide stops on the AzerothGPS map as a bounded overlay, and use the public arrival callback to label the current stop without completing the quest for the player.
- Keep the native pathing option and fallback for missing APIs, unsupported coordinates, flights, and refused requests.
- Avoid duplicate Wow Together route lines and arrows while AzerothGPS is routing; report integration state in `/wt probe`.
- Keep AzerothGPS code, artwork, and map data as separate installed software; do not bundle or modify upstream files.

## Files
`WowTogether/AzerothGPSPathing.lua`, `WowTogether/Config.lua`, `WowTogether/MinimapRoute.lua`, `WowTogether/Navigation.lua`, `WowTogether/Routes.lua`, `WowTogether/StandaloneArrow.lua`, `WowTogether/WowTogether.toc`, `changes/core/azerothgps-pathing.md`, and this brief.

## Verification
No automated tests or live-game test were run for this change. Review the public API contract and coordinate conversion, run the standard host and packaging checks, then play-test guide markers, step changes, arrival, fallback, and manual route replacement with AzerothGPS 1.4.1 plus its map data installed.

## Acceptance
With AzerothGPS API 23 installed and an active mapped guide step, AzerothGPS routes to that step and draws up to 24 upcoming Wow Together guide stops on its map. Arrival is shown in Wow Together but never completes an objective automatically. Without AzerothGPS or a mapped point, Wow Together keeps its native pathing. `/wt probe` reports the selected backend and fallback state.
