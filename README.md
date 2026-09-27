# Pacfully — Packaging Cost Intelligence Platform

> **PACKAGING ENGINEERED** · Full-stack B2B packaging cost estimation, cost intelligence and quotation generation platform for luxury rigid boxes, with architecture prepared for Monocartons and Corrugated packaging.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Tech Stack](#2-tech-stack)
3. [Architecture Diagram](#3-architecture-diagram)
4. [Project Structure](#4-project-structure)
5. [Database Schema](#5-database-schema)
6. [Costing Engine — How It Works](#6-costing-engine--how-it-works)
7. [API Endpoints Reference](#7-api-endpoints-reference)
8. [Frontend Pages & Features](#8-frontend-pages--features)
9. [PDF Generation](#9-pdf-generation)
10. [Calculation Formulas](#10-calculation-formulas)
11. [Getting Started](#11-getting-started)
12. [Environment Variables](#12-environment-variables)
13. [Specification Notes](#13-specification-notes)

---

## 1. Project Overview

Pacfully is a **B2B Packaging Cost Estimation and Cost Intelligence Platform** designed for packaging manufacturers. It allows estimators to:

- Upload a packaging layout (PDF, PNG, JPG, JPEG)
- Run **AI-assisted extraction** of packaging technical data (dimensions, materials, GSM, structure type, printing, lamination, etc.)
- Review and confirm extracted values in a **5-step structured workflow**
- Run a **deterministic, formula-driven costing engine** across 10 modules
- Inspect **human-readable calculation traces** showing every derived value and formula
- Apply **Master Default → Estimate Override → Effective Value** hierarchy for every rate
- Finalize estimates as **immutable historical snapshots**
- Generate **customer-facing Quotation and Proforma Invoice PDFs** (excluding internal manufacturing cost, rates and margin)
- Track all activity through a **complete Audit Log**
- Visualize cost intelligence through **dashboards, charts and module breakdowns**

---

## 2. Tech Stack

### Frontend

| Layer | Technology | Version |
|---|---|---|
| Framework | React | 18.x |
| Language | JavaScript (JSX) | ES2022+ |
| Build Tool | Vite | 8.x |
| Routing | React Router DOM | 6.x |
| Charts | Recharts | 2.x |
| Icons | Lucide React | Latest |
| Styling | Custom CSS (design system) | — |
| Typography | Inter (body) + Manrope (headings/numbers) | Google Fonts |
| HTTP Client | Native fetch API | — |

### Backend

| Layer | Technology | Version |
|---|---|---|
| Framework | FastAPI | Latest |
| Language | Python | 3.12 |
| ORM | SQLAlchemy | 2.x |
| Database | SQLite | 3.x |
| PDF Generation | ReportLab | Latest |
| Server | Uvicorn (ASGI) | Latest |
| Validation | Pydantic v2 | Latest |
| Runtime Manager | uv | Latest |
| PDF/Image (future) | PyMuPDF + Pillow | — |

### Infrastructure

| Component | Technology |
|---|---|
| Package Manager (Python) | uv + .venv |
| Package Manager (Node) | npm |
| Database File | SQLite (`data/pacfully.db`) |
| PDF Storage | Local filesystem (`data/pdfs/`) |
| Configuration | `.env` + `pydantic-settings` |

---

## 3. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         BROWSER (React SPA)                             │
│                                                                         │
│  ┌──────────┐  ┌──────────────────────────────────────────────────────┐ │
│  │  Public  │  │              App Shell (Sidebar + Navbar)            │ │
│  │  Pages   │  │                                                      │ │
│  │          │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │ │
│  │  Home    │  │  │Dashboard │ │Estimator │ │Estimates │ │Reports │ │ │
│  │  Login   │  │  │          │ │(5 Steps) │ │          │ │        │ │ │
│  └──────────┘  │  └──────────┘ └──────────┘ └──────────┘ └────────┘ │ │
│                │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │ │
│                │  │Customers │ │Quotations│ │ Proforma │ │ Audit  │ │ │
│                │  │          │ │PDF Modal │ │PDF Modal │ │  Log   │ │ │
│                │  └──────────┘ └──────────┘ └──────────┘ └────────┘ │ │
│                │                                                      │ │
│                │         services/api.js  (fetch wrapper)            │ │
│                └──────────────────────────────────────────────────────┘ │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │  HTTP / JSON  (port 8000)
                                 │  CORS: localhost:5173 / 5174
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend (Python 3.12)                      │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                         routes.py                               │   │
│  │                                                                 │   │
│  │  GET  /api/health                                               │   │
│  │  POST /api/estimates/calculate   ← stateless costing engine     │   │
│  │  GET  /api/customers             POST /api/customers            │   │
│  │  GET  /api/customers/:id         DELETE /api/customers/:id      │   │
│  │  GET  /api/estimates             POST /api/estimates            │   │
│  │  GET  /api/estimates/:id                                        │   │
│  │  POST /api/estimates/:id/finalize                               │   │
│  │  DELETE /api/estimates/:id                                      │   │
│  │  GET  /api/quotations            POST /api/quotations           │   │
│  │  GET  /api/quotations/:id        DELETE /api/quotations/:id     │   │
│  │  GET  /api/quotations/:id/pdf    ← ReportLab PDF stream         │   │
│  │  GET  /api/audit-log                                            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│            │                        │                                   │
│            ▼                        ▼                                   │
│  ┌──────────────────┐    ┌──────────────────────┐                       │
│  │  Costing Engine  │    │  PDF Generator        │                       │
│  │  (_run_calculation)│  │  (quotation/          │                       │
│  │                  │    │   pdf_generator.py)   │                       │
│  │  10 modules:     │    │                       │                       │
│  │  Kappa,Wrapper,  │    │  generate_quotation_  │                       │
│  │  Printing,       │    │  pdf()                │                       │
│  │  Lamination,     │    │  generate_proforma_   │                       │
│  │  Glue,Punching,  │    │  pdf()                │                       │
│  │  Embellishments, │    │                       │                       │
│  │  Accessories,    │    │  ReportLab → A4 PDF   │                       │
│  │  Conversion,EB   │    │  → data/pdfs/*.pdf    │                       │
│  └──────────────────┘    └──────────────────────┘                       │
│            │                                                             │
│            ▼                                                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    SQLAlchemy ORM Layer                          │   │
│  │           database.py  ←→  models.py                            │   │
│  └──────────────────────────────┬──────────────────────────────────┘   │
│                                 │                                        │
└─────────────────────────────────┼────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        SQLite  (data/pacfully.db)                       │
│                                                                         │
│  customers │ estimates │ cost_lines │ quotations │ audit_events        │
└─────────────────────────────────────────────────────────────────────────┘
```

### Request Flow — Cost Estimator (5-Step Workflow)

```
User                   Frontend                   Backend                SQLite
 │                        │                          │                      │
 │── Fill form ──────────>│                          │                      │
 │                        │── POST /estimates/calculate ──────────────────>│X (stateless)
 │                        │<── JSON result ──────────│                      │
 │                        │                          │                      │
 │── Save Draft ─────────>│── POST /estimates ───────>────────────────────>│ INSERT estimate
 │                        │                          │── INSERT cost_lines─>│ INSERT cost_lines
 │                        │                          │── INSERT audit_event>│ INSERT audit
 │                        │<── {estimate_id, number}─│                      │
 │                        │                          │                      │
 │── Save & Finalize ────>│── POST /estimates/:id/finalize ─────────────>  │ UPDATE status
 │                        │── POST /quotations ──────>── generate PDF ────>│ INSERT quotation
 │                        │                          │── INSERT audit_event>│
 │                        │<── {quotation_id, has_pdf}│                     │
 │                        │                          │                      │
 │── Preview PDF ────────>│── GET /quotations/:id/pdf────────────────────> │ SELECT quotation
 │<── iframe PDF ─────────│<── FileResponse (.pdf)───│                      │
```

---

## 4. Project Structure

```
pacfully-cost-estimator/
│
├── .env                          # Backend environment variables
│
├── backend/
│   ├── .venv/                    # Python virtual environment (uv-managed)
│   ├── app.py                    # FastAPI entry point, CORS, startup, static files
│   ├── routes.py                 # All API routes + costing engine
│   ├── database.py               # SQLAlchemy engine, SessionLocal, Base, init_db()
│   ├── models.py                 # ORM models: Customer, Estimate, CostLine, Quotation, AuditEvent
│   ├── requirements.txt          # Python dependencies, including google-auth
│   ├── ai/
│   │   └── layout_reader.py      # AI layout extraction (future)
│   ├── costing/                  # Domain module stubs (logic lives in routes.py)
│   │   ├── kappa.py
│   │   ├── wrapper.py
│   │   ├── printing.py
│   │   ├── lamination.py
│   │   ├── glue.py
│   │   ├── punching.py
│   │   ├── embellishments.py
│   │   ├── accessories.py
│   │   ├── conversion.py
│   │   ├── eb.py
│   │   └── insert.py
│   └── quotation/
│       ├── __init__.py
│       └── pdf_generator.py      # ReportLab PDF: generate_quotation_pdf(), generate_proforma_pdf()
│
├── frontend/
│   ├── .env                      # VITE_API_URL + VITE_GOOGLE_CLIENT_ID
│   ├── index.html                # HTML shell with Inter + Manrope Google Fonts
│   ├── vite.config.js            # Vite config, proxy, code splitting
│   ├── package.json
│   └── src/
│       ├── main.jsx              # React entry: BrowserRouter + App
│       ├── App.jsx               # Router: PublicLayout / AppLayout + all Routes
│       ├── index.css             # Full design system (CSS custom properties, no Tailwind)
│       ├── services/
│       │   └── api.js            # All API helper functions (fetch wrappers)
│       ├── components/
│       │   ├── BrandLogo.jsx     # Shared Pacfully wordmark component
│       │   ├── Sidebar.jsx       # Fixed sidebar with NavLinks, workspace badge
│       │   ├── Navbar.jsx        # Top bar: active search, notifications, profile menu
│       │   └── CostCard.jsx      # Shared: MetricCard, StatusPill, RateConfigRow,
│       │                         # CalcTracePanel, PageHeader, Stepper, money()
│       ├── pages/
│       │   ├── Home.jsx          # Landing/marketing page
│       │   ├── Login.jsx         # Split-screen login with verified Google SSO
│       │   ├── Dashboard.jsx     # Cost Intelligence overview and interactive filters
│       │   ├── CostEstimator.jsx # 5-step estimator workflow (main feature)
│       │   ├── Estimates.jsx     # Estimates list + live CRUD
│       │   ├── Customers.jsx     # Customer list + Add modal + live CRUD
│       │   ├── Reports.jsx       # Analytics: bar/line/pie charts
│       │   ├── Quotations.jsx    # Quotations list + PDF preview modal
│       │   ├── Proforma.jsx      # Proforma list + PDF preview modal
│       │   ├── MasterConfig.jsx  # Editable rate tables
│       │   ├── Settings.jsx      # Company profile, tax, numbering
│       │   ├── Users.jsx         # Users & Roles management
│       │   └── AuditLog.jsx      # Complete audit trail, live from DB
│       └── modules/              # Costing module stubs (future)
│
└── data/
    ├── pacfully.db               # SQLite database
    └── pdfs/                     # Generated PDF files
```

---

## 5. Database Schema

```sql
-- Customers
CREATE TABLE customers (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    contact     TEXT,
    email       TEXT,
    phone       TEXT,
    address     TEXT,
    city        TEXT,
    state       TEXT,
    gst_number  TEXT,
    created_at  DATETIME,
    updated_at  DATETIME,
    is_active   BOOLEAN DEFAULT TRUE
);

-- Estimates (one per cost calculation job)
CREATE TABLE estimates (
    id                       INTEGER PRIMARY KEY,
    estimate_number          TEXT UNIQUE,        -- EST-00001
    customer_id              INTEGER FK→customers,
    customer_name            TEXT,               -- denormalized for fast list queries
    job_name                 TEXT,
    status                   TEXT,               -- Draft | Quoted | Finalized
    created_by               TEXT,
    created_at               DATETIME,
    updated_at               DATETIME,
    finalized_at             DATETIME,
    input_snapshot           JSON,               -- complete EstimateInput at finalization
    order_quantity           INTEGER,
    total_manufacturing_cost FLOAT,
    cost_per_box             FLOAT,
    margin_percent           FLOAT,
    selling_price_per_box    FLOAT,
    order_value              FLOAT
);

-- CostLines (one row per costing module per estimate)
CREATE TABLE cost_lines (
    id            INTEGER PRIMARY KEY,
    estimate_id   INTEGER FK→estimates,
    module        TEXT,            -- Kappa | Wrapper | Printing | …
    total_cost    FLOAT,
    cost_per_box  FLOAT,
    weightage_pct FLOAT,
    trace         JSON,            -- [{label, value}, …] human-readable trace
    status        TEXT             -- OK | CONFIGURATION REQUIRED
);

-- Quotations (Quotation or Proforma Invoice)
CREATE TABLE quotations (
    id               INTEGER PRIMARY KEY,
    quotation_number TEXT UNIQUE,   -- QUO-2026-09-0001 | PI-2026-09-0001
    estimate_id      INTEGER FK→estimates,
    doc_type         TEXT,          -- Quotation | Proforma Invoice
    customer_name    TEXT,
    customer_address TEXT,
    job_name         TEXT,
    order_quantity   INTEGER,
    unit_price       FLOAT,         -- selling price per box
    subtotal         FLOAT,
    gst_percent      FLOAT,
    gst_amount       FLOAT,
    grand_total      FLOAT,
    validity_days    INTEGER,
    notes            TEXT,
    pdf_path         TEXT,          -- absolute path to generated PDF
    created_at       DATETIME,
    status           TEXT           -- Draft | Sent | Accepted
);

-- AuditEvents (append-only, immutable)
CREATE TABLE audit_events (
    id          INTEGER PRIMARY KEY,
    estimate_id INTEGER FK→estimates,
    user        TEXT,
    action      TEXT,               -- "Estimate Created", "Quotation Generated", …
    entity_type TEXT,               -- estimate | quotation | customer | config
    entity_id   TEXT,               -- EST-00001 | QUO-2026-09-0001
    detail      TEXT,
    old_value   TEXT,
    new_value   TEXT,
    timestamp   DATETIME
);
```

---

## 6. Costing Engine — How It Works

The engine is a **pure deterministic function** (`_run_calculation` in `routes.py`) — no database reads or writes, just math. It takes a full `EstimateInput` payload and returns a complete result with per-module cost lines, calculation traces and weightage percentages.

### Rate Hierarchy

```
Layout Value  →  Master Default  →  Estimate Override  →  Effective Value
```

- **Layout Value**: extracted from the uploaded packaging dieline (AI extraction)
- **Master Default**: stored in the rate tables in `routes.py` (and in future, in `MasterConfig` DB)
- **Estimate Override**: set per-estimate by the estimator (displayed in orange in the UI)
- **Effective Value**: what the engine actually uses — the rightmost non-null value wins

### Calculation Trace

Every module returns a `trace` array — a list of `{label, value}` pairs showing:
- All input values used
- All derived intermediate values
- The final formula applied

This trace is stored in the `cost_lines.trace` JSON column and displayed in the UI as **"How was this calculated?"**

---

## 7. API Endpoints Reference

### Health

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Service health check |

### Costing Engine

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/estimates/calculate` | Stateless calculation — no DB write |

### Customers

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/customers` | List all active customers |
| `POST` | `/api/customers` | Create a new customer |
| `GET` | `/api/customers/:id` | Get customer + estimate history |
| `DELETE` | `/api/customers/:id` | Soft-delete (deactivate) a customer |

### Estimates

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/estimates` | List all estimates (newest first) |
| `POST` | `/api/estimates` | Calculate + persist as Draft |
| `GET` | `/api/estimates/:id` | Get estimate + cost lines + quotations |
| `POST` | `/api/estimates/:id/finalize` | Mark as Finalized (immutable) |
| `DELETE` | `/api/estimates/:id` | Delete Draft/Quoted (Finalized protected) |

### Quotations & PDFs

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/quotations` | List all quotation documents |
| `POST` | `/api/quotations` | Create quotation/proforma + generate PDF |
| `GET` | `/api/quotations/:id` | Get single quotation |
| `GET` | `/api/quotations/:id/pdf` | Stream PDF (inline preview or download) |
| `DELETE` | `/api/quotations/:id` | Delete quotation |

### Audit Log

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/audit-log` | List all audit events (newest first, max 500) |

### Static Files

| Method | Path | Description |
|---|---|---|
| `GET` | `/pdfs/:filename` | Serve generated PDF files directly |

> **Swagger UI**: http://localhost:8000/docs

---

## 8. Frontend Pages & Features

### Public Pages (no sidebar)

| Page | Route | Description |
|---|---|---|
| **Home** | `/` | Marketing landing page — hero, features, stats, CTA |
| **Login** | `/login` | Password login plus Google Identity Services; verified Google emails are persisted in the users table |

### App Pages (with sidebar + topbar)

| Page | Route | Live API | Description |
|---|---|---|---|
| **Dashboard** | `/dashboard` | Partial | Metric cards, charts, recent estimates table, interactive date-range calendar, Monthly/Quarterly/Weekly chart selector, and quick actions |
| **Cost Estimator** | `/estimator/new` | ✅ | 5-step workflow: Layout Upload → Technical Data → Costing Modules → Summary & Margin → Quotation/Proforma |
| **Estimates** | `/estimates` | ✅ | Filterable list, finalize/delete buttons, live from DB |
| **Estimate Detail** | `/estimates/:id` | ✅ | Immutable snapshot view |
| **Customers** | `/customers` | ✅ | List + Add modal, deactivate button, live from DB |
| **Customer Detail** | `/customers/:id` | ✅ | Profile + estimate history |
| **Reports** | `/reports` | — | Bar, line, pie charts — analytics dashboard |
| **Master Config** | `/master-config` | — | Editable rate tables for materials and processes |
| **Quotations** | `/quotations` | ✅ | List + PDF preview modal (iframe) + download |
| **Proforma** | `/proforma` | ✅ | Proforma Invoice list + PDF preview + download |
| **Settings** | `/settings` | — | Company profile, tax, document numbering |
| **Users & Roles** | `/users` | — | Admin/Estimator/Viewer management |
| **Audit Log** | `/audit-log` | ✅ | Live audit trail from DB, searchable |

### Shared App Actions

- The supplied Pacfully wordmark is used across the landing page, login page, sidebar, estimator preview, and footer.
- The sidebar **Help Centre** button opens `https://pacfully.com/` in a new tab.
- The top-bar search routes searches to Estimates, Customers, Quotations, or Reports based on the entered terms.
- The notification bell opens a panel with a link to the Audit Log.
- The profile chip opens Account Settings and Sign out actions.

### Data Status

Estimates, customers, quotations, audit events, and authenticated users are stored through the FastAPI/SQLite backend. The dashboard metric cards, chart series, module percentages, and recent-estimate preview are currently presentation/demo values in `Dashboard.jsx`; the dashboard controls change the displayed view and date range but do not yet query aggregated dashboard data from the database.

### Cost Estimator — 5-Step Workflow

```
Step 1: Layout & AI Extraction
  → Upload PDF/PNG/JPG/JPEG packaging dieline
  → Simulated AI extraction progress animation
  → Dieline SVG preview with detected dimensions
  → Extraction confidence score per field

Step 2: Technical Data Review
  → Table of 12 extracted fields with confidence %
  → "Confirmed" / "Confirmation Required" status pills
  → Layout thumbnail preview
  → Notes field for manual corrections

Step 3: Costing Modules
  → Tab-based navigation across 10 modules
  → Each module shows: input fields, Rate Config row
    (Master Rate | Estimate Override | Effective Rate | Reset to Master)
  → Calculate All Modules button → POST /estimates/calculate
  → Per-module: Total Cost, Cost/Box, Weightage %
  → "How was this calculated?" trace panel
  → Conversion and EB show CONFIGURATION REQUIRED

Step 4: Summary & Margin
  → Module cost table with weightage
  → Donut chart of module allocation
  → Dark panel: Mfg Cost/Box, Margin %, Selling Price/Box, Order Value
  → Margin is editable

Step 5: Quotation / Proforma
  → Select: Quotation or Proforma Invoice
  → Live preview panel (document number, bill-to, line items, GST total)
  → Save & Finalize → POST /estimates → POST /estimates/:id/finalize → POST /quotations
  → Redirects to /estimates after save
```

---

## 9. PDF Generation

PDFs are generated server-side using **ReportLab** and stored in `data/pdfs/`.

### Quotation PDF contains:
- Pacfully logo / brand header (orange accent)
- Document type + number + date
- Bill To: customer name and address
- Document Details: quotation number, date, validity
- Line items: description, quantity, unit price, subtotal
- Totals: subtotal + GST + grand total (orange)
- Terms & Conditions
- Footer note: *Internal manufacturing cost and margin are intentionally excluded*

### Proforma Invoice PDF additionally contains:
- "PROFORMA INVOICE" heading
- Bank Details section (Bank, Account No., IFSC, Branch)
- Due date instead of validity date

### PDF Access

```
# Inline preview (used in iframe)
GET http://localhost:8000/api/quotations/:id/pdf

# Direct file
GET http://localhost:8000/pdfs/QUO-2026-09-0001.pdf
```

PDFs are regenerated on-demand if the file is missing.

---

## 10. Calculation Formulas

### Kappa (Rigid Board)

```
Effective GSM   = GSM@1mm × Thickness(mm)
Area (m²)       = Sheet_L(mm) × Sheet_W(mm) ÷ 1,000,000
KG per Sheet    = Area(m²) × Effective_GSM ÷ 1,000
Base Sheets     = CEILING(Quantity ÷ UPS)
Wastage Sheets  = CEILING(Base_Sheets × Wastage% ÷ 100)
Final Sheets    = Base_Sheets + Wastage_Sheets
Total KG        = Final_Sheets × KG_per_Sheet
Total Cost      = Total_KG × Rate(₹/kg)
Cost per Box    = Total_Cost ÷ Quantity
```

### Wrapper (Art Paper / Cover)

```
KG per Sheet    = Sheet_L(mm) × Sheet_W(mm) × GSM ÷ 1,000,000,000
Base Sheets     = CEILING(Quantity ÷ UPS)
Wastage Sheets  = CEILING(Base_Sheets × Wastage% ÷ 100)
Final Sheets    = Base_Sheets + Wastage_Sheets + Make-ready(default 150)
Total KG        = Final_Sheets × KG_per_Sheet
Total Cost      = Total_KG × Rate(₹/kg)
Cost per Box    = Total_Cost ÷ Quantity

Note: Final_Sheets is consumed directly by Printing, Lamination and Punching.
```

### Printing

```
Tier            = 15×20 | 20×28 | 28×40
If sheets ≤ 1000:  Total = First_1000_Rate
If sheets > 1000:  Total = First_1000_Rate + (Sheets − 1000) × Additional_Rate_per_Sheet

Default rates:
  15×20 → ₹1,500 + ₹0.40/sheet
  20×28 → ₹3,500 + ₹0.50/sheet
  28×40 → ₹6,500 + ₹0.80/sheet
```

### Lamination

```
Cost per Sheet  = L(in) × W(in) × Rate ÷ 100
Total Cost      = Cost_per_Sheet × Final_Wrapper_Sheets
Cost per Box    = Total_Cost ÷ Quantity

Default rates (per 100 sq.in):
  Thermal → ₹1.10 | Cold → ₹0.70 | Dry → ₹0.80
```

### Glue

```
Weight per Box  = Σ (Area(sq.in) × 0.00064516 × GSM ÷ 1000)  per component
Total Cost      = Weight_per_Box × Rate(₹/kg) × Quantity
Cost per Box    = Total_Cost ÷ Quantity

Note: 0.00064516 converts sq.in to m²
```

### Punching

```
Production Hrs  = Quantity ÷ Speed(sheets/hr)
Total Cost      = (Production_Hrs + Setup_Hrs) × Machine_Rate(₹/hr)
Cost per Box    = Total_Cost ÷ Quantity

Default speeds:
  Kappa/FBB/Duplex → 600 sh/hr | Wrapper → 600 sh/hr | Foam/EVA/EPE → 500 sh/hr
```

### Embellishments (Foiling, Spot UV, Embossing, etc.)

```
Raw Cost        = Area(sq.in) × Rate(₹/sq.in) + Setup(₹)
Applied Cost    = MAX(Raw_Cost, Minimum_Charge)
Cost per Box    = Applied_Cost ÷ Quantity
```

### Accessories (Magnet, Ribbon, Window Film, etc.)

```
Total Cost      = Σ (Quantity_per_Box × Unit_Cost) × Order_Quantity
Cost per Box    = Total_Cost ÷ Quantity
```

### Margin & Selling Price

```
Selling Price/Box = Cost/Box ÷ (1 − Margin%)
Order Value       = Selling_Price/Box × Quantity
```

### Modules marked CONFIGURATION REQUIRED

- **Conversion** (Machine + Labour + Setup) — formula not finalised
- **EB** (Extended Billing) — method not defined

These always return ₹0 until the formula is confirmed and configured.

---

## 11. Getting Started

### Prerequisites

- Python 3.12 with `uv` installed
- Node.js 18+ with npm

### 1. Clone and set up backend

```bash
cd backend

# Dependencies are already installed in .venv via uv
# If running fresh, install them:
uv pip install -r requirements.txt

# Verify
.venv/Scripts/python.exe -c "import fastapi, sqlalchemy, reportlab; print('OK')"
```

### 2. Start the backend

```bash
cd backend
.venv/Scripts/uvicorn.exe app:app --host 0.0.0.0 --port 8000 --reload
```

Backend starts at **http://localhost:8000**
Swagger UI at **http://localhost:8000/docs**

The database tables are created automatically on first startup via `init_db()`.

### 3. Set up and start the frontend

```bash
cd frontend
npm install       # only needed first time
npm run dev
```

Frontend starts at **http://localhost:5173** (or 5174 if 5173 is busy)

### 4. Open the app

```
http://localhost:5173
```

Click **Get Started** → Login with a seeded email/password account or use **Sign in with Google** → Dashboard. Google sign-in requires the OAuth environment variables described below.

---

### Production Build

```bash
cd frontend
npm run build
# Output in frontend/dist/ — serve with any static file server
```

---

## 12. Environment Variables

### Frontend (`frontend/.env`)

```env
VITE_API_URL=http://localhost:8000/api
VITE_GOOGLE_CLIENT_ID=your-google-oauth-client-id
```

### Root (`.env`)

```env
VITE_API_URL=http://localhost:8000/api
GOOGLE_CLIENT_ID=your-google-oauth-client-id
```

Create a Google OAuth 2.0 Web application client and add your frontend origin (for local development, `http://localhost:5173`) to its authorized JavaScript origins. Use the same client ID for both variables. The backend verifies Google's ID token, then creates or updates the user by verified email and records the last login. New Google users are assigned the Estimator role.

For local development, authorize both `http://localhost:5173` and `http://127.0.0.1:5173` if you use both URLs. The backend also loads the root `.env` file through `python-dotenv`; restart both servers after changing environment variables.

For production, set both variables in their respective environments, update `VITE_API_URL` to your deployed API domain, and rebuild the frontend.

---

## 13. Specification Notes

### Separation of Concerns

| Layer | Responsibility |
|---|---|
| Frontend | UI rendering, form state, navigation, display |
| API Routes | Input validation, orchestration, DB persistence, audit |
| Costing Engine | Pure deterministic math — zero DB side effects |
| PDF Generator | Document layout and formatting only |
| Database | Persistence, history, immutable snapshots |

**Financial calculations are never performed in frontend code.**

### Immutable Finalized Estimates

Once an estimate is finalized:
- Status is permanently set to `Finalized`
- `finalized_at` timestamp is recorded
- The full `input_snapshot` (all inputs) is stored as JSON
- All module `cost_lines` with traces are stored
- The estimate **cannot be deleted** (returns HTTP 400)
- Later changes to master rates do NOT affect historical estimates

### Quotation vs Proforma

| Feature | Quotation | Proforma Invoice |
|---|---|---|
| Document number | `QUO-YYYY-MM-NNNN` | `PI-YYYY-MM-NNNN` |
| Contains | Unit price + GST + Total | Unit price + GST + Grand Total + Bank Details |
| Excludes | Mfg cost, module breakdown, internal rates, margin | Same |
| Use case | Initial pricing communication | Formal advance payment request |

### Future Packaging Types

The Master → Override → Effective Value → Cost Engine → Cost Intelligence → Documents framework is designed to be extended for:
- **Monocartons** (FBB, SBS, Duplex)
- **Corrugated** (E-flute, B-flute, etc.)
- **Rigid with Insert** (EVA, EPE, Foam)

Each type plugs into the same pipeline without changing the core engine architecture.

### Database Portability

The SQLite setup can be migrated to **PostgreSQL** without changing any business logic — only the `DATABASE_URL` in `database.py` needs to change:

```python
# SQLite (current)
DATABASE_URL = f"sqlite:///{DB_PATH}"

# PostgreSQL (production)
DATABASE_URL = "postgresql://user:pass@host/pacfully"
```

---

## License

Proprietary — Pacfully Packaging Pvt Ltd. All rights reserved.

---

*Built with precision. Packaging Engineered.*
