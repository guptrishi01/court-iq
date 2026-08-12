"""JSON-serializable dataclasses for the AI coach's output.

CoachingReport is the artifact saved to ai/reports/<match_id>.json. Unlike
swingvision_import's MatchRecord, there's no review gate here — a report is
complete the moment it's generated.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

Category = Literal["strategy", "drill", "fitness"]
Priority = Literal["high", "medium", "low"]

_PRIORITY_ORDER: dict[str, int] = {"high": 0, "medium": 1, "low": 2}


@dataclass(frozen=True)
class SupportingStat:
    """A stat that grounds a coaching item in this match's actual numbers.

    This is what makes "specific to this match's stats, not generic
    boilerplate" (the UAT checklist item in CLAUDE.md) something a test can
    assert on, rather than eyeballing prose.

    Attributes:
        stat: The stat's name/abbreviation (e.g. "BP%"), matching
            docs/stat-definitions.md.
        value: The stat's value for this match.
        comparison_label: What it's being compared to, if anything (e.g.
            "your season average").
        comparison_value: The comparison value, if comparison_label is set.
    """

    stat: str
    value: float
    comparison_label: str | None = None
    comparison_value: float | None = None


@dataclass(frozen=True)
class CoachingItem:
    """One coaching insight.

    Attributes:
        category: Which specialist produced this item.
        observation: The pattern in the data that prompted this item.
        recommendation: The actionable advice.
        supporting_stat: The stat that grounds this item in this match.
        priority: Impact ranking, used to build the derived improvement plan.
    """

    category: Category
    observation: str
    recommendation: str
    supporting_stat: SupportingStat
    priority: Priority


@dataclass(frozen=True)
class DrillItem(CoachingItem):
    """A coaching item plus a concrete practice drill.

    Attributes:
        drill_name: Short name for the drill.
        frequency: How often/long to run it (e.g. "15 min, 3x/week").
    """

    drill_name: str
    frequency: str


@dataclass(frozen=True)
class FitnessItem(CoachingItem):
    """A coaching item plus a physical/mental conditioning focus.

    Attributes:
        focus_area: The conditioning theme (e.g. "endurance", "recovery",
            "composure under pressure").
    """

    focus_area: str


def _item_to_dict(item: CoachingItem) -> dict:
    """Converts a single coaching item to a plain dict.

    Args:
        item: A CoachingItem, DrillItem, or FitnessItem.

    Returns:
        Its dict representation, suitable for json.dumps.
    """
    return asdict(item)


@dataclass
class CoachingReport:
    """The full AI-generated coaching output for one match.

    Attributes:
        match_id: The match this report is for.
        generated_at: ISO-format timestamp of generation.
        model: The Claude model id used to generate this report.
        strategy: Strategy insights.
        drills: Drill recommendations.
        fitness: Fitness/conditioning recommendations.
    """

    match_id: int
    generated_at: str
    model: str
    strategy: list[CoachingItem] = field(default_factory=list)
    drills: list[DrillItem] = field(default_factory=list)
    fitness: list[FitnessItem] = field(default_factory=list)

    @property
    def improvement_plan(self) -> list[CoachingItem]:
        """All items across every category, sorted by priority (high first).

        This is a derived view, not a separately generated category — see
        CLAUDE.md: there is deliberately no 4th "synthesis" LLM call, so
        this can never drift out of sync with strategy/drills/fitness.

        Returns:
            All items from strategy, drills, and fitness combined, sorted
            by priority.
        """
        all_items: list[CoachingItem] = [*self.strategy, *self.drills, *self.fitness]
        return sorted(all_items, key=lambda item: _PRIORITY_ORDER[item.priority])

    def to_dict(self) -> dict:
        """Converts this report to a plain, JSON-serializable dict.

        Returns:
            A nested dict representation suitable for json.dumps. The
            derived improvement_plan is not included — recompute it from
            strategy/drills/fitness after loading.
        """
        return {
            "match_id": self.match_id,
            "generated_at": self.generated_at,
            "model": self.model,
            "strategy": [_item_to_dict(item) for item in self.strategy],
            "drills": [_item_to_dict(item) for item in self.drills],
            "fitness": [_item_to_dict(item) for item in self.fitness],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CoachingReport":
        """Rebuilds a CoachingReport from a dict produced by to_dict.

        Args:
            data: A dict shaped like the output of to_dict.

        Returns:
            The reconstructed CoachingReport.
        """

        def _rebuild(item_cls: type, raw: dict) -> CoachingItem:
            kwargs = {**raw, "supporting_stat": SupportingStat(**raw["supporting_stat"])}
            return item_cls(**kwargs)

        return cls(
            match_id=data["match_id"],
            generated_at=data["generated_at"],
            model=data["model"],
            strategy=[_rebuild(CoachingItem, raw) for raw in data.get("strategy", [])],
            drills=[_rebuild(DrillItem, raw) for raw in data.get("drills", [])],
            fitness=[_rebuild(FitnessItem, raw) for raw in data.get("fitness", [])],
        )
