# Care management API

This project scores diabetes encounters for a care-management queue and provides
endpoints for tracking interventions and reviewing operational metrics.

## PostgreSQL setup

The database already has the `diabetic_patient` and `care_interventions` tables.
The application uses these tables as they are; it does not create or change
tables. Run `schema.sql` to check that the expected columns and table
relationships are present. Run `seed_or_setup.sql` to see the encounter, outcome,
and intervention counts.

`risk_score` and `risk_level` are calculated by the Python service when an
encounter is read. `readmitted` is used only for historical readmission analysis.

## Run the application

Create a virtual environment, install the listed packages, and copy
`.env.example` to `.env`. Set `DATABASE_URL` in `.env` to the connection URL for
the existing database. Keep `.env` out of version control.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn main:app --reload
```

The API documentation is available at `/docs`.

If you need to load the dataset, run the loader with the CSV file path. It
accepts the full dataset or a CSV containing the selected encounter columns.
Missing numeric values marked `?` are stored as `NULL`.

```powershell
python data_loader.py .\data\diabetic_data.csv
```

Loading uses `encounter_id` to update existing encounters. The CSV is not
included; provide the dataset file separately.

## Risk score

| Condition | Points |
| --- | ---: |
| `number_inpatient >= 3` | 3 |
| `number_emergency >= 2` | 2 |
| `number_outpatient >= 3` | 1 |
| `time_in_hospital >= 7` | 1 |
| `num_medications >= 20` | 1 |

A score of 0–2 is LOW, 3–4 is MEDIUM, and 5 or more is HIGH. These weights are
for the project exercise; they are not clinical recommendations. Missing
scoring values count as zero.

## API routes

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/encounters` | List scored encounters; supports `limit` and `offset` |
| POST | `/encounters` | Add an encounter; the API assigns the next `encounter_id` |
| GET | `/encounters/{encounter_id}` | Get one encounter |
| GET | `/patients/search` | Search by `patient_nbr`, `risk_level` and/or exact `risk_score` |
| GET | `/care-queue` | List MEDIUM- and HIGH-risk encounters |
| GET | `/care-queue/high` | List HIGH-risk encounters |
| GET | `/interventions/{encounter_id}` | List an encounter's intervention updates, newest first |
| PATCH | `/interventions/{encounter_id}` | Record an intervention update |
| GET | `/operations/summary` | Return risk and intervention counts |
| GET | `/operations/readmission-analysis` | Compare risk groups with historical outcomes |
| GET | `/management/dashboard` | Return the executive summary |

The care queue accepts a `min_risk_score` filter. The existing database limits
intervention statuses to `open`, `in_progress`, `completed`, and `cancelled`;
the API uses those values. Updates may include `status`, `assigned_to`, and
`notes`. Omitted fields are left unchanged.

Each PATCH adds a new `care_interventions` row instead of overwriting the old
one, so the full update history is kept. Fields that are not sent are copied
from the latest row. The row with the highest `intervention_id` is the current
status used by the care queue, search, and metrics.

`/patients/search` needs at least one filter and returns `total` plus one page
of `items` (`limit`, `offset`). Filters are combined with AND.

## Frontend screens

From `frontend/`, run `npm run build`, then `python -m http.server 5500`, and
open `http://127.0.0.1:5500/search.html`.

- `search.html`: search patients, and list HIGH-risk patients with their latest
  intervention status. Each Encounter ID opens the status screen.
- `status.html?encounter_id=...`: update status, owner, and notes; lists every
  update for the encounter.
- `index.html`: add an encounter.

Readmission rates use the known `<30`, `>30`, and `NO` outcomes as the
denominator. The metrics count encounters, not distinct patients.
