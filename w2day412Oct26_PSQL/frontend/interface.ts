// What one encounter looks like when it comes back from GET /encounters/{encounter_id}.
// The fields match the Encounter model in models.py.
// "| null" means the value can be missing in the database.

export interface Encounter {
    encounter_id: number;
    patient_nbr: number | null;
    age: string | null;              // age band from the dataset, for example "[80-90)"
    time_in_hospital: number | null;
    number_inpatient: number | null;
    number_emergency: number | null;
    number_outpatient: number | null;
    num_medications: number | null;
    num_lab_procedures: number | null;
    discharge_disposition_id: number | null;
    admission_type_id: number | null;
    readmitted: string | null;
    risk_score: number;
    risk_level: "LOW" | "MEDIUM" | "HIGH";
}

// Body of POST /encounters. Matches the EncounterCreate model in models.py.
// encounter_id is not sent: the API assigns it. "?" fields may be left out.
export interface EncounterCreate {
    patient_nbr: number;
    age: string;                     // age band, for example "[60-70)"
    time_in_hospital: number;
    number_inpatient: number;
    number_emergency: number;
    num_medications: number;
    number_outpatient?: number | null;
    num_lab_procedures?: number | null;
    discharge_disposition_id?: number | null;
    admission_type_id?: number | null;
}

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH";

// The statuses the care_interventions table allows (InterventionStatus in models.py).
export type InterventionStatus = "open" | "in_progress" | "completed" | "cancelled";

// An encounter plus its latest intervention. Matches QueueItem in models.py.
// Returned by GET /patients/search and GET /care-queue/high.
export interface QueueItem extends Encounter {
    intervention_status: InterventionStatus | null;   // null = no intervention yet
    assigned_to: string | null;
    notes: string | null;
}

// Query of GET /patients/search. Give at least one of the three filters.
export interface PatientSearch {
    patient_nbr?: number;
    risk_level?: RiskLevel;
    risk_score?: number;             // exact score, 0 to 8
    limit?: number;
    offset?: number;
}

// Response of GET /patients/search. Matches PatientSearchResult in models.py.
export interface PatientSearchResult {
    total: number;                   // all matches; items is one page of them
    items: QueueItem[];
}

// One intervention row. Matches Intervention in models.py.
// GET /interventions/{encounter_id} returns a list of these, newest first.
export interface Intervention {
    intervention_id: number;
    encounter_id: number;
    status: InterventionStatus;
    assigned_to: string | null;
    notes: string | null;
    created_at: string;              // ISO date-time from the API
    updated_at: string;
}

// Body of PATCH /interventions/{encounter_id}. Matches InterventionUpdate in models.py.
// Send at least one field; fields left out keep their latest value.
export interface InterventionUpdate {
    status?: InterventionStatus;
    assigned_to?: string | null;
    notes?: string | null;
}

// The fields the UI shows on the encounter screen.
export interface EncounterView {
    encounter_id: number;
    patient_nbr: number | null;
    age: string | null;
    risk_score: number;
    risk_level: "LOW" | "MEDIUM" | "HIGH";
}
