// Calls GET /patients/search from the terminal and prints the matches.
//
// Terminal 1 (keep it running), from w2day412Oct26_PSQL:   uvicorn main:app --reload
// Terminal 2, from w2day412Oct26_PSQL/frontend:
//     npx tsx search-patients.ts patient_nbr=88785891
//     npx tsx search-patients.ts risk_level=HIGH risk_score=8

import { BASE_URL, searchPatients } from "./api";
import type { PatientSearch, RiskLevel } from "./interface";

// Turn "key=value" arguments into the search filters.
function readArgs(args: string[]): PatientSearch {
    const search: PatientSearch = {};
    for (const arg of args) {
        const [key, value] = arg.split("=");
        if (key === "patient_nbr") search.patient_nbr = Number(value);
        else if (key === "risk_score") search.risk_score = Number(value);
        else if (key === "risk_level") search.risk_level = value as RiskLevel;
        else if (key === "limit") search.limit = Number(value);
        else throw new Error(`Unknown argument "${arg}". Use patient_nbr=, risk_level=, risk_score= or limit=`);
    }
    return search;
}

async function main(): Promise<void> {
    const search = readArgs(process.argv.slice(2));
    const result = await searchPatients(search);

    console.log(`GET /patients/search ${JSON.stringify(search)}`);
    console.log(`${result.total} matching encounters, showing ${result.items.length}:`);
    console.table(result.items.map((item) => ({
        encounter_id: item.encounter_id,
        patient_nbr: item.patient_nbr,
        risk_score: item.risk_score,
        risk_level: item.risk_level,
        intervention_status: item.intervention_status,
    })));
}

main().catch((error) => {
    // "fetch failed" means nothing answered at BASE_URL, so the API is not running.
    if (error.message === "fetch failed") {
        console.error(`Could not reach the API at ${BASE_URL}. Start it with: uvicorn main:app --reload`);
        return;
    }
    console.error(error.message);
});
