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

// The fields the UI shows on the encounter screen.
export interface EncounterView {
    encounter_id: number;
    patient_nbr: number | null;
    age: string | null;
    risk_score: number;
    risk_level: "LOW" | "MEDIUM" | "HIGH";
}
