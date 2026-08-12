# Court IQ — AI Tennis Coach 🎾

An AI-powered tennis coaching tool that analyzes your match data to help you improve. Log point-by-point statistics from recorded match footage, reflect on what went right and wrong, and let generative AI turn that data into actionable coaching — strategies to implement, weaknesses to address, and exercises to improve your game.

## Overview

The goal of Court IQ is simple: **use AI to become a better tennis player.**

After each match, you review your recorded footage, log detailed point-by-point data, and write down your pros (what went well) and cons (what needs work). Court IQ feeds all of this — your raw statistics and your own self-assessment — into a generative AI coach that provides:

- **Strategic recommendations** — What tactical adjustments to make based on patterns in your data (e.g. "your first serve win % drops in third sets — conserve energy on second serve points early")
- **Improvement plans** — Specific areas to focus on in practice, prioritized by impact on your results
- **Drills and exercises** — Targeted practice routines and physical conditioning tied directly to your identified weaknesses

The AI coaching gets smarter over time as you log more matches — it can spot trends across your history that you might not notice yourself.

### How It Works

1. **Record** your match using [SwingVision](https://swing.vision/) on a phone fence mount — get verbal consent from the other player first, since the camera captures both sides of the court
2. **Review** the SwingVision footage: confirm or correct its auto-scored point outcomes (its winner/unforced-error/forced-error calls are the least reliable part) and tag anything it doesn't capture at all, like net approaches
3. **Import** the reviewed match — it's staged as JSON first, and only written to the database once every point is confirmed (unresolved points block the whole match, not just themselves)
4. **Reflect** by writing your pros and cons for the match
5. **Get coached** — Court IQ generates a self-contained HTML report combining your derived stats with AI-generated strategy, drills, and fitness recommendations, viewable by just opening the file

## Features

- **AI Coach** — Three parallel Claude Sonnet 5 calls (strategy, drills, fitness) analyze your derived statistics and self-reported pros/cons to deliver recommendations grounded in that match's actual numbers, not generic advice
- **SwingVision Import** — Matches are recorded via SwingVision and loaded through a staged review pipeline that catches unreliable AI classifications before anything reaches the database
- **Derived Statistics** — All stats (first serve %, break point conversion, winner/UE ratio, hold %, etc.) are computed from raw point data via `src/stats/`, including game-score reconstruction for break/deuce points
- **Match Reports** — A self-contained HTML report per match (stat breakdown + AI coaching), plus a cross-match trend report (serve %, W/UE ratio, break points, win/loss record) — hand-rolled, interactive SVG charts, no server required to view
- **Match History Trends** — The cross-match report visualizes patterns across your logged matches, not just the most recent one

## Tech Stack

- **Database:** SQLite (`data/schema.sql`) — three normalized tables, no redundant storage of derived stats
- **Backend:** Python — SwingVision import pipeline (`src/swingvision_import/`), derived-stat aggregation (`src/stats/`), and an AI coaching engine (`ai/`, using Claude Sonnet 5 via the `anthropic` SDK)
- **Reports:** `reports/` — Jinja2-rendered static HTML with hand-rolled inline SVG+CSS+JS charts (no charting library, no matplotlib). This is the current "frontend": one file per match, no server needed to view it
- **Testing:** pytest, 100% statement coverage across all four Python packages; ruff (`E, F, I, W`)

## Database Schema

The database uses three normalized tables:

- **`match`** — Match metadata (date, opponent, result, pros/cons, energy/mental ratings)
- **`set`** — Set-level data linked to a match (set number, score)
- **`point`** — Individual point data linked to a set (serve data, point outcome, net approaches)

All aggregate statistics are derived from the `point` table through queries rather than stored redundantly. See [`data/schema.sql`](data/schema.sql) for the full schema with example queries.

## Project Structure

```
court-iq/
├── README.md
├── CLAUDE.md
├── .gitignore
├── requirements.txt / requirements-dev.txt
├── pyproject.toml               # pytest, coverage, ruff config
├── data/
│   └── schema.sql               # SQL table definitions and example queries
├── docs/
│   └── stat-definitions.md      # What each stat means and how it's calculated
├── src/
│   ├── swingvision_import/      # SwingVision export -> staged JSON -> SQL pipeline
│   └── stats/                   # Derived-stat aggregation, reads data/schema.sql
├── ai/                          # AI coaching engine — context building, 3 parallel
│                                 # Claude Sonnet 5 calls (strategy/drills/fitness)
├── reports/                     # Static HTML report generation + hand-rolled SVG charts
├── frontend/                    # Match logging form UI (TBD — reports/ is the
│                                 # viewing side; nothing yet handles data entry
│                                 # besides the SwingVision pipeline)
└── tests/                       # pytest suite, mirrors each package 1:1
    ├── swingvision_import/
    ├── stats/
    ├── ai/
    └── reports/
```

## Roadmap

- [x] Define trackable statistics
- [x] Design database schema
- [x] Choose tech stack (SQLite + Python; static HTML reports as the initial "frontend" — see Tech Stack)
- [x] Build SwingVision import pipeline (staged JSON review gate before anything reaches SQL)
- [x] Build derived-stat aggregation
- [x] Integrate AI coaching engine (strategy, drills, fitness from stats + pros/cons)
- [x] Generate static HTML match reports (stats + AI coaching, hand-rolled charts)
- [x] AI trend analysis across match history (cross-match trend report)
- [ ] Build match logging form UI (or some other path to get match metadata in beyond SwingVision + hand-editing the staged JSON)
- [ ] Deploy / distribute generated reports

## Version History

- **1.0.0** (2026-08-12) — Initial architecture: SwingVision import pipeline (staged-JSON review gate), derived-stat aggregation, AI coaching engine (Claude Sonnet 5, 3 parallel specialists), and static HTML report generation with hand-rolled SVG charts. 105 tests, 100% statement coverage.

## License

MIT
