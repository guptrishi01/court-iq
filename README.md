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

1. **Record** your match using a phone mount on the court fence
2. **Review** the footage after the match
3. **Log** point-by-point data through the web interface (who served, first serve in/out, how the point ended, etc.)
4. **Reflect** by writing your 3 pros and 3 cons for the match
5. **Get coached** — AI reads your stats and reflections to deliver personalized insights

## Features

- **AI Coach** — Generative AI analyzes your statistics and self-reported pros/cons to deliver personalized strategy, drills, and fitness recommendations
- **Point-by-Point Logging** — Sequential data entry that mirrors watching your footage: add games one at a time within each set
- **Derived Statistics** — All stats (first serve %, break point conversion, winner/UE ratio, hold %, etc.) are computed from raw point data
- **Performance Dashboard** — Visualize trends across matches with charts and graphs
- **Match History** — Browse past matches with full stat breakdowns

## Tech Stack

> **Note:** Tech stack decisions are in progress. This section will be updated as the project develops.

## Database Schema

The database uses three normalized tables:

- **`match`** — Match metadata (date, opponent, result, pros/cons, energy/mental ratings)
- **`set`** — Set-level data linked to a match (set number, score)
- **`point`** — Individual point data linked to a set (serve data, point outcome, net approaches)

All aggregate statistics are derived from the `point` table through queries rather than stored redundantly. See [`database/schema.sql`](database/schema.sql) for the full schema with example queries.

## Project Structure

```
court-iq/
├── README.md
├── .gitignore
├── database/
│   └── schema.sql              # SQL table definitions and example queries
├── docs/
│   └── stat-definitions.md     # What each stat means and how it's calculated
├── frontend/                   # Match logging form + stats dashboard (TBD)
├── backend/                    # API server + database layer (TBD)
└── ai/                         # AI coaching engine — prompt design, context
                                # building, insight generation (TBD)
```

## Roadmap

- [x] Define trackable statistics
- [x] Design database schema
- [ ] Choose tech stack (frontend framework, backend, database)
- [ ] Build match logging form UI
- [ ] Implement backend API
- [ ] Build statistics dashboard
- [ ] Integrate AI coaching engine (strategy, drills, fitness from stats + pros/cons)
- [ ] AI trend analysis across match history
- [ ] Deploy

## License

MIT
