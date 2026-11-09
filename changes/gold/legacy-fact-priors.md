# PINNED LEGACY GOLD FACT PRIORS

For players:
- Add optional, provenance-tracked legacy loot and spawn priors to support Gold suggestions.
- Flag facts that appear in Questie Forever change lists without importing Questie data.

Please check:
- Rebuild the priors from the pinned cmangos snapshot and compare the output hashes.
- Confirm each generated row retains provenance, the GPL notice and the Questie-changed flag where applicable.

Developer notes:
- Extend the tools pipeline for creature/gameobject loot, spawn locations and spawn times from the manifest-pinned snapshot.
- Keep Questie source data excluded beyond the change-list flag until the license policy is updated.
