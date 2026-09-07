# Tenderpreneur MVP Implementation Plan

**Date:** 2026-09-01  
**Status:** Active Implementation Blueprint (Milestones 1–4 Built & Verified)  
**Product:** Tenderpreneur (AI-native BoQ Pricing & Supplier-Quote Marketplace)  
**Authoritative Brief:** `docs/source/concept-c-build-brief.md`, `docs/product-spec.md`, & `docs/mvp-validation-strategy.md`

---

## 1. Executive Summary & Architecture Validation

### 1.1 Source Brief Alignment
We have validated the repository scaffold against the original build brief (*Concept C / Tenderpreneur*) and the MVP Validation Strategy. The core value proposition is preserved without compromise:

$$\text{Upload BoQ/Scope} \longrightarrow \text{Structured Parsing} \longrightarrow \text{Manual Correction} \longrightarrow \text{Supplier Marketplace Loop} \longrightarrow \text{Quote Comparison} \longrightarrow \text{Audit-Ready Export}$$

### 1.2 Scope Boundary Verification
- **MVP Scope (Implemented & Tested):**
  - Multi-tenant data model (Contractor & Supplier organisations with strict server-side scoping).
  - Document ingestion (PDF, Excel, pasted text) with pluggable LLM parsing behind `LLMProvider`.
  - Full manual editability of every parsed field (descriptions, units, quantities, categories, benchmark hints).
  - Supplier onboarding & profile management (categories, service regions, contact methods, compliance flags).
  - Deterministic category + region supplier matching and quote-request broadcasting.
  - Mobile-first supplier quote submission portal with strict response-window/deadline enforcement.
  - Contractor quote comparison dashboard (lowest, fastest, preferred quotes).
  - Quote selection and manual price overrides with mandatory audit reasoning.
  - Append-only immutable audit trail (`AuditEvent`).
  - Submission-ready PDF & Excel BoQ exports with quote references, supplier attribution, and timestamps.
- **Phase 2 Deferred Scope (Strictly Excluded from MVP):**
  - Scraping/purchased historical rate databases (MVP uses simple baseline heuristics / null benchmarks).
  - Automated CSD/CIDB/B-BBEE third-party government verification APIs.
  - Supplier reputation / win-rate algorithms (only submission timestamps and delivery logs are captured).
  - Monetisation / billing / take-rate processing / SaaS subscriptions.
  - Concept E integrations or multi-currency bulk imports.

### 1.3 Conflict Analysis: Original Source Brief vs. MVP Constraints

| Topic | Original Source Brief Mentions | MVP Constraint Resolution |
|---|---|---|
| **Marketplace Scale** | Two-sided marketplace across multiple construction trades. | **Narrow Focus:** Initial launch supports controlled trade categories (`building-materials`, `concrete`, `roofing`, `earthworks`) and single regions (e.g. KwaZulu-Natal / Gauteng) to validate the core loop before category expansion. |
| **Microservices vs Monolith** | Logical service boundaries (BoQ Service, Matching Service, Quote Service, Export Service). | **Modular Monolith:** Kept within a single FastAPI application with internal domain modularity (`app/domains/*`) to ensure high development velocity, testability, and zero infrastructure overhead. |
| **Supplier Compliance** | CIDB ratings, CSD verification, and B-BBEE certificates. | **Self-Declared Profile Metadata:** Stored as structured supplier profile fields without building fragile third-party scrapers or automated verification APIs in the MVP. |
| **Marketplace Automation** | Fully automated RFQ routing. | **Operator Tolerance:** The system allows operator-assisted matching, concierge follow-ups, and manual price overrides to validate real user behavior before introducing complex automation. |

---

## 2. Technical Ambiguities & Resolved Decisions

