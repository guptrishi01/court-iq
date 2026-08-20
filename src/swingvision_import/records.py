"""The JSON-serializable staging schema for a single match.

A MatchRecord is the artifact that gets hand-reviewed before anything reaches
SQL: transform.py builds one from a SwingVision export, review.py saves/loads
it as JSON, and load.py refuses to write it to the database until every
PointRecord.needs_review flag is cleared.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class PointRecord:
    """A single point within the staged, JSON-serializable match schema.

    Attributes:
        game_number: 1-based game number within the set.
        point_number: 1-based point number within the game.
        is_serving: Whether the tracked player was serving this point.
        point_won: Whether the tracked player won this point.
        point_end_type: Canonical point-outcome type (e.g. "ace",
            "unforced_error") — one of the values allowed by the point
            table's CHECK constraint.
        first_serve_in: Whether the first serve landed in, if known.
        second_serve_in: Whether the second serve landed in, if known.
        net_approach: Whether the tracked player approached the net this
            point. SwingVision reports nothing for this; it stays False
            until filled in by hand during review.
        net_point_won: Whether a net approach won the point, if
            net_approach is True.
        is_tiebreak_game: Whether this point was played in a tiebreak game.
        needs_review: True when point_end_type came from one of
            SwingVision's less reliable AI-guessed categories (see
            config.NEEDS_REVIEW_END_TYPES) or from reconstruct.py's
            Shots-based heuristic (which flags every point it produces,
            not just the ambiguous ones), and hasn't been confirmed by
            hand yet. finalize_and_load refuses to write a match while this
            is True on any of its points.
        notes: Free-text notes for this point.
        ai_suggested_point_end_type: A Claude-suggested refinement of
            point_end_type, from review_assist.py — set only when the user
            has explicitly run that (opt-in, costs an API call) step.
            Never clears needs_review by itself: per the user's explicit
            rule, a Claude suggestion is one more thing to confirm, not a
            second silent auto-tagger.
        ai_suggestion_reasoning: The reasoning Claude gave for that
            suggestion, shown alongside it during review.
        source_point_number: The original SwingVision match-wide "Point"
            number this was reconstructed from (see reconstruct.py), or
            None for a point that came from a direct Points-sheet parse.
            Lets pipeline.suggest() re-fetch this point's raw shots from
            the source export without re-deriving the mapping.
    """

    game_number: int
    point_number: int
    is_serving: bool
    point_won: bool
    point_end_type: str
    first_serve_in: bool | None = None
    second_serve_in: bool | None = None
    net_approach: bool = False
    net_point_won: bool | None = None
    is_tiebreak_game: bool = False
    needs_review: bool = False
    notes: str | None = None
    ai_suggested_point_end_type: str | None = None
    ai_suggestion_reasoning: str | None = None
    source_point_number: int | None = None


@dataclass
class SetRecord:
    """A single set within the staged, JSON-serializable match schema.

    Attributes:
        set_number: 1-based set number within the match.
        games_won: Games won by the tracked player in this set.
        games_lost: Games lost by the tracked player in this set.
        is_tiebreak_set: Whether this set was decided by a tiebreak.
        points: All points played in this set, in play order.
    """

    set_number: int
    games_won: int
    games_lost: int
    is_tiebreak_set: bool = False
    points: list[PointRecord] = field(default_factory=list)


@dataclass
class MatchRecord:
    """The staged, JSON-serializable representation of one full match.

    This is the artifact that gets hand-reviewed before anything reaches
    SQL: transform.py builds one from a SwingVision export, review.py
    saves/loads it as JSON, and load.py refuses to write it to the database
    until every PointRecord.needs_review flag is cleared.

    Attributes:
        date: ISO-format date of the match.
        opponent: Opponent's name.
        result: Match result, "W" or "L".
        match_type: "competitive" or "practice".
        location: Where the match was played, if known.
        energy_rating: Self-reported energy rating (1-5), if provided.
        mental_rating: Self-reported mental rating (1-5), if provided.
        pros: Self-reported "what went well" notes.
        cons: Self-reported "what needs work" notes.
        notes: Free-text notes for the match.
        source_file: Path to the SwingVision export this record was built
            from, for traceability during review.
        sets: All sets played in this match, in play order.
    """

    date: str
    opponent: str
    result: str
    match_type: str = "competitive"
    location: str | None = None
    energy_rating: int | None = None
    mental_rating: int | None = None
    pros: str | None = None
    cons: str | None = None
    notes: str | None = None
    source_file: str | None = None
    sets: list[SetRecord] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Converts this record to a plain, JSON-serializable dict.

        Returns:
            A nested dict representation suitable for json.dumps.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "MatchRecord":
        """Rebuilds a MatchRecord from a dict produced by to_dict.

        Tolerates a dict missing optional keys (e.g. a user hand-trimmed
        the pending JSON while resolving a review flag) by falling back to
        each dataclass field's default.

        Args:
            data: A dict shaped like the output of to_dict, with a "sets"
                key containing a list of set dicts, each with a "points"
                key containing a list of point dicts.

        Returns:
            The reconstructed MatchRecord.
        """
        sets = []
        for raw_set in data.get("sets", []):
            points = [PointRecord(**p) for p in raw_set.get("points", [])]
            set_kwargs = {k: v for k, v in raw_set.items() if k != "points"}
            sets.append(SetRecord(points=points, **set_kwargs))
        match_kwargs = {k: v for k, v in data.items() if k != "sets"}
        return cls(sets=sets, **match_kwargs)
