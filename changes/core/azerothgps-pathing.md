# AzerothGPS pathing bridge

For players:
- Choose AzerothGPS pathing to follow Wow Together guide steps with its road-aware route and turn-by-turn arrow.
- See upcoming mapped guide steps on AzerothGPS's map and get an arrival note in the guide card.
- Keep the native router selected or use automatic fallback when AzerothGPS is unavailable.

Please check:
- Install AzerothGPS 1.4.1 and its map data; follow a guide through several mapped stops.
- Check upcoming-stop markers, arrival status, route replacement, coordinate fallback, and route confirmation in game.

Developer notes:
- Wow Together keeps guide ordering and progress; the bridge submits one destination at a time and draws up to 24 upcoming mapped stops through AzerothGPS API 23. Arrival never completes a quest objective.
- AzerothGPS remains separately installed. No upstream code, artwork, or map data is included. Needs play-test.