| Area | Scaffolding / Brief Observation | Technical Resolution |
|---|---|---|
| **Local Runtime Environment** | Docker is not installed in the local host environment; PostgreSQL & MinIO containers cannot run locally without setup. | Support dual database drivers: `postgresql+psycopg` for production and `sqlite+aiosqlite` for instant zero-dependency local development and test automation. Provide a `LocalStorageProvider` alongside `S3StorageProvider`. |
| **Monetary Representation** | Scaffolding references mixed price formats. | Standardize strictly on integer cents (`price_minor`, e.g., `125000` = `R1,250.00`) and ISO 4217 currency code (`ZAR`) across database columns, API request/response DTOs, and calculation logic. |
| **Parsing Safety & LLM Hallucinations** | LLM parsing cannot be trusted as authoritative financial truth. | Implement a 2-stage parsing pipeline: (1) Deterministic document text/table extractor (PDF/Excel/text), (2) LLM structured schema extractor returning validated Pydantic models with confidence scores (0.0 to 1.0). Every field is editable in the UI before quote sourcing. |
| **Multi-Tenancy Scoping** | Contractor and Supplier organisations must be completely isolated. | Every API route validates JWT/Bearer session token and injects tenant context (`CurrentTenant`). Database queries are filtered by organisation ID at the repository/service layer. |
| **Supplier Quote Deadlines** | Quote requests have explicit response windows (e.g. 24h/48h). | Store `response_deadline` as UTC timestamp on `QuoteRequest`. Enforce deadline validation server-side on quote submission; return `DEADLINE_EXPIRED` (422) if submitted after window closes. Provide live visual countdowns on the frontend. |
| **Audit Logging** | Procurement challenge defense requires non-repudiable audit trails. | All price modifications (quote selection, manual override, parsing edits) emit immutable `AuditEvent` rows within the active database transaction. |

---

## 3. Final Tech Stack Choices

### 3.1 Backend (`apps/api`)
- **Runtime:** Python 3.13+
- **Framework:** FastAPI (high-performance async web framework, OpenAPI schema generation)
- **Validation & Settings:** Pydantic v2 & `pydantic-settings`
- **Database & ORM:** SQLAlchemy 2.0 (async session support with `lazy="selectin"` relationship loading)
- **Database Engine:** PostgreSQL 17 (production) / SQLite with `aiosqlite` (zero-config local dev & fast pytest suite)
- **Document Processing:** `pypdf`, `openpyxl`, `python-multipart`
- **Export Engines:** `openpyxl` (Excel), `reportlab` (PDF generation)
- **Testing:** `pytest`, `pytest-asyncio`, `httpx`

### 3.2 Frontend (`apps/web`)
- **Framework:** Next.js 15 (App Router, Server & Client Components)
- **Language:** TypeScript 5+ (strict mode enabled)
- **Styling & UI:** Tailwind CSS, Lucide React icons
- **Package Manager:** npm (v10.9.3)
- **State & Fetching:** React Hooks with typed API client

### 3.3 Storage & External Adapters
- **Storage:** `LocalStorageProvider` (local `./storage` directory) + `S3StorageProvider` (MinIO/AWS S3)
- **LLM Provider:** `StubLLMProvider` (deterministic pattern/heuristic parser with SA rate benchmarks) + extensible OpenAI/Gemini adapters
- **Notification Provider:** `ConsoleNotificationProvider` (local dev & tests) + extensible SMS/WhatsApp adapters

---

## 4. Directory & Module Map

