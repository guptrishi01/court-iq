# Stat Definitions

How each statistic is defined and calculated from raw point data.

## Serving Stats

| Stat | Abbreviation | Calculation |
|---|---|---|
| First Serves Total | FST | Count of points where `is_serving = TRUE` |
| First Serves In | FSI | Count of points where `is_serving = TRUE AND first_serve_in = TRUE` |
| First Serve Percentage | FS% | `FSI / FST * 100` |
| Second Serves Total | SST | Count of points where `is_serving = TRUE AND first_serve_in = FALSE` |
| Second Serves In | SSI | Count of points where `is_serving = TRUE AND first_serve_in = FALSE AND second_serve_in = TRUE` |
| Second Serve Percentage | SS% | `SSI / SST * 100` |
| Aces | ACE | Count of points where `point_end_type = 'ace'` |
| Double Faults | DF | Count of points where `point_end_type = 'double_fault'` |
| Service Games Won | SGW | Count of games where `is_serving = TRUE` and game was won |
| Service Games Total | SGT | Count of games where `is_serving = TRUE` |
| Service Hold Percentage | SH% | `SGW / SGT * 100` |

## Receiving Stats

| Stat | Abbreviation | Calculation |
|---|---|---|
| Break Points Total | BPT | Count of points at break point score (derived from game score reconstruction) |
| Break Points Converted | BPC | Subset of BPT where `point_won = TRUE` |
| Break Point Conversion Rate | BP% | `BPC / BPT * 100` |
| Return Games Won | RGW | Count of games where `is_serving = FALSE` and game was won |
| Return Games Total | RGT | Count of games where `is_serving = FALSE` |
| Return Win Percentage | RW% | `RGW / RGT * 100` |

## Point Outcome Stats

| Stat | Abbreviation | Calculation |
|---|---|---|
| Total Points Played | TPP | Count of all points |
| Total Points Won | TPW | Count of points where `point_won = TRUE` |
| Points Won Percentage | PW% | `TPW / TPP * 100` |
| Winners | W | Count of points where `point_end_type = 'winner'` |
| Unforced Errors | UE | Count of points where `point_end_type = 'unforced_error'` |
| Forced Errors | FE | Count of points where `point_end_type = 'forced_error'` |
| Return Winners | RW | Count of points where `point_end_type = 'return_winner'` |
| Return Errors | RE | Count of points where `point_end_type = 'return_error'` |
| Winner to UE Ratio | W/UE | `W / UE` (above 1.0 is good) |

## Net Stats

| Stat | Abbreviation | Calculation |
|---|---|---|
| Net Approaches | NA | Count of points where `net_approach = TRUE` |
| Net Points Won | NPW | Count of points where `net_approach = TRUE AND net_point_won = TRUE` |
| Net Success Rate | NS% | `NPW / NA * 100` |

## Clutch Stats

| Stat | Abbreviation | Calculation |
|---|---|---|
| Deuce Points Played | DPP | Count of points played at 40-40 (derived from game score reconstruction) |
| Deuces Converted | DC | Subset of DPP that led to winning the game |
| Deuce Conversion Rate | DC% | `DC / DPP * 100` |

## Self-Assessment

| Stat | Scale | Description |
|---|---|---|
| Energy Rating | 1-5 | Physical energy level during the match |
| Mental Rating | 1-5 | Mental focus and composure during the match |

## Scope

All stats can be computed at three levels:

- **Match level** — aggregated across all sets
- **Set level** — filtered to a specific set
- **Game level** — filtered to a specific game within a set
