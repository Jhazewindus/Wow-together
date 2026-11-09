# Smoother Party Route Updates

For players:
- Reduce repeated route and HUD work while following a guide in a party.
- `/wt probe` now reports rolling Lua heap changes by subsystem and current sampled heap size.

Please check:
- Follow a route in a party and confirm the minimap line, travel arrow and step text stay responsive.
- Run `/wt probe` and compare addon memory before and after a manual full garbage collection.

Developer notes:
- Reuse navigation, map-line, travel waypoint and recorder state; cache route text and contexts; add a fixed 60-second subsystem ledger. The ledger samples net Lua heap growth and never triggers collection. The 30-minute retention and external addon-monitor target still require in-game verification.
