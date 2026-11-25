# Record observed instance entrances

For players:
- The addon records the last known outdoor position when you enter an instance and includes personal, build-scoped observations in `/wt research`.
- Until an entrance is observed, instance pages keep showing the available zone information without a guessed route.

Please check:
- In game, walk into an instance, open `/wt research`, and confirm the exported `instance-entrance` row has the correct name, ID, outdoor map, and coordinates.
- Confirm `/wt probe` reports the number of personal entrances recorded for the current build.

Developer notes:
- The host suite verifies capture from a cached outdoor position, build scoping, export, and that missing coordinates are not guessed. No in-game verification has been performed.
