# CLAUDE.md

Project-specific context for Court IQ. See [README.md](README.md) for the product overview and [docs/stat-definitions.md](docs/stat-definitions.md) for stat calculations.

## Data capture: SwingVision

Match and practice footage is recorded with the [SwingVision](https://swing.vision/) app via a phone fence mount, not logged manually from scratch. Its AI auto-tracks serves, point outcomes, rally length, shot speed, and placement, and stats are pulled from its export rather than re-derived from raw video.

**Consent:** verbal consent from the other player is required before recording any rally practice or match, since the camera captures both sides of the court.

**Manual review is required before trusting SwingVision data — do not treat its auto-tags as ground truth:**

- **Winner / unforced error / forced error classification** — SwingVision auto-tags this per point, but it is the least reliable category (this is why the app has an "Edit Point" correction feature). Close calls and doubles shot attribution are especially unreliable. Any pipeline or import code that ingests this classification must surface it for the user's own inspection/verification rather than silently persisting it as final.
- **Net approach outcomes (NA / NPW / NS%)** — SwingVision does not capture a discrete per-point "approached net" flag at all. This is fully manual: it must be tagged by the user while reviewing footage, not inferred from SwingVision's export.
- Everything else in `stat-definitions.md` (serve in/out, aces, double faults, service/return games, break points, deuce points, rally/shot data) maps cleanly to SwingVision's automatic tracking and does not need manual re-verification beyond spot checks.
- Energy Rating, Mental Rating, and pros/cons are self-assessment by design — always manual, unrelated to SwingVision.

There is no dedicated wall/backboard session mode in SwingVision (only Match, Rally, Service Practice, Ball Machine Mode for tennis). Wall-practice tracking is unverified — don't assume its stats are trustworthy without checking against a manual count first.

## Database schema

`data/schema.sql` defines the `match` / `set` / `point` tables (SQLite). This is now finalized — no new columns were added for SwingVision's review-flag tracking; that lives entirely in the pre-SQL JSON staging step described below, not in the database.

## SwingVision import pipeline

`src/swingvision_import/` turns a SwingVision `.xlsx` export into rows in `data/schema.sql`, in two deliberately separate steps — never one:

1. **`pipeline.ingest(xlsx_path, ...)`** — parses the export and writes a staging JSON file to `src/swingvision_import/pending/` (gitignored — personal match data, not code). Never touches SQL.
2. **`pipeline.finalize(json_path)`** — loads that JSON and writes the match + its sets + all its points into SQLite in one atomic transaction.

**The hard rule finalize() enforces:** a match is not written to SQL — at all, not partially — while any `PointRecord.needs_review` flag is still `True`. `load.finalize_and_load` raises `UnresolvedReviewError` and writes nothing if so. Resolve flags by hand-editing the pending JSON (or building a review UI that does the same) before calling `finalize()` again. This is the concrete implementation of the "manual review is required" rule above — code enforces it, not just documentation.

**SwingVision's export format is unverified.** There's no public API or published schema, so `config.DEFAULT_COLUMN_ALIASES` (in `src/swingvision_import/config.py`) is a best guess from secondhand reporting (shot placement, serve state, per-point winner labels), and `tests/swingvision_import/conftest.py`'s `synthetic_xlsx` fixture is a hand-built stand-in, not a real export. Once a real exported match is available: fix the column aliases in `config.py` first — the parsing logic in `parse.py` is written to be alias-driven specifically so this doesn't require a rewrite. Only fall back to changing `parse.py`/`raw.py` if the actual sheet *structure* (not just header names) turns out to differ from what's assumed (three sheets: Sets, Games, Points).

## Derived stats

`src/stats/` computes everything in `docs/stat-definitions.md` by reading `data/schema.sql` back out — nothing derived is stored redundantly, matching the schema's own design intent.

- **`queries.py`** has one function per stat category (`serving_stats`, `receiving_stats`, `point_outcome_stats`, `net_stats`, `clutch_stats`), each taking `(conn, match_id, set_id=None)` — `set_id=None` aggregates the whole match, a given `set_id` scopes to one set. `match_stats(conn, match_id)` assembles the full `MatchStats` bundle used by both the AI coach and the HTML report. Game-level scope (the third tier in `stat-definitions.md`) isn't implemented yet — adding it is a parameter, not a rewrite.
- **`scoring.py`** derives break-point and deuce-point status by replaying each game's points in order under a running point tally — neither is a stored column, both are properties of where a point falls in its game's score. **Tiebreak games are excluded** from break/deuce detection entirely (a tiebreak's server rotates within the game itself, so "break point" doesn't map onto that scoring the same way) and from service/return game-holding counts (same reason — a single game-level `is_serving` value isn't well-defined for a tiebreak under this schema).
- Every percentage/ratio field returns `0.0` when its denominator is 0, never `None` or a raised error — keeps every stat field a plain `float`, renderable without `Optional`-handling downstream. This means "0%" and "no data" aren't distinguished; revisit only if that turns out to matter.
- `DC` (deuces converted) follows the same convention as `BPC` (break points converted): "point_won = TRUE" on a deuce/break point, not the stricter "and the game was won" reading `stat-definitions.md`'s wording could also support — chosen for consistency between the two, not because the wording was unambiguous.

## AI coaching engine

`ai/` (a standalone top-level package, not nested under `src/` — its own `pythonpath` entry in `pyproject.toml`) generates one `CoachingReport` per match: strategy insights, drill recommendations, and fitness/conditioning notes.

- **Three parallel, stateless Claude Sonnet 5 calls** (`generate.py`, via `ThreadPoolExecutor`) — strategy / drills / fitness — each sees the same deterministically-built `CoachContext` (`context.py`, pure data assembly from `MatchStats`, no LLM). No tool-using subagents, no 4th "synthesis" call: this is the one place in the codebase `ThreadPoolExecutor` is actually used, matching the specific carve-out named below.
- **"Improvement plan" is a derived `@property`** on `CoachingReport` (`records.py`) — every item from strategy/drills/fitness combined, sorted by `priority`. Never generated or stored separately, so it can't drift out of sync with the three specialists' actual output.
- **Every item carries a `SupportingStat`** (which stat, its value, optionally a comparison) — this is what makes "specific to this match's stats, not generic boilerplate" (the UAT checklist item below) something a test can assert on rather than eyeball.
- **The Anthropic client is always injected**, never constructed inside `ai/` itself (`client.py`'s `call_specialist`, `pipeline.py`'s `generate`) — so tests never touch the real API or spend real money. `tests/ai/conftest.py`'s `FakeAnthropicClient` is the standard fake to reuse.
- **Incremental state tracking lives on the filesystem**, same pattern as SwingVision's pending JSON: `pipeline.AICoachPipeline.generate()` skips calling the API and loads the cached report if `ai/reports/<match_id>.json` already exists, unless `force=True`. `ai/reports/` is gitignored — personal AI output, not code.
- A specialist whose response fails to parse (`SpecialistError`) contributes an empty list for its category rather than failing the whole report — logged as an error, not silently dropped.

## Report generation

`reports/` (also standalone top-level) is the one piece that consumes *both* `stats` and `ai` output and is the actual product surface for now: **one self-contained, downloadable `report.html` per match** (stats breakdown + AI coaching insights together) — there is no live web app. `render_history_report` produces a second, separate cross-match trend page from the same building blocks.

- **Charts are hand-rolled inline SVG+CSS+JS** (`charts.py`), following the `dataviz` skill's method (pick the form → assign color by its job → mark specs → hover layer) instead of a plotting library — matplotlib was explicitly ruled out (static, no real interactivity, and its default look was the thing being avoided). Every hex value in `palette.py` is lifted verbatim from the skill's validated reference palette, never re-derived or eyeballed.
- **Six chart primitives** cover the outline: `bar_chart` (sequential hue — magnitude, not identity), `stacked_bar_chart` (2-category only: serve in/out), `line_chart` (single series, per-point hover rather than a continuous crosshair — a deliberate v1 simplification), `stat_tile`, `meter`, and `status_strip` (win/loss — uses the fixed **status** palette, not categorical, since win/loss is a state). A genuine multi-series `line_chart` variant (for the combined hold%/return% trend from the original ideation) doesn't exist yet — cut for v1 rather than rushed, with no real multi-match data yet to validate it against anyway.
- **Every label is free text from the database or the AI** (opponent names, `pros`/`cons`, observation/recommendation text) — `charts.py` HTML-escapes anything going into an SVG attribute and reads it back via `.dataset`/sets it via `.textContent` in the emitted JS, never `innerHTML`. Jinja's `autoescape` is on in `render.py`; only pre-built chart fragments (already escaped internally) are marked `| safe`, never raw user or AI text. A chart's DOM id is also JSON-escaped before being spliced into its own `<script>` block, not just HTML-escaped for the attribute — the two contexts need different escaping and only satisfying one isn't enough.

## Testing

**Backend:** pytest for unit tests. Run with coverage (`pytest --cov`) — treat coverage gaps as a signal to look for untested *or redundant* paths, not just a number to push up. Run via `pytest --cov=swingvision_import --cov=stats --cov=ai --cov=reports --cov-report=term-missing` from the repo root (config in `pyproject.toml` puts `src` **and the repo root** on `sys.path` — `ai`/`reports` are top-level, `stats` is under `src/` — and points `testpaths` at `tests/`, which mirrors each package 1:1: `tests/swingvision_import/`, `tests/stats/`, `tests/ai/`, `tests/reports/`). The AI coach's tests never call the real Anthropic API — every one injects `tests/ai/conftest.py`'s `FakeAnthropicClient`.

**Frontend (UAT):** an objective checklist tied to the user-facing features in the README, not implementation details:

- [ ] Match creation captures date, opponent, result, energy/mental ratings
- [ ] Games can be logged one at a time within a set, points logged sequentially within a game
- [ ] Derived stats (FS%, BP%, W/UE ratio, etc.) recompute and display correctly once a match is fully logged
- [ ] 3 pros / 3 cons can be entered and are attached to the correct match
- [ ] AI coach output is specific to the logged match's stats + pros/cons, not generic boilerplate
- [ ] Dashboard charts reflect trends across multiple matches, not just the most recent one
- [ ] Match history lists all past matches, and opening one shows its full stat breakdown
- [ ] Data persists across a page reload / new session
- [ ] Manual-review flags (winner/UE/FE tags, net approach) surface in the UI for the user to confirm before a match's stats are treated as final

## Code conventions

Backend: SQL database (SQLite) for storage, Python for stat aggregation, the SwingVision import pipeline, the AI coach (`anthropic` SDK), and report generation (`jinja2`). Frontend stack is still TBD — for now, `reports/`'s generated HTML *is* the frontend.

- **Dataclass-based configuration** — config objects (AI prompt settings, SwingVision import settings, stat-calc parameters) as `@dataclass`, not raw dicts.
- **Pipeline classes with incremental state tracking** — SwingVision import and the AI coach are structured as pipeline classes (`SwingVisionImportPipeline`, `AICoachPipeline`) that track what's already been processed via the filesystem (an existing pending/report file means skip, not reprocess) — never reprocess or duplicate by default.
- **Per-module logging** — `logging.getLogger(__name__)` per module, not a shared root logger.
- **Docstrings** — every module, class, and function gets a Google-style docstring (`Args:` / `Returns:`, plus `Raises:` and `Attributes:` where relevant). This is initial architecture and will keep shifting, so the docstrings are how the *current* contract of each piece stays legible as things move, not a one-time formality.
- **Ruff**: rules `E, F, I, W`, 100-char line limit.
- **Parallel processing via `ThreadPoolExecutor`** — adopted in exactly the one place flagged for it: `ai/generate.py`'s three concurrent, stateless coaching-specialist calls. Not a blanket convention — day-to-day backend work (one user, one match at a time) still doesn't need it anywhere else.

**Given a second look, not adopted for now** (flagged here rather than silently dropped, in case a future feature changes this):

- **Sparse matrix handling** — Court IQ's data is small and dense (per-point flags, per-match stats), not high-dimensional/sparse. No current feature needs it; revisit only if something like large-scale cross-match feature vectors gets built.

## Versioning & README updates

After each implementation (a meaningful chunk of work — a new package, a new pipeline stage — not every small edit): ask the user whether it's a **major**, **minor**, or **patch** change (semver `major.minor.patch`), then reflect that in README's **Version History** section — bump the number and add a one-line entry naming what shipped.

Update README itself to match, not just the version line — revise whatever existing sections are now stale (Tech Stack, How It Works, Features, Project Structure, Roadmap) rather than only appending new text, since a stale claim sitting next to accurate ones is worse than no claim at all. Add a new section only when the change doesn't fit an existing one.

Current version: **1.0.0** (major — initial architecture: SwingVision import pipeline, derived-stat aggregation, AI coaching engine, static HTML report generation). Numbering starts here; there was no prior tagged version.