"""All SQL queries live here. No business rules - just reading and writing the tables.

Tables used:
    diabetic_patient   - one row per hospital encounter (already exists in the database)
    care_interventions - follow-up actions for an encounter (already exists)

Every function takes `conn`, an open database connection from database.py.
Values are always passed as %s parameters (never pasted into the SQL text),
which protects against SQL injection.
"""

from collections.abc import Mapping, Sequence
from typing import Any

import psycopg

# One database row, as a dict: {"column_name": value}
Row = dict[str, Any]

# The encounter columns we select. Shared by several queries (p = diabetic_patient).
ENCOUNTER_COLUMNS = """
    p.encounter_id, p.patient_nbr, p.age, p.time_in_hospital, p.number_inpatient,
    p.number_emergency, p.number_outpatient, p.num_medications, p.num_lab_procedures,
    p.discharge_disposition_id, p.admission_type_id, p.readmitted
"""

# Joins each encounter to its most recent intervention (highest intervention_id).
# LEFT JOIN keeps encounters that have no intervention yet (those columns are NULL).
LATEST_INTERVENTION = """
    LEFT JOIN LATERAL (
        SELECT status AS intervention_status, assigned_to, notes
        FROM care_interventions ci
        WHERE ci.encounter_id = p.encounter_id
        ORDER BY ci.intervention_id DESC
        LIMIT 1
    ) li ON TRUE
"""


# ---------- Reading encounters ----------

def get_encounters(
    conn: psycopg.Connection, limit: int | None = 50, offset: int = 0
) -> list[Row]:
    """Return encounters ordered by id. limit=None returns all of them."""
    if limit is None:
        query = f"""
            SELECT {ENCOUNTER_COLUMNS}
            FROM diabetic_patient p
            ORDER BY p.encounter_id
        """
        return list(conn.execute(query).fetchall())

    # limit/offset are used for paging: "give me `limit` rows after skipping `offset`".
    query = f"""
        SELECT {ENCOUNTER_COLUMNS}
        FROM diabetic_patient p
        ORDER BY p.encounter_id
        LIMIT %s OFFSET %s
    """
    return list(conn.execute(query, (limit, offset)).fetchall())


def get_encounter(conn: psycopg.Connection, encounter_id: int) -> Row | None:
    """Return one encounter, or None if the id does not exist."""
    query = f"""
        SELECT {ENCOUNTER_COLUMNS}
        FROM diabetic_patient p
        WHERE p.encounter_id = %s
    """
    return conn.execute(query, (encounter_id,)).fetchone()


def insert_encounter(conn: psycopg.Connection, encounter: Mapping[str, object]) -> Row:
    """Insert one new encounter and return it. The new encounter_id is MAX + 1.

    diabetic_patient.encounter_id has no default value, so the id is worked out here.
    The lock makes a second insert wait until this transaction ends, so two requests
    cannot pick the same id. Reads are not blocked.
    """
    conn.execute("LOCK TABLE diabetic_patient IN SHARE ROW EXCLUSIVE MODE")

    columns = (
        "patient_nbr",
        "age",
        "time_in_hospital",
        "number_inpatient",
        "number_emergency",
        "number_outpatient",
        "num_medications",
        "num_lab_procedures",
        "discharge_disposition_id",
        "admission_type_id",
    )
    column_sql = ", ".join(columns)
    placeholders = ", ".join("%s" for _ in columns)
    query = f"""
        INSERT INTO diabetic_patient AS p (encounter_id, {column_sql})
        VALUES (
            (SELECT COALESCE(MAX(encounter_id), 0) + 1 FROM diabetic_patient),
            {placeholders}
        )
        RETURNING {ENCOUNTER_COLUMNS}
    """
    values = tuple(encounter.get(column) for column in columns)
    return conn.execute(query, values).fetchone()


def get_care_queue(conn: psycopg.Connection) -> list[Row]:
    """Return ALL encounters plus their latest intervention info.

    The risk filtering happens later in service.py, because the risk score is
    calculated in Python, not stored in the database.
    """
    query = f"""
        SELECT {ENCOUNTER_COLUMNS},
               li.intervention_status, li.assigned_to, li.notes
        FROM diabetic_patient p
        {LATEST_INTERVENTION}
        ORDER BY p.encounter_id
    """
    return list(conn.execute(query).fetchall())


def search_encounters(
    conn: psycopg.Connection, patient_nbr: int | None = None
) -> list[Row]:
    """Return encounters plus their latest intervention, optionally for one patient only.

    The risk filters happen later in service.py, because the risk score is
    calculated in Python, not stored in the database.
    """
    if patient_nbr is None:
        return get_care_queue(conn)

    query = f"""
        SELECT {ENCOUNTER_COLUMNS},
               li.intervention_status, li.assigned_to, li.notes
        FROM diabetic_patient p
        {LATEST_INTERVENTION}
        WHERE p.patient_nbr = %s
        ORDER BY p.encounter_id
    """
    return list(conn.execute(query, (patient_nbr,)).fetchall())


# ---------- Interventions ----------

