"""Dataclasses mirroring SwingVision's raw exported rows, pre-transformation.

Only the sheets that map onto Court IQ's match/set/point schema are modeled
here (Sets, Games, Points) — SwingVision's Shots/Settings sheets carry
shot-level detail (speed, spin, placement) that nothing in the current schema
stores yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RawSetRow:
    """One row from SwingVision's "Sets" sheet, before transformation.

    Attributes:
        set_number: 1-based set number within the match.
        winner: Raw winner label from the export (e.g. "player" or
            "opponent"), not yet normalized.
        games_won: Games won by the tracked player in this set.
        games_lost: Games lost by the tracked player in this set.
    """

    set_number: int
    winner: str
    games_won: int
    games_lost: int


@dataclass
class RawGameRow:
    """One row from SwingVision's "Games" sheet, before transformation.

    Attributes:
        set_number: 1-based set number this game belongs to.
        game_number: 1-based game number within the set.
        server: Raw server label from the export, not yet normalized.
        winner: Raw game-winner label from the export, not yet normalized.
    """

    set_number: int
    game_number: int
    server: str
    winner: str


@dataclass
class RawPointRow:
    """One row from SwingVision's "Points" sheet, before transformation.

    Attributes:
        set_number: 1-based set number this point belongs to.
        game_number: 1-based game number within the set.
        point_number: 1-based point number within the game.
        server: Raw server label from the export, not yet normalized.
        winner: Raw point-winner label from the export, not yet normalized.
        end_type: Raw point-outcome label from the export (e.g. "ace",
            "winner"), not yet mapped onto Court IQ's canonical set.
        first_serve_in: Whether the first serve landed in, or None if the
            export didn't report it for this point.
        second_serve_in: Whether the second serve landed in, or None if
            there was no second serve or it wasn't reported.
    """

    set_number: int
    game_number: int
    point_number: int
    server: str
    winner: str
    end_type: str
    first_serve_in: bool | None = None
    second_serve_in: bool | None = None


@dataclass
class RawMatchExport:
    """The full set of raw rows parsed from one SwingVision .xlsx export.

    Attributes:
        sets: All rows from the "Sets" sheet.
        games: All rows from the "Games" sheet.
        points: All rows from the "Points" sheet.
    """

    sets: list[RawSetRow] = field(default_factory=list)
    games: list[RawGameRow] = field(default_factory=list)
    points: list[RawPointRow] = field(default_factory=list)
