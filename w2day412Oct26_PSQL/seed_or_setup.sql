-- Check the existing dataset and intervention records.
-- Nothing is inserted or changed by this script.
--
-- To load a CSV into the existing diabetic_patient table, run:
--   python data_loader.py path\to\diabetic_data.csv
--
-- Set DATABASE_URL in .env before running the loader or starting the API.

SELECT
    'diabetic_patient' AS table_name,
    count(*) AS encounter_count
FROM diabetic_patient;

SELECT
    readmitted AS historical_outcome,
    count(*) AS encounter_count
FROM diabetic_patient
GROUP BY readmitted
ORDER BY readmitted NULLS LAST;

SELECT
    status,
    count(*) AS intervention_count
FROM care_interventions
GROUP BY status
ORDER BY status;
