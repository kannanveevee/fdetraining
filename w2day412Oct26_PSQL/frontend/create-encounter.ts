// Calls POST /encounters from the terminal, then reads the new encounter back with GET.
//
// Terminal 1 (keep it running), from w2day412Oct26_PSQL:   uvicorn main:app --reload
// Terminal 2, from w2day412Oct26_PSQL/frontend:            npx tsx create-encounter.ts

import { BASE_URL, createEncounter, getEncounter } from "./api";
import type { EncounterCreate } from "./interface";

const newEncounter: EncounterCreate = {
    patient_nbr: 99000002,
    age: "[70-80)",
    time_in_hospital: 3,
    number_inpatient: 3,
    number_emergency: 0,
    num_medications: 12,
};

async function main(): Promise<void> {
    const created = await createEncounter(newEncounter);
    console.log("POST /encounters response:");
    console.log(JSON.stringify(created, null, 2));

    // Read it back, to show the API returns what is saved in PostgreSQL.
    const saved = await getEncounter(created.encounter_id);
    console.log(`\nGET /encounters/${created.encounter_id} response:`);
    console.log(JSON.stringify(saved, null, 2));
}

main().catch((error) => {
    // "fetch failed" means nothing answered at BASE_URL, so the API is not running.
    if (error.message === "fetch failed") {
        console.error(`Could not reach the API at ${BASE_URL}. Start it with: uvicorn main:app --reload`);
        return;
    }
    console.error(error.message);
});
