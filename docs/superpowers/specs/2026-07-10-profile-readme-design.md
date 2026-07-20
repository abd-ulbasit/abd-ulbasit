# Profile README: Terminal-Style Card with Live GitHub Stats

**Date:** 2026-07-10
**Repo:** abd-ulbasit/abd-ulbasit (GitHub profile README)

## Goal

Replace the current markdown README with an Andrew6rant-style neofetch card:
an SVG image showing an ASCII-art portrait on the left and system-info-style
fields on the right, with GitHub stats refreshed daily by a GitHub Actions
workflow.

## Approach

Adapt Andrew6rant/Andrew6rant's open-source setup (Python `today.py` +
GraphQL API + SVG rewriting) rather than off-the-shelf stat widgets or a
from-scratch generator. It is proven, matches the target look exactly, and
already solves GraphQL pagination and lines-of-code caching.

## Components

1. **ASCII portrait** — generated once from the GitHub avatar of
   `abd-ulbasit` (image → grayscale → character ramp), sized to match the
   card's left column (~40 cols × ~30 rows). Static; embedded in both SVGs.

2. **`dark_mode.svg` and `light_mode.svg`** — the full card. SVG `<text>`
   elements with monospace font, dotted leaders, and theme-appropriate
   colors. Elements that hold live values carry stable `id` attributes
   (`age_data`, `repo_data`, `contrib_data`, `commit_data`, `star_data`,
   `follower_data`, `loc_data`, `loc_add`, `loc_del`) so the script can
   rewrite them.

3. **`today.py`** — Python script that:
   - computes Uptime from birthdate **2003-09-08** (years, months, days);
   - queries the GitHub GraphQL API for repo count, contributed-repo count,
     total commits, stars, followers;
   - computes lines of code added/deleted across owned repos, with a
     committed cache file (`cache/`) so daily runs stay cheap;
   - rewrites the `id`-tagged SVG elements in both SVG files.

4. **`.github/workflows/main.yml`** — Actions workflow: daily cron +
   manual `workflow_dispatch` + push trigger; runs `today.py` with a
   repo-scoped `ACCESS_TOKEN` secret and commits changed SVGs/cache.

5. **`README.md`** — replaced by a `<picture>` element:
   `prefers-color-scheme: dark` → `dark_mode.svg`, default →
   `light_mode.svg`.

## Card content

- **Header:** `basit@abd-ulbasit`
- **OS:** macOS, Linux — **Uptime:** live age from 2003-09-08 —
  **Host:** Elite IT Team — **Kernel:** Software Engineer, Platform &
  Distributed Systems — **IDE:** VSCode, Neovim
- **Languages.Programming:** Go, TypeScript, Python, JavaScript —
  **Languages.Cloud:** Kubernetes, Docker, AWS, CI/CD —
  **Languages.Real:** English, Urdu
- **Hobbies.Software:** Kubernetes Operators, CRDT Sync —
  **Hobbies.Hardware:** Homelab (ThinkPad k8s cluster)
- **Contact:** basit@basit.engineer, LinkedIn `abd-ulbasit`,
  Portfolio `abd-ulbasit.vercel.app`
- **GitHub Stats (live):** Repos {Contributed}, Stars, Commits, Followers,
  Lines of Code (net, +added / −deleted)

## Error handling

- Script fails loudly (non-zero exit) on API errors so the Action shows red
  instead of silently committing wrong numbers.
- LOC cache misses (new repos) are fetched and appended; existing entries
  are only refetched when the repo's commit count changes.
- Workflow commits only when files actually changed.

## Testing

- Run `today.py` locally with a personal access token before first push;
  verify SVG renders correctly in both GitHub themes.
- Trigger `workflow_dispatch` once after setup to verify the token secret
  and the auto-commit path.

## Out of scope

- Live-regenerating the ASCII portrait when the avatar changes.
- The old README content (skill icons, badges) — fully replaced; recoverable
  from git history.
