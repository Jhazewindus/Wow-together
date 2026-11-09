# Brief — Release automation: PR builds, releases, Discord, WowUp

## Goal
No human builds zips or posts them. A PR produces a testable build posted
to Discord by itself; a merge to `main` produces a release posted to
Discord with the zip **attached**; friends download from Discord and unzip
into AddOns, as today — the file just arrives on its own. The owner's job
is approve + merge. No GitHub accounts, WowUp or public repo required.

## Pieces
1. **`tools/build_release.py`** (exists) — must accept `--output <path>` and
   `--label <text>` and exit non-zero on any missing TOC file. Zip layout
   = the addon folders at the zip root (`WowTogether/`,
   `WowTogether_QuestData/`, …, `WowTogether_Gold/` when present), nothing
   else. Assert this layout in a test; WowUp depends on it.
2. **`.github/workflows/pr-build.yml`** — on `pull_request` (opened,
   synchronize):
   - checkout; set up Python; `pip install lupa`;
   - run the host test suite, `tools/syntax_check.py` (or equivalent),
     `tools/boundary_check.py`;
   - `python3 tools/build_release.py --output dist/ --label <branch>`;
   - post to Discord `#beta-builds` via webhook (`DISCORD_BETA_WEBHOOK`
     secret) as a **multipart message with the zip attached** (webhook
     limit 25 MB; the zip is ~9 MB). First line: "Beta build — `<branch>`
     (#<pr>) — not a release". Then the PR title and the first 10 lines
     of the changelog diff. Zip name: `WowTogether-beta-<branch>-<short
     sha>.zip` so it can never be mistaken for a release;
   - also keep the zip as a workflow artifact (14 days) for the record.
3. **`.github/workflows/release.yml`** — on `push` to `main`:
   - read `## Version:` from `WowTogether/WowTogether.toc`; fail if a tag
     `v<version>` already exists (version not bumped) or if
     `CHANGELOG.md` has no `## <version>` heading;
   - run the same checks as the PR build;
   - build `WowTogether-<version>.zip`; create a GitHub Release
     `v<version>` with the changelog section as body and the zip as the
     asset;
   - post to Discord `#releases` (`DISCORD_RELEASE_WEBHOOK`) with the zip
     **attached**: first line "**Wow Together <version> — <release
     name>**", then the changelog section, then "Install: unzip into
     Interface/AddOns, replacing the four folders; restart the client."
     The GitHub Release is the archive of record; nobody needs to open it.
4. **Secrets**: two Discord webhook URLs as repository secrets; nothing
   else. No tokens in Codex environments.
5. **Branch protection on `main`**: require the PR workflow to pass;
   require one approval (you). Codex cannot merge.
6. **Friends' install**: download the zip from `#releases`, unzip into
   AddOns — unchanged from today. Pin a one-line message in the channel
   saying exactly that, and that `#beta-builds` is for testing branches
   only.
7. If the zip ever exceeds 25 MB (data add-ons growing), split the
   release into `WowTogether-<version>.zip` (core) and
   `WowTogether-data-<version>.zip`, posted as two attachments on one
   message, with the install line naming both.
8. Optional later: WowUp/CurseForge via the BigWigsMods packager if the
   addon ever goes public. Not needed now.

## Message formats (what the webhook posts)

Each `CHANGELOG.md` entry gets two short subsections above the developer
bullets, written by Codex with the change:
```
## 0.8.108
**SUGGESTION CHIPS**
For players:
- Pop-ups are gone: dungeon, party-route, save-and-pause and collection prompts are now one quiet line under the guide card.
- Grouping asks whether to switch to party mode; leaving the group switches back.
Please check:
- Enter a dungeon zone: a chip appears, nothing blocks the screen.
- Group up: the party-mode question appears once.
- (developer bullets as today)
```
`For players` ≤ 3 lines, plain language, no identifiers, file names or
test counts. `Please check` ≤ 3 items a friend can do in five minutes.
The release workflow refuses to run if the entry lacks `For players`.

**Release post** (`#releases`, zip attached, nothing else attached):
```
**Wow Together 0.8.108 — SUGGESTION CHIPS** — World of Warcraft: Forever (live)

<For players block>

Install: replace `WowTogether` and the matching `WowTogether_*` sibling folders in `Interface\AddOns\` on every member's client, then fully restart.

Please check:
<items>

||Developer notes:
<developer bullets>||
```

**Beta post** (`#beta-builds`, beta zip attached):
```
**Beta build — `core/ui-chips` (#42) — not a release**
<PR title>
<For players block from the entry, if present>
Please check: <items>
```
The full CHANGELOG.md and TESTING.md are not attached; they live in the
repo and the GitHub Release.

## Codex rules that make this work (already in place; now enforced)
- Every PR bumps `## Version` in the TOC and adds the `## <version>`
  changelog heading — the release workflow refuses to run otherwise.
- The version string appears in exactly one place (the TOC); the
  changelog heading must match it.
- Branches: `core/<topic>` (A), `gold/<topic>` (B); squash-merge.

## Tests / acceptance
- A PR from a branch posts a Discord message within 5 minutes with the
  beta zip attached and labelled as a beta; a tester installs it without
  help.
- Merging a PR with a bumped version creates `v0.8.108` and posts the
  release zip to `#releases` with the changelog; the first line carries
  the version.
- Merging a PR **without** a version bump fails the release workflow
  with a clear message, and nothing is posted.
- The release zip's top-level entries are exactly the addon folders.
