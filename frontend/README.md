# Academic Integrity Casework UI

The React frontend is an operational workspace for the FastAPI backend. It
supports submission registration and similarity analysis, case assignment and
status transitions, append-only evidence, decision recording, and independent
appeal review. It is not an analytics dashboard.

## Run locally

Start the backend API, then from this directory run:

```powershell
npm install
npm run dev
```

By default, the UI calls `http://localhost:8000/api/v1`. To use another API
address, set `VITE_API_BASE_URL`, for example in a local frontend `.env.local`:

```text
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

The backend must allow the frontend origin through CORS. API validation remains
authoritative: invalid state transitions, reviewer conflicts, duplicate flag
links, and appeal eligibility errors are returned to the user.
Submissions can be deleted from the Submissions list only before similarity
analysis or review records exist; linked reports and case history are preserved.

## Generated data tools

Open **Dataset tools** in the sidebar to download generated JSON, per-entity
CSVs, the SQL seed, and supporting documentation. Ground-truth exports are
available separately and are labeled as evaluation data; keep them out of
input features.

The local import preview accepts `backend/generated_data/data.json` and checks
table structure, primary-key uniqueness, and foreign-key references in the
browser. It does not upload records or persist them to a database. Generate the
files first from `backend/` with:

```powershell
python scripts\generate_synthetic_data.py
```

The export API is read-only: `GET /api/v1/datasets/generated` lists available
files and `GET /api/v1/datasets/generated/files/{filename}` downloads a
whitelisted export.

## Verify

```powershell
npm run build
npm run lint
```
