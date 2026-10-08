# Wow Together release workflow

Always reply in English, including when friends' reports are written in Dutch.

The user has authorized posting every completed addon update to their configured
Discord channel webhook. Include the full release archive, the changelog and
the friend-testing checklist in one message. Do not ask for posting permission
again for ordinary updates to this addon and channel.

The user has also authorized publishing the addon source and release history to
`Jhazewindus/Wow-together` on GitHub, including future completed updates. The user
requires direct pushes to `main` for tested updates. Work on `main` in the existing
checkout, fetch and incorporate remote changes, then push normally with the
matching annotated release tag. Do not require pull requests or ask for posting
permission again; create a pull request only if specifically requested. Preserve
history: do not force-push or replace existing tags. Verify remote commit/tag IDs
before reporting success. GitHub source publication complements Discord builds.

## Include the quest-guide agent's work before releases

Before every addon release, check `origin/guides/coverage` for new quest-guide
commits as well as checking `origin/main`. The checkout may fetch only `main`;
explicitly fetch the guide branch with
`git fetch origin main refs/heads/guides/coverage:refs/remotes/origin/guides/coverage`
or retain an equivalent fetch mapping. Check at the start of an update and again
before the final build/publication.

Review the guide commits not yet in `main`, including their source evidence,
data changes, generated outputs and tests. Incorporate completed, relevant
changes into the release on `main`; do not silently omit ready guide updates.
Preserve both agents' work when resolving ordinary merge conflicts. Ask the
user before resolving contradictory product choices or changing established
guide fundamentals. Do not blindly merge experimental/unrelated branches or
unfinished work. Explain any deferred guide commits and the concrete reason.

Test the combined code and quest data after integration, then finalize the
version, changelog, test checklist and ZIP. If more guide commits arrive before
publication, review them and repeat affected integration/checks before building
the final archive. Record integrated guide work in the release notes. Push the
tested combined `main` and annotated tag to GitHub, verify their remote IDs,
then publish that same release's ZIP and matching docs to Discord. A workflow
instruction change alone does not require an addon version or Discord release.

For each addon release:

1. Keep Forever interface `16001` and Lua 5.1. Update the version in the TOC and
   diagnostic heading; update README, CHANGELOG.md and TESTING.md for the release.
2. Run relevant host checks with `/workspace/.wow-together-tests/bin/python`.
   These cannot establish actual WoW beta API behavior or map rendering.
3. Build and publish using `python3 tools/build_release.py --post-discord`.
   The uploader attaches docs extracted from that ZIP so versions cannot drift.
   Use `python3 tools/post_discord_release.py <archive> --dry-run` to preview.
4. Report a Discord post as successful only after the API confirms its message
   ID and all three attachments. Receipts in the artifact directory prevent
   reposting the same release; changed files require a new release version.
5. If posting is blocked, finish the complete ZIP and report the specific
   external blocker. Preserve proxy routing and certificate verification.
   Ambiguous failures require checking channel history before retrying.
6. Commit the tested source and matching release notes, create the annotated
   version tag, and push `main` and that tag directly to GitHub. Report GitHub
   and Discord outcomes separately if either destination fails.

Read `DISCORD_WEBHOOK_URL` from the environment. For a webhook supplied in the
current conversation, `--prompt` permits hidden input without writing it to a
file. Never commit or print the webhook token, store it in release archives or
add it to the addon. Persistent values belong in environment settings.

Work in the existing checkout; preserve user changes. Do not push to GitHub or
publish a new environment solely to make the Discord release appear successful.

## Reviewing reports from the user and friends

Before implementing feedback, compare all reports supplied for that batch.
The user will identify their own report; preserve that label and each friend's
identity. Do not assume an unlabeled report belongs to the user.

Group overlapping symptoms and likely shared causes, and track issues observed
by individual players. Compare the reported addon version, client build, level,
faction, class, zone, party state, settings and selected route where available.
Distinguish evidence from hypotheses; similar symptoms can have different causes.
Briefly share the comparison and fix priorities before changing addon code.
If suggestions contradict each other or the user's established preferences,
explain the conflict and ask the user which direction to take before implementing
changes from that batch. Wait for their answer; do not silently choose a side or
implement a compromise. Read-only investigation may continue to clarify the
options. Different observations alone are not necessarily conflicting requests.
If the user explicitly says more reports are still coming for the batch, collect
them before implementing fixes. Otherwise continue within the authorized task.

Changes to this review workflow alone do not constitute a new addon release.

## Project direction

Treat WoW Together as a **WoW Forever companion**. This is the user's standing
product direction from 6 October 2026. Keep the product name **WoW Together**;
"WoW Forever companion" describes the mindset, not a rename. Keep leveling as
the backbone, with supporting tools for travel, dungeon preparation, training
and solo/group play.
Party quest sync remains one part of that wider companion.

Use this direction when evaluating features, naming and interface design.
Keep supporting tools optional and the interface compact and coherent. Prioritize
reliable, useful guidance for the player's current situation, with clear next
steps and build-tested behavior. Preserve working guide fundamentals and the
user's established preferences while developing the wider companion. Work toward
a polished 1.0 release; current updates remain beta releases until that milestone.

Keep player-facing screens concise. Show quest actions, destinations, progress,
levels and useful choices. Keep developer discussion, API limitations, source
coverage, raw IDs and chat commands in diagnostics/help/documentation rather than
routine screens and tooltips. Use brief, honest empty states such as "Map
unavailable" when content is missing; preserve explanations that help a player
make a decision, including useful low-level prerequisite exceptions.
