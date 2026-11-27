# AzerothGPS pathing bridge

For players:
- Choose AzerothGPS pathing to follow Wow Together guide steps with its road-aware route and turn-by-turn arrow.
- Keep the native router selected or use automatic fallback when AzerothGPS is unavailable.

Please check:
- Install AzerothGPS 1.4.1 and its map data; follow a guide through several mapped stops.
- Check route replacement, coordinate fallback, and the AzerothGPS route confirmation in game.

Developer notes:
- Wow Together keeps guide ordering and progress; the bridge submits one destination at a time through AzerothGPS API 23.
- AzerothGPS remains separately installed. No upstream code, artwork, or map data is included. Needs play-test.
