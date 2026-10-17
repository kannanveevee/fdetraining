Critical Data Leakage Rule:
The `readmitted` field is the historical outcome. Do NOT use it to calculate the risk score. Use it only after scoring to
evaluate whether your prioritization identified a population with higher historical <30-day readmission.

Prototype Prioritization Rule:
For this mini project, use a simple explainable scoring rule. These weights are learning assumptions, not clinical
recommendations.
Condition             Points
number_inpatient >= 3  +3
number_emergency >= 2  +2
number_outpatient >= 3 +1
time_in_hospital >= 7  +1
num_medications >= 20  +1
Risk level mapping: 0-2 = LOW | 3-4 = MEDIUM | 5+ = HIGH

Layering Rule
Keep SQL in repository.py, business rules in service.py, request/response handling in main.py, and database configuration
in database.py.

PostgreSQL Design  <<Table Created in PostgreSQL>>
Table A — patient_encounters
encounter_id
patient_nbr
age
time_in_hospital
number_inpatient
number_emergency
number_outpatient
num_medications
num_lab_procedures
discharge_disposition_id
admission_type_id
readmitted
risk_score
risk_level

Table B — care_interventions  <<Table Created in PostgreSQL>>
intervention_id
encounter_id
status
assigned_to
notes
created_at
updated_at

Suggested intervention statuses:
PENDING_REVIEW → ASSIGNED → CONTACTED → FOLLOW_UP_SCHEDULED → CLOSED

8. What You Must Build
1. Load the selected healthcare dataset fields into PostgreSQL.
2. Calculate risk_score and risk_level without using the historical readmitted outcome.
3. Create a care-management queue for MEDIUM and HIGH risk encounters.
4. Allow care-management intervention status to be tracked.
5. Expose operational metrics through FastAPI.
6. Compare your prioritization against historical <30-day readmission outcomes.

Mandatory FastAPI Endpoints
Method Endpoint                        Purpose
GET /encounters                        List encounters
GET /encounters/{encounter_id}         Get one encounter
GET /care-queue                        Return MEDIUM + HIGH risk queue
GET /care-queue/high                   Return only HIGH risk queue
PATCH /interventions/{encounter_id}    Update workflow status / owner / notes
GET /operations/summary                Operational metrics
GET /operations/readmission-analysis   Compare prioritization vs historical outcomes
GET /management/dashboard              Executive summary metrics

Example Workflow
Example intervention update:
PATCH /interventions/12345
{
"status": "CONTACTED",
"assigned_to": "Care Team A",
"notes": "Follow-up appointment scheduled"
}
Example operations summary:
{
"total_encounters": 10000,
"high_risk": 850,
"medium_risk": 2100,
"low_risk": 7050,
"pending_interventions": 640,
"completed_interventions": 210
}
Example readmission analysis:
{
"high_risk_patients": 850,
"high_risk_readmitted_under_30_days": 220,
"high_risk_readmission_rate": 25.88
}
Important
The numbers above are response-shape examples only. Your application must calculate metrics from the dataset and
database. Do not copy these sample values as results.

Acceptance Criteria
• Dataset can be loaded into PostgreSQL without manually inserting individual encounters.
• Risk score is calculated without using `readmitted`.
• MEDIUM and HIGH risk cases appear in the care queue.
• Intervention status can be updated and remains persisted after FastAPI restarts.
• Operational summary is calculated from stored data.
• Readmission analysis compares risk groups against historical `<30` outcomes.
• Routes return useful HTTP errors for missing encounter IDs.
• SQL is parameterized; no user-supplied values are concatenated into SQL strings.
• Code follows main / models / service / repository / database separation

w2day412Oct26_PSQL
│
├── main.py
├── models.py
├── service.py
├── repository.py
├── database.py
├── data_loader.py
├── schema.sql
├── seed_or_setup.sql
├── requirements.txt
├── .env.example
├── README.md
└── data/
└── <provided diabetes dataset>

Evaluation Rubric
Area Weight What Good Looks Like
FDE problem understanding 15% Clear user, decision, unknowns and MVP assumptions
Dataset ingestion / cleanup 10% Focused columns, repeatable loading, sensible missing-data handling
PostgreSQL design 15% Usable schema and persistence
Business / risk rules 15% Explainable, isolated in service layer, no leakage
FastAPI + layering 20% Clean API, repository separation, useful errors
Care-management workflow 10% Queue and intervention lifecycle work end-to-end
Operational metrics 10% Metrics are calculated from data, not hard-coded
README / demo quality 5% Easy to run and easy to explain

Stretch Goals
Filter care queue by minimum risk score.
• Add pagination to encounter APIs.
• Add summary by age band or utilization history.
• Add an intervention history table instead of overwriting the latest status.
• Add a CSV export endpoint for the care queue.
• Compare the simple rule against an alternative rule set and explain which is more useful operationally.