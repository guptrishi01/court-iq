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

## Testing

**Backend:** pytest for unit tests. Run with coverage (`pytest --cov`) — treat coverage gaps as a signal to look for untested *or redundant* paths, not just a number to push up. Run via `pytest --cov=swingvision_import --cov-report=term-missing` from the repo root (config in `pyproject.toml` puts `src` on `sys.path` and points `testpaths` at `tests/`, which mirrors the `src` package layout — e.g. `tests/swingvision_import/` for `src/swingvision_import/`).

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

Backend: SQL database (SQLite) for storage, Python for stat aggregation and the SwingVision import pipeline. Frontend stack is still TBD.

- **Dataclass-based configuration** — config objects (AI prompt settings, SwingVision import settings, stat-calc parameters) as `@dataclass`, not raw dicts.
- **Pipeline classes with incremental state tracking** — SwingVision import and AI context-building should be structured as pipeline classes that track what's already been processed (e.g. which points/matches have already been imported), so re-running doesn't reprocess or duplicate data.
- **Per-module logging** — `logging.getLogger(__name__)` per module, not a shared root logger.
- **Docstrings** — every module, class, and function gets a Google-style docstring (`Args:` / `Returns:`, plus `Raises:` and `Attributes:` where relevant). This is initial architecture and will keep shifting, so the docstrings are how the *current* contract of each piece stays legible as things move, not a one-time formality.
- **Ruff**: rules `E, F, I, W`, 100-char line limit.

**Given a second look, not adopted for now** (flagged here rather than silently dropped, in case a future feature changes this):

- **Sparse matrix handling** — Court IQ's data is small and dense (per-point flags, per-match stats), not high-dimensional/sparse. No current feature needs it; revisit only if something like large-scale cross-match feature vectors gets built.
- **Parallel processing via `ThreadPoolExecutor`** — data volume is small (one user, one match at a time), so day-to-day backend work doesn't need it. The one plausible fit is firing the AI coach's strategy/drills/fitness generations concurrently instead of sequentially — worth doing there specifically, not as a blanket convention everywhere.