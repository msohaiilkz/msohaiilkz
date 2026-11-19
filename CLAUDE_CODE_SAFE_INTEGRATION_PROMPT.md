# Claude Code — Safe GitHub Profile README SVG Redesign Integration

You are operating in my local GitHub profile repository, expected owner/repo `msohaiilkz/msohaiilkz`. I have supplied an Animated GitHub README Kit containing `config.json`, `scripts/`, `cards/`, `data/` and a GitHub Actions workflow.

## Non-negotiable safety instructions

1. **Read-only audit FIRST.** Inspect `README.md`, all `.github/workflows/*.yml`, existing scripts, current `git status`, branches, any pending changes, and my actual portfolio website from the correct URL in my current repo. Do not assume `portfolio.netlify.app` is mine: that URL was found to show another developer's website.
2. **Do not delete, overwrite, rename or truncate** any existing README sections, project links, images, badges, contributions widgets, workflow or source files. Preserve all my 15+ project references and recent information.
3. **Do not run `git reset`, `git clean`, `git checkout --`, force push, merge, rebase or push.** Do not commit anything until I explicitly approve the reviewed diff. Never expose tokens or credentials.
4. Determine whether I already have a contribution-data workflow. If yes, extend it safely instead of introducing a conflicting daily schedule.
5. Work on a new branch only after confirming there are no uncommitted changes at risk. If dirty, stop and ask.
6. Verify the correct GitHub username and profile repo, and check each supplied repo/demo/contact link. Never substitute someone else's profile or portfolio.
7. Keep the existing brand palette from my supplied README: dark `#0d1117`, cyan `#00D9FF`, blue `#0077FF`, with Fira Code-inspired typography; refine it only after comparing with my real portfolio.
8. No fabricated GitHub stats or contribution history. If API data is missing, show an explicit pending state.

## Required outcome

- A visually polished stack of native SVG cards rendered by `scripts/render_cards.py`: hero (name, one-line role/tagline, optional portrait), three clickable 32.5%-width tiles, monthly contribution bar chart and streak/active/busiest stats, one card per configured featured public repo, and cyan/blue contribution heatmap.
- All SVGs are self-contained, embedded subset WOFF fonts via `pyftsubset`, CSS keyframes and decorative SMIL, no JS or foreignObject, `prefers-reduced-motion` support and `STATIC=1` final-frame mode.
- A scheduled GitHub Action that refreshes `data/contributions.json` from GitHub APIs daily, runs generator, validates output and stages/commits **only** generated cards and JSON (when enabled). Preserve any existing workflow.
- An idempotent, reversible README modification using `scripts/patch_readme.py`: preview first, then after my approval, add only the marked card block at the top while retaining the entire original README below. Back up README before applying.
- Run `python scripts/validate_cards.py`, `python tests/test_readme_patch.py`, a STATIC=1 preview and a normal animated build. Inspect rendered images for clipping, text overflow, contrast, link accuracy, and reduced motion.

## Your response BEFORE editing

Provide: (a) existing README inventory, (b) existing workflows and conflicts, (c) correct verified website branding, (d) exact proposed file changes, (e) safety risks, (f) expected before/after layout. **Wait for my explicit approval before modifying the repo.** After approved edits, show a diff and ask separately before any commit or push.
