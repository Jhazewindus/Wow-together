# Automated builds and releases

Each pull request adds exactly one `changes/<branch>.md` release fragment. A
visible-change fragment has a release-name heading, `For players` (at most three
lines), `Please check` (one to three items), and developer notes. A change with no
player-visible result uses `internal: true` and developer notes. The PR check
rejects missing or extra fragments, TOC-version edits, and edits to
`CHANGELOG.md`. The one-time `core/release-fragments` bootstrap establishes this
policy and freezes the repository changelog at 0.8.110.

A pull request runs the host suite and other PR checks, then builds a beta ZIP.
The next beta version is derived from the latest reachable `v*` tag and stamped
into the packaged TOC as `<next>-beta.<pr>.<sha>`; the repository TOC remains
`@project-version@`. A successful same-repository PR build sends that ZIP to the
beta channel from trusted default-branch code. The message names the branch, PR
and commit, and says it is not a release. Fork PRs cannot access webhook secrets.
The beta archive remains a workflow artifact for 14 days.

On a push to `main`, CI collects newly added fragments since the latest reachable
`v*` tag. No fragments, or internal-only fragments, means no release and no post.
Otherwise CI calculates the next patch version, assembles the visible fragments,
runs checks, stamps the version and release name into the packaged TOC, builds a
release ZIP, creates the GitHub Release and posts the ZIP to Discord. It never
commits to `main`. The generated package has a release section prepended to its
copy of `CHANGELOG.md`; the repository copy remains frozen history. If the build
exceeds 25 MB, core and data ZIPs must each fit the limit and arrive on one
message.

Discord receives player notes, install instructions and quick checks; developer
notes are spoiler-wrapped. Release posts require a confirmed message ID and the
full attachment list. If delivery is ambiguous, inspect the workflow receipt and
channel history before any retry. Successful uploads save `discord-receipt.json`
with the message ID and confirmed attachment names; webhook values are excluded.

The trusted beta-publishing workflow must first be merged onto the default
branch. A PR that introduces it cannot demonstrate the beta-posting path before
that bootstrap merge. Subsequent PR builds exercise the complete flow. The full
host suite is divided by test file across four isolated runners. Local sequential
runs take longer; runner queues and CI timing should be monitored after rollout.

## Owner setup

In GitHub repository Settings → Secrets and variables → Actions, create these
repository secrets using the intended channels' webhook URLs:

- `DISCORD_BETA_WEBHOOK`: the `#beta-builds` channel webhook.
- `DISCORD_RELEASE_WEBHOOK`: the `#releases` channel webhook.

Enter webhook values directly in GitHub's secret fields. They are passwords;
never put them in source, issues, PR descriptions, logs or Codex environments.
No personal GitHub token is needed: workflows use their scoped `GITHUB_TOKEN`.

In Settings → Rules → Rulesets (or Branches → Branch protection), protect `main`:
require a pull request, one approving review, and the `PR checks` status check.
Disable bypasses that would let automation merge or push directly. The owner
approves and squash-merges. If Codex lacks repository administration/API login,
these settings must be completed by the owner; committed workflow files cannot
create repository secrets or turn branch protection on by themselves.

Pin this line in `#releases`:

> Download the ZIP from #releases, unzip its addon folders into Interface/AddOns, replace the matching folders and fully restart; #beta-builds is for testing branches only.

## Updating the addon

Add one `changes/<branch>.md` file per PR. Do not change the TOC version or
`CHANGELOG.md`. Release versions are calculated from the last reachable `v*`
tag, and only generated packages receive a stamped version. `CHANGELOG.md` ends
at 0.8.110 and remains the historical reference.

## Verify the rollout

Open a same-repository PR and check the beta message and downloadable ZIP. Merge
a reviewed visible-change PR and check the new GitHub Release, Discord message ID
and attachment names. Merge an internal-only PR and confirm the workflow creates
no release. Install by replacing the sibling addon folders and fully restarting
WoW. Host checks validate packaging and the message protocol; they do not
establish live webhook credentials, channel permissions, GitHub settings, runner
latency or in-game behavior.
