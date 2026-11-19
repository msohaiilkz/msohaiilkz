# Muhammad Sohail — Safe Animated GitHub README Kit

A self-contained **code update kit**, not a modification of your live GitHub account.
It is tailored to the README text supplied in chat for `msohaiilkz`.

## What is included

- `config.json` — your name, original cyan/navy/blue brand, three verified-by-you contact destinations, five featured repositories and their existing links.
- `scripts/render_cards.py` — ONE Python script rendering all 11 cards into `cards/`.
- `scripts/fetch_contributions.py` — GitHub GraphQL daily contributions and GitHub REST public repository metadata. No fabricated data.
- `scripts/patch_readme.py` — previews or inserts a new card section **without deleting existing README content**. Creates a timestamped backup before applying.
- `scripts/validate_cards.py` — validates SVG XML, reduced-motion CSS, embedded fonts and absence of external scripts.
- `.github/workflows/refresh-profile-cards.yml` — daily scheduled refresh, generation, validation and **scoped commit** of `cards/` and `data/contributions.json` only.
- `data/contributions.json` — honest `pending` placeholder, NOT fake activity data.
- `cards/` — 11 already generated, animated, self-contained SVGs (hero, 3 tiles, stats, contribution graph, 5 featured repo cards).
- `CLAUDE_CODE_SAFE_INTEGRATION_PROMPT.md` — detailed integration prompt for Claude Code.

**Important:** This package deliberately contains NO `README.md` so that extracting it into your profile repository cannot overwrite your current README.

## 1. Before doing anything

Confirm that your GitHub profile repository is named exactly:

`https://github.com/msohaiilkz/msohaiilkz`

GitHub displays a profile README from a public repository named exactly like your username.

Back up the repo / create a separate branch before applying changes:

```bash
git switch -c feat/animated-profile-cards
# Keep all current uncommitted changes safe; do not reset or force-push.
```

**Website issue discovered:** `https://portfolio.netlify.app` currently resolves to **Ryan Unruh**, not Muhammad Sohail. This kit does NOT copy its style or link to it in the new tiles. Your original README is preserved exactly, including this old link; review it separately. The other URL `https://msohailkz.github.io` could not be verified. Update the correct portfolio URL only after checking it yourself.

## 2. Install into the local profile repository

Extract this ZIP into a **temporary folder first**. Copy these files/folders into the root of your actual `msohaiilkz/msohaiilkz` repo:

- `config.json`
- `scripts/`
- `data/`
- `cards/`
- `.github/workflows/refresh-profile-cards.yml` **only if there is no conflicting existing workflow**
- `tests/` (optional)

Review every existing destination before copying. Do not overwrite any file already in your repo without checking its diff. If you already have a scheduled contributions workflow, merge the new fetch/render/validate/commit steps into that workflow instead of running two competing schedules.

## 3. Install font subsetting dependency

Requires Python 3.10+, `pyftsubset`, and a local font (Fira Code preferred, with Inter/DejaVu fallbacks):

```bash
python -m pip install 'fonttools[woff]>=4.55,<5'
```

The GitHub Action installs `fonts-firacode` and `fonttools[woff]` automatically. No font files are bundled or uploaded separately. The generator embeds only subsetted WOFF data inside each SVG.

## 4. Preview WITHOUT editing README

From the profile repo root:

```bash
python scripts/render_cards.py
python scripts/validate_cards.py
python scripts/patch_readme.py
```

This writes `README.preview.md` for review. Your existing `README.md` remains unchanged.

For a screenshot with **every animation disabled**:

```bash
STATIC=1 python scripts/render_cards.py
python scripts/validate_cards.py
```

On Windows PowerShell:

```powershell
$env:STATIC='1'
python scripts/render_cards.py
Remove-Item Env:STATIC
```

**IMPORTANT:** Before committing the cards, run `python scripts/render_cards.py` again WITHOUT `STATIC=1` to restore the animated version.

## 5. Only when you approve the README preview

```bash
python scripts/patch_readme.py --apply
```

This writes a timestamped `README.backup-YYYYMMDD-HHMMSS.md` and inserts an animated section at the top of `README.md`. Your original README text, all 15 project descriptions, links, badges, and other sections remain below the new cards.

Review changes:

```bash
git diff -- README.md
git status --short
```

No code here automatically commits or pushes the README. Do that yourself after reviewing the diff.

## 6. Daily real contribution data

The workflow runs once per day (02:17 UTC) and can also be started manually from **Actions > Refresh animated profile cards > Run workflow**. It:

1. Uses the repository's standard `GITHUB_TOKEN` (never hardcoded).
2. Fetches the public contribution calendar through GitHub GraphQL and public repo metadata through REST.
3. Saves only validated data to `data/contributions.json` using an atomic replace.
4. Generates SVG cards, validates them, then commits only the generated cards and contribution JSON.

The first preview intentionally says **Awaiting verified GitHub data**. Once the first authenticated Action succeeds, it displays actual contributions, current streak, active days, busiest day, monthly bars and the contribution heatmap.

GitHub Actions must be allowed to write repository contents. Organization rules, branch protection or disabled scheduled workflows can prevent automated pushes. If so, use a PR-based workflow or allow the repository's standard Actions write permissions.

## 7. Motion, SVG and GitHub limitations

- CSS keyframes and a small SMIL decorative pulse are embedded in the SVG. All visible animation is disabled under `prefers-reduced-motion: reduce`. `STATIC=1` omits SMIL and disables CSS animation for screenshots.
- SVGs contain no JavaScript, no `foreignObject`, no external fonts and no remote image dependencies.
- GitHub's SVG image proxy, some browsers and accessibility settings may render SVG animations or embedded fonts differently. Cards remain legible as static graphics.
- An optional portrait is supported by `portrait_path` in `config.json`; it must be a local PNG/JPEG/WebP smaller than 1 MB. Do not upload private photos unintentionally.
- Public GitHub GraphQL data may not include private contribution details. No private activity is inferred.
- Only five source-code repositories explicitly linked in your supplied README are converted into repository cards. Your **other projects are preserved in the original README**, not silently removed.

## 8. Safety and confidentiality

No production credentials, source code from private repos, internal healthcare data, patient records or API keys are included. All profile information is public-facing and derived from the README you supplied. The original profile README was supplied as chat text; live GitHub access was not available during creation.

No files have been pushed to GitHub.
