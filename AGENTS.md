# Wow Together release workflow

Always reply in English, including when friends' reports are written in Dutch.

The user has authorized posting every completed addon update to their configured
Discord channel webhook. Include the full release archive, the changelog and
the friend-testing checklist in one message. Do not ask for posting permission
again for ordinary updates to this addon and channel.

The user has also authorized publishing the addon source and release history to
`Jhazewindus/Wow-together` on GitHub, including future completed updates. Push the
tested working branch and its annotated release tag, preserving prior history.
Keep a reviewable pull request for changes destined for `main`; attach any created
or updated pull request to the chat. Verify the remote branch/tag commit IDs before
reporting success. Do not force-push, replace existing tags or merge without an
explicit request. GitHub source publication complements the Discord builds.

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
   version tag, and push the development branch and that tag to GitHub. Update
   the pull request to describe the final code and validation. Report GitHub
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
