// Calls GET /encounters/{encounter_id} and prints the response.
//
// Terminal 1 (keep it running), from w2day412Oct26_PSQL:   uvicorn main:app --reload
// Terminal 2, from w2day412Oct26_PSQL/frontend:            npx tsx encounter.ts 12522

import type { Encounter, EncounterView } from "./interface";

const BASE_URL = "http://127.0.0.1:8000";

async function fetchEncounter(encounterId: number): Promise<Encounter | null> {
    const response = await fetch(`${BASE_URL}/encounters/${encounterId}`);

    // The API sends 404 when the encounter id is not in the database.
    if (response.status === 404) {
        return null;
    }
    if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
    }

    const data: Encounter = await response.json();
    return data;
}

// Keep only the fields the UI needs.
function toView(encounter: Encounter): EncounterView {
    return {
        encounter_id: encounter.encounter_id,
        patient_nbr: encounter.patient_nbr,
        age: encounter.age,
        risk_score: encounter.risk_score,
        risk_level: encounter.risk_level,
    };
}

async function main(): Promise<void> {
    const encounterId = Number(process.argv[2] ?? 12522);

    if (!Number.isInteger(encounterId)) {
        console.log("Please pass a whole number, for example: npx tsx encounter.ts 12522");
        return;
    }

    const encounter = await fetchEncounter(encounterId);

    if (encounter === null) {
        console.log(`Encounter ${encounterId} not found.`);
        return;
    }

    console.log("Full API response:");
    console.log(JSON.stringify(encounter, null, 2));

    console.log("\nData for the UI:");
    console.log(JSON.stringify(toView(encounter), null, 2));
}

main().catch((error) => {
    // "fetch failed" means nothing answered at BASE_URL, so the API is not running.
    if (error.message === "fetch failed") {
        console.error(`Could not reach the API at ${BASE_URL}. Start it with: uvicorn main:app --reload`);
        return;
    }
    console.error(error.message);
});
