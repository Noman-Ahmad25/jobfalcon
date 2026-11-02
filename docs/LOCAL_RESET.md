# JobFalcon — Local Development Reset Procedure & Persistence Architecture

## 1. Database Location & Data Sources

JobFalcon uses SQLite for local single-user operations. The active database path is configured via `Settings.DATABASE_URL` (defaulting to `sqlite:///./jobfalcon_dev.db`).

- **Active SQLite Database**: `backend/jobfalcon_dev.db`  
  Path resolution: In `backend/app/db/connection.py`, `resolve_sqlite_path("sqlite:///./jobfalcon_dev.db")` computes the path relative to the backend project root, pointing directly to `/path/to/JobFalcon/backend/jobfalcon_dev.db`.
- **Stale Orphan Database**: `jobfalcon_dev.db` (in repository root)  
  An artifact from prior sessions with alternate working directories. This file is ignored by the backend runtime and can be safely deleted.

## 2. Seed Data Isolation & Gate

To prevent demo data from contaminating clean local user testing:
- Setting `SEED_DEMO_DATA: bool = False` (in `backend/app/core/config.py`) ensures that on startup, `seed_demo_data()` is **not executed**.
- Demo candidates (`maya-chen-junior`, `usr_cand_student_02`, `alex-rivera-fullstack`) will not be inserted into an empty database.
- If pre-populated demonstration profiles are needed for demo/benchmark testing, launch the backend with:
  ```bash
  SEED_DEMO_DATA=true uvicorn app.main:app --reload
  ```

## 3. Clean-State Reset Procedure

To completely reset the JobFalcon environment to a pristine first-time user state:

```bash
# 1. Stop any running backend or frontend processes (Ctrl+C)

# 2. Delete the active database and any orphan copies from project root:
rm -f backend/jobfalcon_dev.db
rm -f jobfalcon_dev.db

# 3. Start the backend:
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 4. In a separate terminal, start the frontend:
cd frontend
npm run dev
```

### Verification of Clean State:
1. `GET http://localhost:8000/api/v1/profile/` returns an empty array `[]`.
2. The frontend automatically detects zero profiles and displays the **First-Time User Onboarding Wizard**.
3. Completing onboarding calls `POST /api/v1/profile/create-structured`, persisting the user profile into `backend/jobfalcon_dev.db`.
4. Refreshing the browser or restarting the backend keeps the profile intact without reloading any demo candidates.