def get_latest_intervention(
    conn: psycopg.Connection, encounter_id: int
) -> Row | None:
    """Return the newest intervention of an encounter, or None if it has none."""
    return conn.execute(
        """
        SELECT intervention_id, encounter_id, status, assigned_to, notes,
               created_at, updated_at
        FROM care_interventions
        WHERE encounter_id = %s
        ORDER BY intervention_id DESC
        LIMIT 1
        """,
        (encounter_id,),
    ).fetchone()


def get_intervention_history(
    conn: psycopg.Connection, encounter_id: int
) -> list[Row]:
    """Return every intervention of an encounter, newest first (empty list if none)."""
    return list(
        conn.execute(
            """
            SELECT intervention_id, encounter_id, status, assigned_to, notes,
                   created_at, updated_at
            FROM care_interventions
            WHERE encounter_id = %s
            ORDER BY intervention_id DESC
            """,
            (encounter_id,),
        ).fetchall()
    )


def encounter_exists(conn: psycopg.Connection, encounter_id: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM diabetic_patient WHERE encounter_id = %s", (encounter_id,)
    ).fetchone()
    return row is not None


def update_intervention(
    conn: psycopg.Connection,
    encounter_id: int,
    changes: Mapping[str, object],
) -> Row | None:
    """Record an intervention update as a NEW care_interventions row (keeps the history).

    `changes` only contains the fields the caller sent (status, assigned_to, notes).
    Fields that were not sent are copied from the latest intervention, so the new
    row is the full current state. The newest row (highest intervention_id) is the
    one every other query treats as "latest".
    Returns the saved intervention, or None if the encounter does not exist.
    """
    # Step 1: make sure the encounter exists. FOR UPDATE locks that row until the
    # transaction ends, so two updates of the same encounter run one after the other.
    exists = conn.execute(
        "SELECT encounter_id FROM diabetic_patient WHERE encounter_id = %s FOR UPDATE",
        (encounter_id,),
    ).fetchone()
    if exists is None:
        return None

    # Step 2: start from the latest intervention, or from a new "open" one.
    current = get_latest_intervention(conn, encounter_id)
    new_values = {
        "status": current["status"] if current else "open",
        "assigned_to": current["assigned_to"] if current else None,
        "notes": current["notes"] if current else None,
    }

    # Step 3: apply the fields that were sent, and insert the result as a new row.
    for field in new_values:
        if field in changes:
            new_values[field] = changes[field]

    inserted = conn.execute(
        """
        INSERT INTO care_interventions (encounter_id, status, assigned_to, notes)
        VALUES (%s, %s, %s, %s)
        RETURNING intervention_id, encounter_id, status, assigned_to, notes,
                  created_at, updated_at
        """,
        (
            encounter_id,
            new_values["status"],
            new_values["assigned_to"],
            new_values["notes"],
        ),
    )
    return inserted.fetchone()


def get_latest_intervention_status_counts(conn: psycopg.Connection) -> dict[str, int]:
    """Count encounters per intervention status, using each encounter's newest intervention.

    Returns e.g. {"open": 5, "completed": 2}. Statuses with no rows are not included.
    """
    rows = conn.execute(
        """
        WITH latest AS (
            SELECT DISTINCT ON (encounter_id) encounter_id, status
            FROM care_interventions
            ORDER BY encounter_id, intervention_id DESC
        )
        SELECT status, count(*) AS count
        FROM latest
        GROUP BY status
        """
    ).fetchall()
    return {row["status"]: row["count"] for row in rows}


# ---------- Loading data (used by data_loader.py) ----------

def load_encounters(
    conn: psycopg.Connection, rows: Sequence[Mapping[str, object]]
) -> None:
    """Insert encounters, or update them if the encounter_id already exists (an "upsert")."""
    if not rows:
        return

    columns = (
        "encounter_id",
        "patient_nbr",
        "age",
        "time_in_hospital",
        "number_inpatient",
        "number_emergency",
        "number_outpatient",
        "num_medications",
        "num_lab_procedures",
        "discharge_disposition_id",
        "admission_type_id",
        "readmitted",
    )

    # Build the SQL pieces from the column list so the names are written only once.
    column_sql = ", ".join(columns)                               # "encounter_id, patient_nbr, ..."
    placeholders = ", ".join("%s" for _ in columns)               # "%s, %s, ..."
    update_sql = ", ".join(                                       # "patient_nbr = EXCLUDED.patient_nbr, ..."
        f"{column} = EXCLUDED.{column}"
        for column in columns
        if column != "encounter_id"
    )
    # ON CONFLICT: if the encounter_id is already in the table, update that row instead.
    query = f"""
        INSERT INTO diabetic_patient ({column_sql})
        VALUES ({placeholders})
        ON CONFLICT (encounter_id) DO UPDATE SET {update_sql}
    """

    # One tuple of values per row, in the same order as `columns` (missing -> None).
    values = [tuple(row.get(column) for column in columns) for row in rows]
    with conn.cursor() as cursor:
        cursor.executemany(query, values)
