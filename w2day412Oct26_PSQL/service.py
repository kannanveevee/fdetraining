"""Business rules for explainable, outcome-independent encounter prioritization.

"Risk score" is worked out here in Python from a few encounter fields.
It never looks at `readmitted`, so the score can be used before the outcome is known.
The points below are learning assumptions, not clinical advice.
"""

from collections.abc import Mapping

import psycopg

import repository
from models import RiskLevel

# Scoring rules: (field, threshold, points).
# Example: ("number_inpatient", 3, 3) means "3 or more inpatient visits adds 3 points".
# Maximum possible score = 3 + 2 + 1 + 1 + 1 = 8.
RISK_RULES: tuple[tuple[str, int, int], ...] = (
    ("number_inpatient", 3, 3),
    ("number_emergency", 2, 2),
    ("number_outpatient", 3, 1),
    ("time_in_hospital", 7, 1),
    ("num_medications", 20, 1),
)


# =====================================================================
# Risk scoring
# =====================================================================

def calculate_risk_score(encounter: Mapping[str, object]) -> int:
    """Add up the points of every rule the encounter meets."""
    score = 0
    for field, threshold, points in RISK_RULES:
        # A missing (None) value counts as 0, so it never earns points.
        value = int(encounter.get(field) or 0)
        if value >= threshold:
            score += points
    return score


def risk_level_for_score(score: int) -> RiskLevel:
    """Turn a score into a level: 5+ HIGH, 3-4 MEDIUM, 0-2 LOW."""
    if score >= 5:
        return RiskLevel.HIGH
    if score >= 3:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def score_encounter(encounter: Mapping[str, object]) -> dict[str, object]:
    """Return a copy of the encounter with risk_score and risk_level added."""
    scored = dict(encounter)
    score = calculate_risk_score(encounter)
    scored["risk_score"] = score
    scored["risk_level"] = risk_level_for_score(score).value
    return scored


def rate_percent(part: int, whole: int) -> float | None:
    """part as a percentage of whole, rounded to 2 decimals. None if whole is 0."""
    if whole == 0:
        return None
    return round(part * 100 / whole, 2)


# =====================================================================
# Encounters and care queue (used by the /encounters and /care-queue routes)
# =====================================================================

def list_encounters(
    conn: psycopg.Connection, limit: int, offset: int
) -> list[dict[str, object]]:
    """One page of encounters, each with its risk score."""
    rows = repository.get_encounters(conn, limit=limit, offset=offset)
    return [score_encounter(row) for row in rows]


def get_encounter(
    conn: psycopg.Connection, encounter_id: int
) -> dict[str, object] | None:
    """One encounter with its risk score, or None if it does not exist."""
    row = repository.get_encounter(conn, encounter_id)
    if row is None:
        return None
    return score_encounter(row)


def list_care_queue(
    conn: psycopg.Connection,
    *,
    min_risk_score: int = 3,
    risk_level: RiskLevel | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, object]]:
    """Encounters that need attention, highest risk first.

    Keeps only encounters with risk_score >= min_risk_score and, if risk_level
    is given, only that level. limit/offset then pick one page of the result.
    """
    queue = []
    for row in repository.get_care_queue(conn):
        scored = score_encounter(row)
        if scored["risk_score"] < min_risk_score:
            continue
        if risk_level is not None and scored["risk_level"] != risk_level.value:
            continue
        queue.append(scored)

    # Highest score first. Python's sort keeps the original (encounter_id) order for ties.
    queue.sort(key=lambda row: int(row["risk_score"]), reverse=True)
    return queue[offset : offset + limit]


def update_intervention(
    conn: psycopg.Connection,
    encounter_id: int,
    changes: Mapping[str, object],
) -> dict[str, object] | None:
    """Create or update an intervention. None means the encounter does not exist."""
    return repository.update_intervention(conn, encounter_id, changes)


# =====================================================================
# Reports (summary, readmission analysis, dashboard)
# =====================================================================

