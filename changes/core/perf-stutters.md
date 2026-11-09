# Steadier Elevator Travel Checks

For players:
- Recheck travel directions less often after large position changes, reducing recurring stutters near elevators.

Please check:
- Ride an elevator while following a route and confirm directions still recover after moving away from the path.
- Confirm major detours and map changes still refresh travel directions.

Developer notes:
- Rate-limit detour replans to once every five seconds and flight-discovery scans to movement checks spaced at least thirty seconds apart; run discovery route search only when an eligible nearby flight master exists.
