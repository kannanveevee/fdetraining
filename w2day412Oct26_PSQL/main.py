"""Care Management API - the web layer.

Each function below is one URL (route). A route only:
  1. reads the request (path, query string, body),
  2. calls a function in service.py,
  3. returns the result, or an HTTP error such as 404 if nothing was found.
The business rules are in service.py and the SQL is in repository.py.

Run:   uvicorn main:app --reload
Docs:  http://127.0.0.1:8000/docs
"""

from typing import Annotated

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from database import get_connection
from models import (
    Encounter,
    Intervention,
    InterventionUpdate,
    ManagementDashboard,
    OperationsSummary,
    QueueItem,
    ReadmissionAnalysis,
    RiskLevel,
)
from service import (
    get_encounter,
    list_care_queue,
    list_encounters,
    management_dashboard,
    operations_summary,
    readmission_analysis,
    update_intervention,
)

app = FastAPI(
    title="Care Management Prioritization API",
    description=(
        "An explainable, non-clinical prototype for prioritizing diabetes encounters. "
        "Its scoring weights are learning assumptions, not clinical recommendations."
    ),
    version="1.0.0",
)

# Short name for "a database connection". FastAPI opens one per request through
# get_connection() and closes it when the request is finished.
Connection = Annotated[psycopg.Connection, Depends(get_connection)]

app.add_middleware (
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Encounters ----------

@app.get("/encounters", response_model=list[Encounter])
def encounters(
    conn: Connection,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,   # page size, 1 to 500
    offset: Annotated[int, Query(ge=0)] = 0,           # how many rows to skip
) -> list[dict[str, object]]:
    return list_encounters(conn, limit=limit, offset=offset)


@app.get("/encounters/{encounter_id}", response_model=Encounter)
def encounter(encounter_id: int, conn: Connection) -> dict[str, object]:
    result = get_encounter(conn, encounter_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Encounter not found.")
    return result


# ---------- Care queue ----------

@app.get("/care-queue", response_model=list[QueueItem])
def care_queue(
    conn: Connection,
    min_risk_score: Annotated[int, Query(ge=3, le=8)] = 3,   # 3 = MEDIUM and above
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict[str, object]]:
    return list_care_queue(
        conn, min_risk_score=min_risk_score, limit=limit, offset=offset
    )


@app.get("/care-queue/high", response_model=list[QueueItem])
def high_risk_care_queue(
    conn: Connection,
    min_risk_score: Annotated[int, Query(ge=5, le=8)] = 5,   # 5 = HIGH
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict[str, object]]:
    return list_care_queue(
        conn,
        min_risk_score=min_risk_score,
        risk_level=RiskLevel.HIGH,
        limit=limit,
        offset=offset,
    )


# ---------- Interventions ----------

@app.patch("/interventions/{encounter_id}", response_model=Intervention)
def patch_intervention(
    encounter_id: int, update: InterventionUpdate, conn: Connection
) -> dict[str, object]:
    # exclude_unset: pass on only the fields the caller really sent,
    # so anything they left out keeps its old value.
    intervention = update_intervention(
        conn, encounter_id, update.model_dump(mode="json", exclude_unset=True)
    )
    if intervention is None:
        raise HTTPException(status_code=404, detail="Encounter not found.")
    return intervention


# ---------- Reports ----------

@app.get("/operations/summary", response_model=OperationsSummary)
def operations(conn: Connection) -> dict[str, int]:
    return operations_summary(conn)


@app.get(
    "/operations/readmission-analysis", response_model=ReadmissionAnalysis
)
def readmissions(conn: Connection) -> dict[str, object]:
    return readmission_analysis(conn)


@app.get("/management/dashboard", response_model=ManagementDashboard)
def dashboard(conn: Connection) -> dict[str, object]:
    return management_dashboard(conn)