```text
tenderpreneur/
├── .agents/                      # AI rules, agent definitions, skills & workflows
├── apps/
│   ├── api/                      # FastAPI Backend
│   │   ├── app/
│   │   │   ├── core/             # App configuration, security, database session, models
│   │   │   │   ├── config.py
│   │   │   │   ├── database.py
│   │   │   │   ├── models.py     # 10 core SQLAlchemy models
│   │   │   │   └── security.py   # JWT & tenant authentication
│   │   │   ├── domains/          # Domain business modules
│   │   │   │   ├── auth/         # Tenancy, users, sessions & tokens
│   │   │   │   ├── boq/          # BoQ document metadata & line-item lifecycle
│   │   │   │   ├── parsing/      # Document ingestion & LLM normalization
│   │   │   │   ├── suppliers/    # Supplier profiles, category/region catalogs
│   │   │   │   ├── matching/     # Category + region deterministic supplier matcher
│   │   │   │   ├── quotes/       # Quote requests, broadcast, submissions, deadlines, selection
│   │   │   │   ├── audit/        # Append-only audit logging & event queries
│   │   │   │   └── exports/      # PDF & Excel priced BoQ export generation
│   │   │   ├── integrations/     # Provider adapter implementations
│   │   │   │   ├── storage/      # LocalStorageProvider
│   │   │   │   ├── llm/          # StubLLMProvider
│   │   │   │   ├── notifications/# ConsoleNotificationProvider
│   │   │   │   └── exports/      # StandardExportRenderer
│   │   │   ├── schemas/          # API Request/Response DTOs
│   │   │   ├── seed.py           # Database seeder with sample contractors, suppliers, and BoQs
│   │   │   └── main.py           # FastAPI entrypoint & router registrations
│   │   ├── tests/                # 47 Automated tests (100% passing)
│   │   │   ├── conftest.py       # Fixtures, test client, test DB setup
│   │   │   ├── test_auth.py
│   │   │   ├── test_boq_parsing.py
│   │   │   ├── test_matching.py
│   │   │   ├── test_quotes.py
│   │   │   ├── test_audit.py
│   │   │   ├── test_exports.py
│   │   │   └── test_e2e_journey.py # Complete contractor-to-supplier-to-export flow
│   │   └── pyproject.toml
│   │
│   └── web/                      # Next.js Frontend
│       ├── app/
│       │   ├── layout.tsx        # Root layout
│       │   ├── page.tsx          # Landing & demo persona switcher
│       │   ├── contractor/       # Contractor Portal
│       │   │   ├── layout.tsx    # Contractor portal shell
│       │   │   ├── page.tsx      # Contractor BoQ list & metrics
│       │   │   └── boqs/
│       │   │       ├── new/page.tsx          # Upload document & parse BoQ
│       │   │       └── [boqId]/
│       │   │           ├── review/page.tsx   # Line-item editor & sourcing broadcast
│       │   │           ├── quotes/page.tsx   # Quote comparison & selection matrix
│       │   │           └── export/page.tsx   # Priced BoQ & audit trail export
│       │   └── supplier/         # Supplier Portal (Mobile-First)
│       │       ├── layout.tsx    # Mobile-optimized shell
│       │       ├── page.tsx      # Active quote requests inbox
│       │       ├── profile/page.tsx          # Categories & regions configuration
│       │       └── quote-requests/
│       │           └── [requestId]/page.tsx  # Mobile quote submission form with countdown
│       ├── lib/                  # Utilities, API client, currency formatters
│       │   ├── api.ts            # Typed fetch wrapper against backend API
│       │   └── formatters.ts     # ZAR currency formatting (minor cents to Rands), dates
│       ├── package.json
│       ├── tailwind.config.ts
│       └── tsconfig.json
│
└── docs/                         # Specification and architecture docs
```

---

## 5. Implementation Status of Milestones

### Milestone 1 — Foundation (Backend & Frontend Scaffold)
- [x] Architecture & plan validation against source brief & MVP validation strategy.
- [x] Implemented `apps/api/app/core` (config, database engine with SQLite & PostgreSQL support, models, error handlers).
- [x] Implemented `apps/api/app/domains/auth` with tenant context and 1-click persona switcher endpoints.
- [x] Implemented database seed script (`apps/api/app/seed.py`) with realistic South African contractors and suppliers.
- [x] Set up `apps/web` with Tailwind CSS, layout shells, and shared API client.
- [x] Verified `/health` and baseline auth endpoints with automated tests.

