-- Check the existing tables used by this project.
-- This script intentionally does not create or alter database objects.

DO $$
DECLARE
    missing_columns TEXT;
BEGIN
    SELECT string_agg(expected.table_name || '.' || expected.column_name, ', ')
    INTO missing_columns
    FROM (
        VALUES
            ('diabetic_patient', 'encounter_id'),
            ('diabetic_patient', 'patient_nbr'),
            ('diabetic_patient', 'age'),
            ('diabetic_patient', 'time_in_hospital'),
            ('diabetic_patient', 'number_inpatient'),
            ('diabetic_patient', 'number_emergency'),
            ('diabetic_patient', 'number_outpatient'),
            ('diabetic_patient', 'num_medications'),
            ('diabetic_patient', 'num_lab_procedures'),
            ('diabetic_patient', 'discharge_disposition_id'),
            ('diabetic_patient', 'admission_type_id'),
            ('diabetic_patient', 'readmitted'),
            ('care_interventions', 'intervention_id'),
            ('care_interventions', 'encounter_id'),
            ('care_interventions', 'status'),
            ('care_interventions', 'assigned_to'),
            ('care_interventions', 'notes'),
            ('care_interventions', 'created_at'),
            ('care_interventions', 'updated_at')
    ) AS expected(table_name, column_name)
    LEFT JOIN information_schema.columns AS actual
        ON actual.table_schema = 'public'
       AND actual.table_name = expected.table_name
       AND actual.column_name = expected.column_name
    WHERE actual.column_name IS NULL;

    IF missing_columns IS NOT NULL THEN
        RAISE EXCEPTION 'Required existing database columns are missing: %',
            missing_columns;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'public.diabetic_patient'::regclass
          AND contype = 'p'
          AND pg_get_constraintdef(oid) = 'PRIMARY KEY (encounter_id)'
    ) THEN
        RAISE EXCEPTION
            'diabetic_patient must have a primary key on encounter_id';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'public.care_interventions'::regclass
          AND contype = 'f'
          AND confrelid = 'public.diabetic_patient'::regclass
          AND pg_get_constraintdef(oid)
              LIKE 'FOREIGN KEY (encounter_id) REFERENCES diabetic_patient(encounter_id)%'
    ) THEN
        RAISE EXCEPTION
            'care_interventions.encounter_id must reference diabetic_patient.encounter_id';
    END IF;
END;
$$;

-- The application uses the status values supported by this existing constraint.
SELECT
    conname AS constraint_name,
    pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conrelid = 'public.care_interventions'::regclass
  AND contype = 'c';
