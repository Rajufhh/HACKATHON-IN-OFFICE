# Academic Integrity Management System

This project supports an academic-integrity review workflow: submissions,
similarity analysis, flags, case assignment, evidence, decisions, and
independent appeals. A similarity flag requests human review; it is not itself
a finding of misconduct.

The backend is a FastAPI application in `backend/`. The React/TypeScript
workflow interface is in `frontend/`. Deterministic synthetic dataset
generation and exports are documented in
[`backend/generated_data/README.md`](./backend/generated_data/README.md).
The frontend's **Dataset tools** section downloads generated exports and
provides a browser-only `data.json` preview. Preview does not persist or send
records; ground-truth labels are shown separately from input data.

## Run locally

### Backend

From `backend/`, configure `DATABASE_URL` for a database intended for this
application, then start the API:

```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The API documentation is available at `/docs` while the server is running.

### Frontend

From `frontend/`:

```powershell
npm install
npm run dev
```

The UI defaults to `http://localhost:8000/api/v1`. See
[`frontend/README.md`](./frontend/README.md) for configuring another API URL.

## Testing results

Results recorded on **2026-11-13**:

| Area | Command | Result |
|---|---|---|
| Backend test suite (isolated temporary SQLite database) | `python -m pytest tests -q` | **123 passed** in 3.30s |
| Business-rule unit tests | `python -m pytest tests/test_business_rules_unit.py -q` | **24 passed** |
| Previous MySQL test-database run | `python -m pytest tests -q` | **89 passed** in 4.67s; one Starlette `httpx` deprecation warning |
| Frontend TypeScript and production build | `npm run build` | **Passed** |
| Frontend lint | `npm run lint` | **Blocked**: Windows Application Control prevented Oxlint's native binding from loading |
| Frontend unit tests | — | No frontend test script or test runner is currently configured |

The latest backend suite used a fresh temporary SQLite database and removed it
after testing; it did not touch the development database. The earlier MySQL run
used the dedicated `academic_integrity_test` database. The lint failure is an
environment restriction, not a reported lint result.
