// Functions that call the Python API. Used by index.html (compiled to dist/api.js)
// and by create-encounter.ts in the terminal.
//
// Build for the browser, from w2day412Oct26_PSQL/frontend:   npm run build

import type {
    Encounter,
    EncounterCreate,
    Intervention,
    InterventionUpdate,
    PatientSearch,
    PatientSearchResult,
    QueueItem,
} from "./interface";

export const BASE_URL = "http://127.0.0.1:8000";

// Turns a non-OK response into an Error with the API's message.
// FastAPI sends {"detail": "..."} or, for 422 validation errors, {"detail": [{loc, msg}, ...]}.
async function apiError(response: Response): Promise<Error> {
    let message = `${response.status} ${response.statusText}`;
    try {
        const body = await response.json();
        if (Array.isArray(body.detail)) {
            message += ": " + body.detail
                .map((error: { loc: string[]; msg: string }) => `${error.loc.at(-1)} - ${error.msg}`)
                .join("; ");
        } else if (body.detail) {
            message += `: ${body.detail}`;
        }
    } catch {
        // The body was not JSON; keep the status text only.
    }
    return new Error(`API error ${message}`);
}

// POST /encounters - saves a new encounter and returns it with its new id and risk score.
export async function createEncounter(encounter: EncounterCreate): Promise<Encounter> {
    const response = await fetch(`${BASE_URL}/encounters`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(encounter),
    });
    if (response.status !== 201) {
        throw await apiError(response);
    }
    const created: Encounter = await response.json();
    return created;
}

// GET /encounters/{encounter_id} - one encounter, or null if the id does not exist.
export async function getEncounter(encounterId: number): Promise<Encounter | null> {
    const response = await fetch(`${BASE_URL}/encounters/${encounterId}`);
    if (response.status === 404) {
        return null;
    }
    if (!response.ok) {
        throw await apiError(response);
    }
    const encounter: Encounter = await response.json();
    return encounter;
}

// GET /patients/search - encounters matching every filter given (patient number,
// risk level, exact risk score). Filters left out (undefined) are not sent.
export async function searchPatients(search: PatientSearch): Promise<PatientSearchResult> {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(search)) {
        if (value !== undefined) {
            params.set(key, String(value));
        }
    }
    const response = await fetch(`${BASE_URL}/patients/search?${params}`);
    if (!response.ok) {
        throw await apiError(response);
    }
    const result: PatientSearchResult = await response.json();
    return result;
}

// GET /care-queue/high - HIGH risk encounters, highest score first, each with the
// status of its latest care intervention (null if it has none yet).
export async function getHighRiskQueue(limit = 50, offset = 0): Promise<QueueItem[]> {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    const response = await fetch(`${BASE_URL}/care-queue/high?${params}`);
    if (!response.ok) {
        throw await apiError(response);
    }
    const queue: QueueItem[] = await response.json();
    return queue;
}

// GET /interventions/{encounter_id} - every status update of the encounter, newest
// first ([] if none yet), or null if the encounter does not exist.
export async function getInterventionHistory(encounterId: number): Promise<Intervention[] | null> {
    const response = await fetch(`${BASE_URL}/interventions/${encounterId}`);
    if (response.status === 404) {
        return null;
    }
    if (!response.ok) {
        throw await apiError(response);
    }
    const history: Intervention[] = await response.json();
    return history;
}

// PATCH /interventions/{encounter_id} - saves a status update as a new intervention row
// and returns it. Fields left out keep their latest value.
export async function updateIntervention(
    encounterId: number,
    update: InterventionUpdate,
): Promise<Intervention> {
    const response = await fetch(`${BASE_URL}/interventions/${encounterId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(update),
    });
    if (!response.ok) {
        throw await apiError(response);
    }
    const saved: Intervention = await response.json();
    return saved;
}
