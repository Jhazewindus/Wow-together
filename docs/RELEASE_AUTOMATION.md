# Automated builds and releases

A pull request runs `PR checks` and produces a beta ZIP; a successful same-repository
PR build sends that ZIP to the beta channel. The message names the branch, PR and
commit, and explicitly says it is not a release. Fork PRs run checks without access
to repository webhook secrets. The beta archive remains a workflow artifact for
14 days. Beta delivery runs from trusted default-branch code after the checks,
without executing files from the PR artifact.

A push to `main` validates the TOC version, matching changelog entry, player notes
and unused `v<version>` tag, runs all checks, and builds the release. GitHub Releases
stores the ZIP and full changelog section. Discord receives the ZIP attachment,
player notes, install instruction and quick checks; developer notes are spoilers.
CHANGELOG.md and TESTING.md are not separate Discord attachments. If the build
exceeds 25 MB, core and data ZIPs must each fit the limit and arrive on one message.

The trusted beta-publishing workflow must first be merged onto the default
branch. A PR that introduces it cannot demonstrate the beta-posting path before
that bootstrap merge. Subsequent PR builds exercise the complete flow. The full host suite is divided by test file across four isolated runners to
target beta delivery within five minutes. A local sequential run takes about nine
minutes; runner queues and measured CI shard timings still need rollout verification.

## Owner setup, once

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

The old manual uploader remains for historical releases; the new workflows are
the normal publication path. Do not manually trigger a second webhook post after
an ambiguous network failure. Check the channel and workflow receipt first.
Successful CI uploads save `discord-receipt.json` with the message ID and confirmed
attachment names; webhook values are excluded.

## Updating the addon

Bump `## Version:` in `WowTogether/WowTogether.toc` and add its exact `## <version>`
changelog entry. Include `For players` (at most three short lines), `Please check`
(at most three quick checks), then any developer notes. Keep the TOC as the single
runtime source of the version. Release preflight runs before publishing anything,
so a missing version entry, missing player notes or an existing release tag stops
the release with an error.

## Verify the rollout

Open a same-repository PR and check the beta message and downloadable ZIP. Merge
a reviewed version bump and check the new GitHub Release plus the Discord message
ID and attachment names. Install by replacing the sibling addon folders and fully
restarting WoW. Host checks validate the packaging and message protocol; they do
not establish a live webhook's credentials, channel permissions, GitHub settings,
runner latency or in-game behavior.

## Resume Discord delivery after a failed post

GitHub release creation and Discord delivery are separate jobs. The normal push
path always rejects an existing version tag. If a release was created but delivery
failed, first check the Discord channel and the delivery receipt artifact. Never
retry when a message ID or the ZIP attachment confirms delivery.

Only after confirming the message is absent, open Actions → Release → Run workflow
on `main`, enter the existing version without `v`, and check **confirmed_absent**.
This downloads the existing GitHub Release assets, checks their version and sends
those same ZIPs. It does not rebuild, retag, or create another GitHub Release.
The checkbox defaults to false; without it no delivery job runs. No timeout or
HTTP failure automatically triggers this path.
