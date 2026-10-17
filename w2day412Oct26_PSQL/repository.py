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


def update_intervention(
    conn: psycopg.Connection,
    encounter_id: int,
    changes: Mapping[str, object],
) -> Row | None:
    """Create the encounter's intervention, or update it if one already exists.

    `changes` only contains the fields the caller sent (status, assigned_to, notes).
    Returns the saved intervention, or None if the encounter does not exist.
    """
    # Step 1: make sure the encounter exists. FOR UPDATE locks that row until the
    # transaction ends, so two requests cannot create duplicate interventions at once.
    exists = conn.execute(
        "SELECT encounter_id FROM diabetic_patient WHERE encounter_id = %s FOR UPDATE",
        (encounter_id,),
    ).fetchone()
    if exists is None:
        return None

    # Step 2: no intervention yet -> create one (status defaults to "open").
    current = get_latest_intervention(conn, encounter_id)
    if current is None:
        inserted = conn.execute(
            """
            INSERT INTO care_interventions (encounter_id, status, assigned_to, notes)
            VALUES (%s, %s, %s, %s)
            RETURNING intervention_id, encounter_id, status, assigned_to, notes,
                      created_at, updated_at
            """,
            (
                encounter_id,
                changes.get("status", "open"),
                changes.get("assigned_to"),
                changes.get("notes"),
            ),
        )
        return inserted.fetchone()

    # Step 3: an intervention exists -> update only the fields that were sent.
    # Column names cannot be %s parameters, so they are pasted into the SQL text.
    # That is safe because only names from this fixed list are ever used.
    allowed_columns = {"status", "assigned_to", "notes"}
    fields = [field for field in changes if field in allowed_columns]
    if not fields:
        return current  # nothing to change

    assignments = ", ".join(f"{field} = %s" for field in fields)   # "status = %s, notes = %s"
    values: Sequence[object] = tuple(changes[field] for field in fields)
    updated = conn.execute(
        f"""
        UPDATE care_interventions
        SET {assignments}
        WHERE intervention_id = %s
        RETURNING intervention_id, encounter_id, status, assigned_to, notes,
                  created_at, updated_at
        """,
        (*values, current["intervention_id"]),
    )
    return updated.fetchone()


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
