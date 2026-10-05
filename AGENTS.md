# Wow Together release workflow

The user has authorized posting every completed addon update to their configured
Discord channel webhook. Include the full release archive, the changelog and
the friend-testing checklist in one message. Do not ask for posting permission
again for ordinary updates to this addon and channel.

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

Read `DISCORD_WEBHOOK_URL` from the environment. For a webhook supplied in the
current conversation, `--prompt` permits hidden input without writing it to a
file. Never commit or print the webhook token, store it in release archives or
add it to the addon. Persistent values belong in environment settings.

Work in the existing checkout; preserve user changes. Do not push to GitHub or
publish a new environment solely to make the Discord release appear successful.
