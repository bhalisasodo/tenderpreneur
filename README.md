# Tenderpreneur

AI-native Bill of Quantities (BoQ) pricing and verified supplier-quote marketplace for South African tender contractors.

> Built from the Tenderpreneur / Concept C source brief dated 24 August 2026.

---

## Core Product Value

$$\text{Upload BoQ/Scope} \longrightarrow \text{Structured Parsing} \longrightarrow \text{Supplier Sourcing Loop} \longrightarrow \text{Quote Comparison} \longrightarrow \text{Audit-Ready Export}$$

1. **Document Ingestion & AI Parsing:** Contractors upload PDF, Excel, or paste scope text. The system extracts structured line items (descriptions, units, quantities, trade categories, and SA rate guide benchmark ranges).
2. **Manual Correction:** Every parsed field is editable.
3. **Supplier Matching & Broadcast:** Deterministic matching by trade category + province/region with explicit countdown response windows (e.g. 24h / 48h).
4. **Mobile-First Supplier Submissions:** Suppliers receive instant notification alerts and submit item rates and turnaround times from mobile-friendly forms with server-side deadline enforcement.
5. **Quote Comparison Matrix:** Side-by-side contractor view highlighting lowest price and fastest delivery, with 1-click quote selection or manual price overrides with mandatory audit justification.
6. **Audit-Ready Exports:** Generates submission-ready Excel (`.xlsx` with embedded audit sheet) and PDF schedules with quote references and timestamps.

---

## Quickstart (Local Zero-Config Run)

### 1. Start Backend API (`apps/api`)
```bash
cd apps/api
# Uses Python 3.13 venv
.venv\Scripts\activate          # Windows (.venv/bin/activate on Linux/Mac)
uvicorn app.main:app --reload --port 8000
```
- API Docs & Swagger UI: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`
- The database is automatically initialized and seeded with demo contractors and suppliers on first launch.

### 2. Start Frontend Web App (`apps/web`)
```bash
cd apps/web
npm run dev
```
- Open `http://localhost:3000` in your browser.
- Toggle between Contractor and Supplier personas via the interactive demo switcher.

---

## Running the Automated Test Suite

To run all backend unit, integration, and end-to-end user journey tests:
```bash
cd apps/api
.venv\Scripts\pytest -v
```

To run the complete automated 13-step procurement loop validation scenario:
```bash
python scripts/verify_mvp_loop.py
```

To run the BoQ ingestion stress-testing suite (100 items, dirty Excel, GCC clauses, OCR glyph repairs):
```bash
python scripts/run_boq_stress_tests.py
```

---

## Production Cloud Deployment

For deploying to a cloud VPS (Hetzner, AWS, DigitalOcean, Azure) with automated SSL/TLS (Caddy), PostgreSQL 17, MinIO, and Alembic migrations:
- Follow the step-by-step guide in [`docs/production-deployment-guide.md`](docs/production-deployment-guide.md).
- Configuration template: [`infra/docker/.env.production.example`](infra/docker/.env.production.example).
- Automated deployment script: [`infra/docker/deploy.sh`](infra/docker/deploy.sh).

---

## Architecture & Codebase Map

```text
tenderpreneur/
├── apps/
│   ├── api/                      # FastAPI Python Backend
│   │   ├── app/
│   │   │   ├── core/             # Config, database, models, security, base exception handlers
│   │   │   ├── domains/          # Domain business modules
│   │   │   │   ├── auth/         # Token issuing & multi-tenant isolation
│   │   │   │   ├── boq/          # BoQ metadata, document upload, line-item CRUD
│   │   │   │   ├── parsing/      # PDF/Excel/Text extraction & LLM schema structuring
│   │   │   │   ├── suppliers/    # Supplier profiles, trade categories & regions
│   │   │   │   ├── matching/     # Deterministic category + region supplier matcher
│   │   │   │   ├── quotes/       # Quote requests, delivery logs, submissions, deadlines, selection
│   │   │   │   ├── audit/        # Append-only audit trail
│   │   │   │   └── exports/      # PDF & Excel priced BoQ export generation
│   │   │   ├── integrations/     # Pluggable provider adapters (Storage, LLM, Notifications, Export)
│   │   │   ├── schemas/          # Pydantic v2 API DTOs
│   │   │   ├── seed.py           # Demo contractor, supplier, and BoQ seeder
│   │   │   └── main.py           # FastAPI application entrypoint
│   │   └── tests/                # Complete pytest test suite (47/47 tests)
│   │
│   └── web/                      # Next.js 15 App Router Frontend
│       ├── app/
│       │   ├── page.tsx          # Landing & interactive demo persona switcher
│       │   ├── contractor/       # Contractor Portal (BoQs, Upload, Review, Quotes, Export)
│       │   └── supplier/         # Mobile-First Supplier Portal (Requests inbox, Quote submission, Profile)
│       └── lib/
│           ├── api.ts            # Typed API client
│           └── formatters.ts     # ZAR currency (cents to Rands) & deadline formatters
├── docs/                         # Specifications, data model, security, and implementation plan
└── AGENTS.md                     # Agent core instructions
```
