# Pacfully Cost Estimator

Pacfully is a packaging estimation and quotation application for rigid boxes and related packaging components. It combines PDF specification extraction, a component/process matrix, formula-driven costing, estimate history, and customer-facing quotation and proforma PDFs.

The repository contains a React single-page application and a FastAPI service. Cost calculations run in the backend. The application can use SQLite locally and PostgreSQL through `DATABASE_URL` in deployment.

## Contents

- [Capabilities](#capabilities)
- [Technology](#technology)
- [Architecture](#architecture)
- [Repository layout](#repository-layout)
- [Requirements](#requirements)
- [Local setup](#local-setup)
- [Configuration](#configuration)
- [PDF extraction](#pdf-extraction)
- [Costing workflow](#costing-workflow)
- [API reference](#api-reference)
- [Data and persistence](#data-and-persistence)
- [Testing and build](#testing-and-build)
- [Deployment](#deployment)
- [Known limitations](#known-limitations)

## Capabilities

- Upload a PDF packaging layout and extract project fields, component specifications, process values, and drawing dimensions.
- Review source page, confidence, and confirmation state before using extracted values for costing.
- Route components to manufacturing processes in a shared process matrix.
- Calculate material and process costs with configurable formulas and rates, module breakdowns, and calculation traces.
- Save estimates, customers, quotations, proformas, configuration, and audit events.
- Generate quotation and proforma invoice PDFs.
- Manage users and roles; authenticate with email/password or optional Google sign-in.

Automatic extraction is currently for PDF files. Image uploads can be reviewed, but require manual entry of component and process values.

## Technology

| Area | Technology |
|---|---|
| Frontend | React, JavaScript/JSX, React Router, Vite |
| UI | Application CSS design system, Lucide icons, Recharts |
| API | Python, FastAPI, Pydantic |
| Persistence | SQLAlchemy; SQLite by default, PostgreSQL when configured |
| PDF text and geometry | PyMuPDF, Pillow, OpenCV |
| Scanned-page OCR | Tesseract executable and `pytesseract` |
| Optional visual fallback | Gemini API, enabled only when `GEMINI_API_KEY` is configured |
| Customer documents | ReportLab |
| Tests | pytest, FastAPI TestClient |
| Hosting configuration | Render backend blueprint and Vercel frontend rewrite |

Python dependencies are listed in [`backend/requirements.txt`](backend/requirements.txt); frontend dependencies and scripts are in [`frontend/package.json`](frontend/package.json). Dependency versions are managed by those manifests and the package manager lockfile, rather than all being pinned in this document.

## Architecture

```text
Browser (React + Vite)
  ├─ Public home and sign-in
  ├─ Protected estimator, estimates, customers, configuration, and documents
  └─ API service (fetch + Bearer token)
         │ HTTP / JSON
         ▼
FastAPI (/api)
  ├─ Authentication and role checks
  ├─ PDF extraction (PyMuPDF, OCR fallback, optional Vision fallback)
  ├─ Costing and formula evaluation
  ├─ Estimate, customer, quotation, and audit routes
  └─ ReportLab document generation
         │
         ├─ SQLAlchemy → SQLite or PostgreSQL
         └─ PDF files → data/pdfs by default (configurable with PDF_DIR)
```

The estimator has five stages: Layout & Component Extraction, Technical Data, Costing Modules, Summary & Margin, and Quotation / Proforma. Final costing is performed by the backend; the frontend provides inputs and displays returned results and traces.

## Repository layout

```text
.
├── backend/
│   ├── app.py                    # FastAPI app, CORS, startup, PDF static mount
│   ├── auth.py                   # Login, JWT, user roles and admin bootstrap
│   ├── database.py               # SQLAlchemy engine and database initialization
│   ├── models.py                 # Database models
│   ├── routes.py                 # API routes and costing orchestration
│   ├── component_process.py      # Shared process-to-module mapping
│   ├── formulas.py               # Formula definitions, validation and evaluation
│   ├── ai/layout_reader.py       # PDF text, table, OCR and geometry extraction
│   ├── costing/                  # Domain costing modules
│   ├── quotation/                # Quotation and proforma generation
│   ├── requirements.txt
│   └── apt.txt                   # Tesseract system package for Render
├── frontend/
│   ├── src/App.jsx               # Public and protected routes
│   ├── src/pages/                # Estimator and application pages
│   ├── src/components/           # Shared UI and process-matrix components
│   ├── src/services/api.js       # API requests
│   ├── package.json
│   ├── vite.config.js
│   └── vercel.json               # SPA route rewrite
├── data/
│   └── pdfs/                     # Generated PDFs by default
├── tests/                        # Backend and real-PDF regression tests
├── render.yaml                   # Render API blueprint
└── README.md
```

## Requirements

- Python 3.12 is the version used for local verification; use a compatible Python 3 version for the backend.
- Node.js and npm compatible with the Vite version installed from the frontend manifest.
- Tesseract OCR is optional for native-text PDFs, but required for scanned PDF pages where OCR is needed. The Python package alone does not install the Tesseract executable.
- Gemini credentials are optional; native extraction and local OCR do not require them.

## Local setup

Commands below use PowerShell from the repository root.

### 1. Configure the backend

Create a local `.env` file in the repository root. Set an administrator for the first local sign-in:

```env
INITIAL_ADMIN_EMAIL=admin@example.com
INITIAL_ADMIN_PASSWORD=use-a-unique-password-at-least-12-characters
INITIAL_ADMIN_NAME=Pacfully Administrator
```

Create the Python environment and install dependencies:

```powershell
py -3.12 -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install --upgrade pip
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
```

Start the API:

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

The API is at `http://127.0.0.1:8000`; interactive API documentation is at `http://127.0.0.1:8000/docs` and health is at `http://127.0.0.1:8000/api/health`.

### 2. Configure and start the frontend

In another terminal:

```powershell
Push-Location frontend
npm install
npm run dev
```

Vite serves the app at `http://localhost:5173` by default. If that port is occupied, Vite selects another available port. The default frontend API URL is `http://localhost:8000/api`; override it with `VITE_API_URL` when the backend is hosted elsewhere.

In local development, sign in with the administrator configured above. The administrator is seeded only when the users table is empty. Production deployments with `PUBLIC_APP_ACCESS=true` open directly to the dashboard; no built-in production credentials are provided.

### 3. Stop and restart

Stop each development server with `Ctrl+C`. Restart the backend and frontend after changing environment variables. The SQLite database and development signing key are stored under `data/` by default.

## Configuration

Backend variables are read from the repository-root `.env` file and/or the hosting environment. Do not commit secrets.

| Variable | Purpose |
|---|---|
| `ENVIRONMENT` | Set to `production` in production deployments. |
| `PUBLIC_APP_ACCESS` | Set to `true` to open the production workspace without login. Visitors can access operational customer, estimate, and quotation records and edit master rates. Formula edits, system settings, audit logs, and user management remain admin-only. |
| `SECRET_KEY` | JWT signing key; required in production. Development creates and persists a local key under `data/`. |
| `INITIAL_ADMIN_EMAIL` | Email for the first administrator when the users table is empty. Required on initial production startup. |
| `INITIAL_ADMIN_PASSWORD` | Initial administrator password; must be at least 12 characters. Required on initial production startup. |
| `INITIAL_ADMIN_NAME` | Optional name for the initial administrator. |
| `DATABASE_URL` | Optional SQLAlchemy database URL. Defaults to `data/pacfully.db` SQLite. PostgreSQL URLs are adapted to the psycopg driver. |
| `CORS_ORIGINS` | Comma-separated additional allowed browser origins. |
| `PDF_DIR` | Output directory for generated quotation and proforma PDFs. Defaults to `data/pdfs`. |
| `GOOGLE_CLIENT_ID` | Optional backend Google ID-token verification client ID. |
| `TESSERACT_CMD` | Optional full path to the Tesseract executable if it is not on `PATH`. |
| `GEMINI_API_KEY` | Optional API key for the final Vision fallback. No Vision request is made when unset. |
| `GEMINI_MODEL` | Optional Gemini model; defaults to `gemini-2.5-flash`. |

Frontend variables belong in `frontend/.env` or the frontend hosting environment:

```env
VITE_API_URL=http://localhost:8000/api
VITE_GOOGLE_CLIENT_ID=your-google-oauth-web-client-id
```

For Google sign-in, use the same client ID in the frontend and backend and add the frontend origin to the OAuth client's authorized JavaScript origins.

## PDF extraction

The protected `POST /api/layout/extract` endpoint accepts PDF files up to 20 MB and returns JSON. It does not create an estimate or write costing results to the database.

1. PyMuPDF reads native PDF text, page count, text positions, tables, vectors, and embedded images.
2. Label parsing extracts project fields and component specifications. Sheet sizes are normalized to millimetres when a unit is stated; quantity and finished box dimensions are normalized when unambiguous.
3. Drawing dimensions and page geometry are reported as evidence. Dimensions are not assigned to a component without a reliable relationship in the source.
4. OpenCV prepares scanned pages for OCR. Tesseract runs when native text is absent or incomplete and available locally.
5. Gemini Vision is an optional final fallback. Vision-only process values remain confirmation-required and do not automatically activate costing routes.
6. Extracted fields include raw and normalized values where available, source, page, confidence, and review status. Treat confidence as an extraction indicator, not a calibrated probability.

Explicit process values map to `YES`, `NO`, or `REVIEW`: YES routes a component, NO excludes it, and missing/ambiguous data remains for user confirmation. Component headings such as Base Material, Wrapper, and Inserts may identify the corresponding section route. Always review these routes and any inferred/default costing inputs before quoting.

## Costing workflow

The process matrix controls which components enter each module. Supported module routes include Kappa/Base Material, Wrapper, Insert, Printing, Lamination, Punching/Die Cutting, Glue, Embellishments, Accessories, Conversion, EB, and One Time Cost.

- Each module calculation uses the estimate quantity, shared module inputs, component-specific overrides, configured formulas, and effective rates.
- Printing, Lamination, and Wrapper-material Punching depend on a current Wrapper final-sheet result. Calculate Wrapper first when calculating those modules individually; Calculate All handles the overall estimate flow.
- Module output includes totals, cost per box, applicable component rows, and calculation traces. Configuration gaps are returned separately.
- Rates and production assumptions come from saved master configuration, form defaults, or estimate overrides; they are not automatically extracted from a layout PDF.
- Conversion has supported configured paths for selected materials/methods. Unsupported combinations report configuration-required. EB may require configuration before it can be costed.
- Unconfirmed source values (for example, a material sheet size with no unit) must be resolved before a complete estimate can be calculated.

Common formula relationships include:

```text
Base sheets     = CEILING(order quantity / UPS)
Wastage sheets  = CEILING(base sheets * wastage percent / 100)
Final sheets    = base sheets + wastage sheets + make-ready, when applicable
Cost per box    = module total cost / order quantity
Selling price   = cost per box / (1 - margin percent / 100)
Order value     = selling price per box * order quantity
```

The active formula set is stored in `formula_configuration` and can be inspected or updated through the formula configuration API. Formula evaluation and validation live in `backend/formulas.py` and are used by the backend costing routes.

## API reference

Base path: `/api`. The interactive OpenAPI documentation is available at `/docs`.

### Health and layout

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | API health check |
| `POST` | `/api/layout/extract` | Extract fields and geometry from a PDF upload |

### Authentication and users

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/auth/login` | Email/password login; returns a Bearer token |
| `POST` | `/api/auth/google` | Google ID-token sign-in |
| `GET` | `/api/auth/me` | Current user profile |
| `GET` | `/api/auth/users` | List users (admin access) |
| `POST` | `/api/auth/users` | Create user (admin access) |
| `PUT` | `/api/auth/users/{user_id}` | Update user (admin access) |
| `DELETE` | `/api/auth/users/{user_id}` | Delete/deactivate user (admin access) |
| `POST` | `/api/auth/change-password` | Change current user's password |

### Estimation and configuration

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/estimates/calculate` | Calculate an estimate without saving it |
| `POST` | `/api/estimates/calculate/module` | Calculate a single module |
| `GET` | `/api/estimates` | List saved estimates |
| `POST` | `/api/estimates` | Save an estimate draft |
| `GET` | `/api/estimates/{estimate_id}` | Read an estimate and related records |
| `POST` | `/api/estimates/{estimate_id}/finalize` | Finalize an estimate |
| `DELETE` | `/api/estimates/{estimate_id}` | Delete an eligible non-finalized estimate |
| `GET`, `PUT` | `/api/master-config` | Read or update master rates |
| `GET`, `PUT` | `/api/formulas` | Read or update calculation formulas |
| `GET`, `PUT` | `/api/settings` | Read or update system settings |

### Customers, quotations, and audit

| Method | Path | Purpose |
|---|---|---|
| `GET`, `POST` | `/api/customers` | List or create customers |
| `GET`, `DELETE` | `/api/customers/{customer_id}` | Read or deactivate a customer |
| `GET`, `POST` | `/api/quotations` | List or create quotation/proforma documents |
| `GET` | `/api/quotations/next-number` | Get the next document number |
| `GET`, `PUT`, `DELETE` | `/api/quotations/{quotation_id}` | Read, update, or delete a quotation |
| `POST` | `/api/quotations/preview` | Generate a PDF preview without creating a saved document |
| `GET` | `/api/quotations/{quotation_id}/pdf` | Stream the generated PDF |
| `GET` | `/api/audit-log` | Read audit events |
| `GET` | `/pdfs/{filename}` | Serve a generated PDF from `PDF_DIR` |

Most API calls require a Bearer access token. Configuration and user management endpoints have role checks; see the route dependencies in `backend/routes.py` and `backend/auth.py` for exact authorization requirements.

## Data and persistence

SQLAlchemy models are defined in `backend/models.py`:

- `User`: account, role, activation, and last-login state.
- `Customer`: customer contact and business details.
- `Estimate`: status, summary values, customer/job identity, and input snapshot.
- `CostLine`: module totals, weightage, trace, and status.
- `Quotation`: quotation/proforma values and generated PDF path.
- `AuditEvent`: recorded actions and changes.
- `MasterConfiguration`, `FormulaConfiguration`, `SystemSettings`: persistent configuration.

Local SQLite defaults to `data/pacfully.db`. Set `DATABASE_URL` to use PostgreSQL. Generated PDFs default to `data/pdfs`; local files may be ephemeral on hosted services unless a persistent disk or external storage is configured. Finalized estimates preserve a snapshot of their inputs and costing results.

## Testing and build

From the repository root in PowerShell:

```powershell
backend\.venv\Scripts\python.exe -m pytest tests -q
Push-Location frontend
npm run build
Pop-Location
```

Tests cover formula evaluation, component/process routing, PDF field extraction, OCR/Vision fallback behavior, geometry, API extraction, and estimate calculations. Real reference PDFs in the repository are used when available; tests for absent local PDF fixtures are skipped.

## Deployment

### Vercel frontend and Render API

The repository provides `frontend/vercel.json` for SPA route rewrites and `render.yaml` for the API service. A typical deployment uses:

1. Deploy `backend/` to Render using the blueprint. Configure a PostgreSQL database and set `DATABASE_URL` to its connection URL.
2. Set `INITIAL_ADMIN_EMAIL`, `INITIAL_ADMIN_PASSWORD` (at least 12 characters), and optionally `INITIAL_ADMIN_NAME` before the first production startup. Set `CORS_ORIGINS` to the exact frontend origin.
3. Deploy `frontend/` to Vercel with project root `frontend`, build command `npm run build`, and output directory `dist`.
4. Set `VITE_API_URL=https://<render-service>.onrender.com/api` in Vercel. If using Google sign-in, configure the same OAuth client ID in `VITE_GOOGLE_CLIENT_ID` and backend `GOOGLE_CLIENT_ID`.
5. Configure a persistent Render disk and `PDF_DIR` if generated PDFs must survive service restarts and deploys.

Production requires `ENVIRONMENT=production` and a configured `SECRET_KEY`. Do not put credentials, signing keys, or database passwords in source control.

## Known limitations

- Only PDF uploads receive automatic field extraction. Image uploads need manual entry.
- OCR requires an installed Tesseract executable; `pytesseract` alone is not the executable.
- Vision extraction is optional and was not exercised unless a Gemini key is configured.
- Geometry values are reported but are not automatically mapped to component dimensions without a reliable relationship.
- PDF statements may omit critical units, process routes, finish/method, or costing assumptions. Such values require human confirmation; a calculated partial total is not quote-ready.
- Master rates and production settings are configuration inputs, not PDF-extracted facts. Review them before sending a quote.
- The dashboard includes presentation/demo metrics in places where live database aggregation has not been implemented.
- Conversion is supported only for configured material/method combinations; EB may require additional configuration.

## License

Proprietary — Pacfully Packaging Pvt Ltd. All rights reserved.