def _scored_encounters(conn: psycopg.Connection) -> list[dict[str, object]]:
    """Every encounter in the database, with risk scores (no paging)."""
    rows = repository.get_encounters(conn, limit=None)
    return [score_encounter(row) for row in rows]


def _risk_counts(
    scored_rows: list[dict[str, object]],
) -> dict[str, int]:
    """Count encounters per risk level, e.g. {"LOW": 10, "MEDIUM": 4, "HIGH": 2}."""
    counts = {level.value: 0 for level in RiskLevel}
    for row in scored_rows:
        counts[str(row["risk_level"])] += 1
    return counts


def _readmission_analysis(
    scored_rows: list[dict[str, object]],
) -> dict[str, object]:
    """Compare risk levels with what actually happened (the historical `readmitted` value).

    readmitted is "<30" (back within 30 days), ">30" (back later) or "NO".
    Rows with any other value (empty or "?") have an unknown outcome and are
    left out of the rate, so they do not distort the percentage.
    """
    # Put the encounters into one list per risk level.
    groups: dict[str, list[dict[str, object]]] = {
        level.value: [] for level in RiskLevel
    }
    for row in scored_rows:
        groups[str(row["risk_level"])].append(row)

    # Work out the numbers for each level.
    results: list[dict[str, object]] = []
    for level in RiskLevel:
        rows = groups[level.value]
        known = [
            row
            for row in rows
            if row.get("readmitted") in ("<30", ">30", "NO")
        ]
        readmitted = sum(row.get("readmitted") == "<30" for row in known)
        results.append(
            {
                "risk_level": level.value,
                "encounters": len(rows),
                "known_outcomes": len(known),
                "readmitted_under_30_days": readmitted,
                "readmission_rate": rate_percent(readmitted, len(known)),
            }
        )

    # The HIGH group is also reported on its own as the headline numbers.
    high = next(
        result for result in results if result["risk_level"] == RiskLevel.HIGH
    )
    return {
        "risk_groups": results,
        "high_risk_patients": high["encounters"],
        "high_risk_readmitted_under_30_days": high["readmitted_under_30_days"],
        "high_risk_readmission_rate": high["readmission_rate"],
    }


def _operations_summary(
    conn: psycopg.Connection, scored_rows: list[dict[str, object]]
) -> dict[str, int]:
    """Counts of encounters per risk level and of interventions by status."""
    counts = _risk_counts(scored_rows)
    statuses = repository.get_latest_intervention_status_counts(conn)
    return {
        "total_encounters": len(scored_rows),
        "high_risk": counts[RiskLevel.HIGH.value],
        "medium_risk": counts[RiskLevel.MEDIUM.value],
        "low_risk": counts[RiskLevel.LOW.value],
        # "pending" = work not finished yet: open or in progress.
        "pending_interventions": statuses.get("open", 0)
        + statuses.get("in_progress", 0),
        "completed_interventions": statuses.get("completed", 0),
    }


def operations_summary(conn: psycopg.Connection) -> dict[str, int]:
    return _operations_summary(conn, _scored_encounters(conn))


def readmission_analysis(conn: psycopg.Connection) -> dict[str, object]:
    return _readmission_analysis(_scored_encounters(conn))


def management_dashboard(conn: psycopg.Connection) -> dict[str, object]:
    """Short summary for managers, built from the same helpers as the reports above."""
    # Score the encounters once and reuse the result for both reports.
    scored_rows = _scored_encounters(conn)
    summary = _operations_summary(conn, scored_rows)
    analysis = _readmission_analysis(scored_rows)
    return {
        "total_encounters": summary["total_encounters"],
        "high_risk": summary["high_risk"],
        "medium_risk": summary["medium_risk"],
        "low_risk": summary["low_risk"],
        # The care queue = HIGH + MEDIUM risk encounters.
        "care_queue_size": summary["high_risk"] + summary["medium_risk"],
        "high_risk_readmission_rate": analysis["high_risk_readmission_rate"],
    }
