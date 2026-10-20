"""Data shapes (Pydantic models) for the API: what goes in and what comes out.

FastAPI uses these to validate requests and to build the /docs page.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# The database only allows these four statuses.
class InterventionStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# One hospital encounter plus its calculated risk. "| None" means the value can be missing.
class Encounter(BaseModel):
    encounter_id: int
    patient_nbr: int | None
    age: str | None
    time_in_hospital: int | None
    number_inpatient: int | None
    number_emergency: int | None
    number_outpatient: int | None
    num_medications: int | None
    num_lab_procedures: int | None
    discharge_disposition_id: int | None
    admission_type_id: int | None
    readmitted: str | None
    risk_score: int
    risk_level: RiskLevel


# Body of POST /encounters. encounter_id is not sent: the API assigns the next one.
# readmitted is not accepted, because a new encounter's outcome is not known yet.
class EncounterCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")   # unknown fields are rejected

    patient_nbr: int = Field(ge=1)
    age: str = Field(pattern=r"^\[\d{1,2}-\d{2,3}\)$")   # age band, e.g. "[80-90)"
    time_in_hospital: int = Field(ge=0)
    number_inpatient: int = Field(ge=0)
    number_emergency: int = Field(ge=0)
    num_medications: int = Field(ge=0)
    number_outpatient: int | None = Field(default=None, ge=0)
    num_lab_procedures: int | None = Field(default=None, ge=0)
    discharge_disposition_id: int | None = None
    admission_type_id: int | None = None


# An encounter in the care queue: the same fields plus its latest intervention.
class QueueItem(Encounter):
    intervention_status: InterventionStatus | None = None
    assigned_to: str | None = None
    notes: str | None = None


# Response of GET /patients/search: how many encounters matched, and one page of them.
class PatientSearchResult(BaseModel):
    total: int
    items: list[QueueItem]


# Body of PATCH /interventions/{encounter_id}. Send only what you want to change.
class InterventionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")   # unknown fields are rejected

    status: InterventionStatus | None = None
    assigned_to: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def require_an_update(self) -> "InterventionUpdate":
        # model_fields_set = the fields the caller actually sent.
        if not self.model_fields_set:
            raise ValueError("Provide at least one intervention field to update.")
        # Sending status: null is not allowed (leave it out to keep the old one).
        if "status" in self.model_fields_set and self.status is None:
            raise ValueError("status cannot be null.")
        return self


# An intervention as stored in the database.
class Intervention(BaseModel):
    intervention_id: int
    encounter_id: int
    status: InterventionStatus
    assigned_to: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


# Response of GET /operations/summary.
class OperationsSummary(BaseModel):
    total_encounters: int
    high_risk: int
    medium_risk: int
    low_risk: int
    pending_interventions: int
    completed_interventions: int


# Readmission numbers for one risk level.
class ReadmissionGroup(BaseModel):
    risk_level: RiskLevel
    encounters: int
    known_outcomes: int
    readmitted_under_30_days: int
    readmission_rate: float | None   # percent; None when no outcome is known


# Response of GET /operations/readmission-analysis.
class ReadmissionAnalysis(BaseModel):
    risk_groups: list[ReadmissionGroup]
    high_risk_patients: int
    high_risk_readmitted_under_30_days: int
    high_risk_readmission_rate: float | None


# Response of GET /management/dashboard.
class ManagementDashboard(BaseModel):
    total_encounters: int
    high_risk: int
    medium_risk: int
    low_risk: int
    care_queue_size: int
    high_risk_readmission_rate: float | None
