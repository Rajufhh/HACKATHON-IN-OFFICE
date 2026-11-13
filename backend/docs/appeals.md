# Appeals API

Appeals are separate records linked to an original case decision. Resolving an
appeal does not update the decision or its evidence snapshot.

## Rules and lifecycle

- One appeal may be submitted per original decision.
- The submitting learner must be the learner on the decision's case.
- An appeal moves from `SUBMITTED` to `UNDER_REVIEW` when assigned, then to
  `DECIDED` when resolved. A submitted appeal may instead be `WITHDRAWN`.
- The original decision-maker, inactive reviewers, reviewers assigned to the
  original case, reviewers with pending or confirmed conflicts, and reviewers
  at capacity cannot be assigned.
- Appeal outcomes are `UPHELD`, `OVERTURNED`, and `REMANDED`.
- Added evidence must belong to the original case. Appeal evidence links to the
  existing item and stores a snapshot of its code, title, and type.
- Important actions create append-only appeal events.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/appeals/` | Submit an appeal |
| `GET` | `/api/v1/appeals/` | List appeals; optional `status` query |
| `GET` | `/api/v1/appeals/{appeal_id}` | Get an appeal with events and evidence snapshots |
| `POST` | `/api/v1/appeals/{appeal_id}/assign` | Assign an independent reviewer |
| `POST` | `/api/v1/appeals/{appeal_id}/evidence` | Attach existing case evidence |
| `POST` | `/api/v1/appeals/{appeal_id}/resolve` | Record an appeal outcome |
| `POST` | `/api/v1/appeals/{appeal_id}/withdraw` | Withdraw a submitted appeal; takes `learner_id` as a query parameter |
| `GET` | `/api/v1/appeals/{appeal_id}/events` | Read appeal audit history |

### Submit an appeal

```json
{
  "decision_id": 12,
  "learner_id": 7,
  "grounds": "The original decision did not consider the supplied context.",
  "evidence_ids": [25]
}
```

### Assign an independent reviewer

```json
{
  "reviewer_id": 9,
  "actor_id": 2
}
```

### Resolve an appeal

```json
{
  "reviewer_id": 9,
  "outcome": "UPHELD",
  "rationale": "The independent review found the original decision supported."
}
```

Use `/docs` in the running FastAPI application to try the endpoints interactively.

## Test and table verification

Use the dedicated test database, not the development database. From
`C:\CandidateWorkspace\backend` in PowerShell:

```powershell
$env:DATABASE_URL = "mysql+pymysql://YOUR_USER:YOUR_PASSWORD@localhost:3306/academic_integrity_test"
python -m pytest tests\test_appeals.py -vv
python -m pytest -q
```

The application imports registered models and calls
`Base.metadata.create_all()` on startup. To create missing tables explicitly
against the configured test database:

```powershell
python -c "import app.models; from app.database.connection import Base, engine; Base.metadata.create_all(bind=engine)"
```

Then verify the table names in MySQL:

```sql
SHOW TABLES LIKE 'appeal%';
```

Expected: `appeals`, `appeal_events`, and `appeal_evidence`. `create_all()` does
not migrate existing tables; use a migration if a future model change alters
an already-created table.

## Security note

The current API accepts learner, reviewer, and actor IDs in request data. This
is not identity verification. Production deployments should derive those IDs
from authenticated principals and enforce role-based authorization.