### Milestone 2 — BoQ Document Ingestion & Parsing
- [x] Implemented `ObjectStorageProvider` (`LocalStorageProvider`).
- [x] Implemented `POST /boqs` and `POST /boqs/{id}/documents` (PDF/Excel/text upload).
- [x] Implemented `LLMProvider` abstraction with `StubLLMProvider` (heuristic parsing + SA rate guide benchmarks).
- [x] Implemented parsing pipeline `POST /boqs/{id}/parse` with structured Pydantic schema validation.
- [x] Implemented `PATCH /boqs/{id}/line-items/{itemId}` for manual line-item correction.
- [x] Built Contractor UI: BoQ upload page and inline line-item review & edit modal.
- [x] Verified with integration and parsing validation tests.

### Milestone 3 — Supplier Marketplace & Sourcing Loop
- [x] Implemented `POST /suppliers/profile` and `GET /suppliers/profile` for category/region management.
- [x] Implemented `MatchingService` (`category` + `service_region` deterministic supplier lookup).
- [x] Implemented `POST /quote-requests` (create request for line items with response window).
- [x] Implemented `POST /quote-requests/{id}/broadcast` (delivery logging + notification trigger).
- [x] Implemented `GET /suppliers/quote-requests` (supplier inbox filtered by supplier organisation).
- [x] Implemented `POST /quote-requests/{id}/quotes` with strict server-side deadline validation.
- [x] Built Supplier UI: Mobile-first quote request inbox and mobile quote submission form with live countdown timer.
- [x] Verified with marketplace lifecycle unit and integration tests.

### Milestone 4 — Comparison, Overrides & Audit-Ready Export
- [x] Implemented `GET /boqs/{id}/quote-comparison` (per-line-item summary: lowest, fastest, selected supplier).
- [x] Implemented `POST /quote-requests/{id}/select` (select winning quote -> updates line item `final_price` -> logs `AuditEvent`).
- [x] Implemented `POST /boqs/{id}/line-items/{itemId}/price-override` (manual price override with mandatory reason -> logs `AuditEvent`).
- [x] Implemented `GET /boqs/{id}/audit` (inspectable event trail).
- [x] Implemented `StandardExportRenderer` (`openpyxl` for formatted Excel with quote evidence tab; `reportlab` for clean PDF tender schedule).
- [x] Implemented `POST /boqs/{id}/exports` and `GET /exports/{id}/download`.
- [x] Built Contractor UI: Quote comparison matrix, price override modal, audit timeline, and export triggers.
- [x] Built End-to-End Test (`test_e2e_journey.py`, `test_mvp_verification_loop.py`, `test_boq_ingestion_stress.py`, `test_production_readiness.py`, `test_safety_gate_and_extraction.py`) verifying the complete lifecycle and production hardening (54/54 automated tests passing, 100%).

---

## 6. Testing Strategy & Validation Experiments

The test suite systematically proves the 6 Core MVP Validation Experiments:

| Experiment | Focus Area | Verification Test | Status |
|---|---|---|---|
| **Experiment 1** | BoQ Ingestion & Parsing | `tests/test_boq_parsing.py::test_parse_boq_pasted_text` | **PASSED** |
| **Experiment 2** | Frictionless Field Correction | `tests/test_boq_parsing.py::test_create_boq_and_manual_line_item` | **PASSED** |
| **Experiment 3** | RFQ Generation & Broadcast | `tests/test_quotes.py::test_quote_flow_and_server_deadline_enforcement` | **PASSED** |
| **Experiment 4** | Mobile Supplier Quote & Deadlines | `tests/test_quotes.py::test_deadline_expired_rejection` | **PASSED** |
| **Experiment 5** | Quote Comparison & Selection | `tests/test_quotes.py::test_quote_flow_and_server_deadline_enforcement` | **PASSED** |
| **Experiment 6** | Defensible Priced BoQ & Audit Trail | `tests/test_exports.py` & `tests/test_audit.py` & `tests/test_e2e_journey.py` | **PASSED** |
