# Release automation and changelog fragments

## Policy

Release notes are authored once per pull request as exactly one file:
`changes/<branch>.md` (the branch path is preserved, including its slash).
A visible-change fragment has this shape:

```md
# RELEASE NAME

For players:
- Plain-language change, at most three lines.

Please check:
- One to three friend-sized checks.

Developer notes:
- Implementation details useful to reviewers.
```

A PR with no player-visible change uses `internal: true` and a developer-notes
section instead of the player/check sections. PRs do not edit the TOC version or
`CHANGELOG.md`. The source `CHANGELOG.md` is frozen at 0.8.110 as historical
reference. The release-policy bootstrap PR is the one-time migration that sets
the TOC placeholder and trims the history; all later PRs are checked strictly.

## PR builds

`.github/workflows/pr-build.yml` runs the host suite, syntax and module-boundary
checks. `tools/ci_release.py validate-pr` verifies exactly one new fragment at
the branch-matching path, the fragment format, and that the TOC version and
`CHANGELOG.md` were not edited. The next beta version is the last reachable
`vMAJOR.MINOR.PATCH` tag plus one patch, stamped into the package only as
`<next>-beta.<pr>.<sha>`. The source TOC remains `@project-version@`. Beta ZIPs
are named with the branch and SHA, posted only to `#beta-builds`, and retained
as workflow artifacts. The installed `/wt` version fallback is `dev`.

## Main releases

On a push to `main`, `.github/workflows/release.yml` finds newly added
`changes/*.md` files since the latest reachable `v*` tag. If there are no
fragments, or every fragment says `internal: true`, it exits without making a
release. Otherwise it calculates the next patch version, assembles the notes,
runs the release checks, stamps version/release-name into the packaged TOC,
builds the ZIP, creates the `v*` GitHub Release and posts the ZIP to Discord.
The generated package gets a release section prepended to its copy of
`CHANGELOG.md`; the repository copy is never updated by CI. CI may create a tag
and GitHub Release, but never commits to `main`.

Discord posts carry the release name, combined player notes, install steps and
checks. Developer notes are spoiler-wrapped. Release posts include the ZIP
attachment and require a confirmed Discord message ID and attachment list.
Beta posts are labelled as beta and are not releases.

## Validation

Host tests cover fragment format and count, branch/path matching, rejection of
TOC-version and changelog edits, internal-only no-release behavior, next-tag
versioning, beta/release package stamping, archive layout, release-note assembly,
Discord dry-run formatting and confirmed attachment receipts. A live Discord
post occurs only from the trusted main workflow with the repository secret.
