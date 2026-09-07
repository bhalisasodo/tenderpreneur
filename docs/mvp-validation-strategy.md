# Tenderpreneur — MVP Validation Strategy

**Document Status:** Approved Product Strategy & MVP Constraints  
**Source Baseline:** `docs/product-validation-principles.md` & `docs/source/concept-c-build-brief.md`  

---

## 1. Core Product Hypothesis

The foundational hypothesis of Tenderpreneur is:

> **If tender contractors are provided an AI-assisted tool to rapidly parse raw BoQs and request structured quotes from regional suppliers with visible deadlines, they will achieve a defensible, submission-ready priced BoQ significantly faster than manual phone/email outreach, creating atomic transaction records that power long-term procurement pricing intelligence.**

The BoQ parser is merely the *top-of-funnel entry point*; the defensible supplier sourcing and decision audit trail is the core value proposition.

---

## 2. Primary User

- **Persona:** General Contractor Estimator / Commercial Manager / SME Tenderer.
- **Context:** South African contractors bidding for public infrastructure, municipal tenders, or commercial projects under strict tender submission deadlines (typically 7–21 days).
- **Environment:** Desktop/laptop web browser, juggling unstructured PDF/Excel tender schedules with disparate supplier quote WhatsApps, PDFs, and rate books.

---

## 3. Primary Job-to-be-Done (JTBD)

> *"When I receive a 50+ item tender Bill of Quantities with 5 days until submission deadline, I want to extract the line items, send structured RFQs to regional suppliers, and compile defensible prices with clear evidence, so that I can submit a competitive, audited tender on time without arithmetic errors or unverified guesswork."*

---

## 4. MVP Success Criterion

The single benchmark defining MVP success is:

> **"Can ONE contractor upload ONE real BoQ and receive a defensible priced BoQ before their tender deadline?"**

**Secondary validation question:**
> *"Can real suppliers respond to specific quote requests quickly enough on their mobile phones to make the contractor's workflow materially better?"*

We strictly do not optimize prematurely for thousands of users, multi-country expansions, or autonomous agents before proving this single atomic loop.

---

## 5. Contractor Workflow (Phases A & B)

```
[Upload BoQ / Scope Text] 
         │
         ▼
[AI Parsing + SA Benchmark Ranges]
         │
         ▼
[Manual Review & Field Correction] ◄── Contractor retains 100% authority
         │
         ├───► [Internal Plant / Negotiated Price Override + Mandatory Reason]
         │
         ▼
[Select Items & Broadcast Quote Requests] ◄── Response deadline countdown visible
         │
         ▼
[Side-by-Side Quote Comparison Matrix] (Lowest Price vs Fastest Lead Time)
         │
         ▼
[Select Winning Quote / Override Price]
         │
         ▼
[Export Submission-Ready Priced BoQ] (Excel .xlsx + PDF + Immutable Audit Trail)
```

---

## 6. Supplier Workflow (Mobile-First)

```
[Receive WhatsApp/Email Notification] ("New RFQ: 75m3 Ready-Mix Concrete — Due in 22h")
         │
         ▼
[Open Direct Submission URL on Mobile] (No password wall required for direct link)
         │
         ▼
[Review Item Description, Quantity, Unit, Tender Province]
         │
         ▼
[Enter Unit Price (ZAR) + Lead Time (Days) + Terms]
         │
         ▼
[Instant Submit Before Server-Enforced Deadline]
```

---

## 7. Critical Assumptions

1. **Format Tolerance:** Real contractor BoQs vary wildly (scanned PDFs, messy Excel grids, pasted WhatsApp specs). The system must extract usable candidates and let the contractor fix inaccuracies without starting over.
2. **Speed Over Scale:** A small network of 5–10 responsive suppliers in a single region (e.g. KwaZulu-Natal / Gauteng) is sufficient to prove value.
3. **Deadline Gravity:** Contractors will prioritize responsive suppliers if deadline countdowns and turnaround times are front-and-center.
4. **Audit Defensibility:** Public and commercial tender boards scrutinize price realism; retaining supplier quote references and manual override reasons gives contractors submission confidence.

---

## 8. Biggest Risks & Mitigations

| Risk | Impact | Mitigation Strategy |
|---|---|---|
| **AI Hallucination / Parse Error** | Contractor loses trust or quotes inaccurate quantities. | **Rule:** AI is an assistant, never the financial authority. Every line item field (description, quantity, unit, category) is directly editable in place before sourcing. |
| **Supplier Cold Start / Low Response** | Contractor broadcasts RFQ but receives no responses before deadline. | **Human-in-the-loop / Operator intervention:** System alerts operators if an RFQ is unanswered within 12h. Contractor can fallback to manual price overrides. |
| **Premature Architectural Complexity** | Project bogged down in microservices, distributed queues, or complex auth. | **Modular Monolith:** FastAPI backend + Next.js frontend with clear domain boundaries and zero-dependency local adapters. |
| **Missed Tender Deadlines** | Severe financial/reputational harm to contractor. | Strict countdown indicators in UI, deadline-expired status, and explicit server-side deadline enforcement (`DEADLINE_EXPIRED`). |

---

## 9. Manual Operations We Can Tolerate Initially

During MVP validation, manual operational assistance ("Wizard of Oz" support) is explicitly encouraged:
1. **BoQ Review Support:** An operator may inspect extracted line items to assist a contractor during onboarding.
2. **Supplier Concierge:** An operator may manually WhatsApp or call registered suppliers to encourage timely quote submissions.
3. **Catalog & Category Alignment:** Operators can manually assign or refine trade categories and supplier tags.
4. **Offline Override Assistance:** If a supplier submits a price via PDF email, the contractor (or operator) can input it as an audited price override with a reference note.

---

## 10. MVP Acceptance Criteria (The 6 Product Experiments)

The test suite and live validation must prove these 6 acceptance experiments:

- [x] **Experiment 1 (BoQ Ingestion):** Can a real BoQ document (PDF/Excel/text) be uploaded and structured into line items?
- [x] **Experiment 2 (Frictionless Correction):** Can a contractor correct parsing mistakes (quantity, unit, description) directly in the UI without losing data?
- [x] **Experiment 3 (RFQ Generation):** Can selected line items be converted into broadcasted quote requests with explicit response windows?
- [x] **Experiment 4 (Mobile Supplier Quote):** Can a supplier receive an alert and submit a unit price and lead time from a mobile viewport before the deadline?
- [x] **Experiment 5 (Quote Comparison):** Can a contractor compare quotes side-by-side with clear badges for Lowest Price and Fastest Delivery and select a winner?
- [x] **Experiment 6 (Defensible Export):** Can Tenderpreneur generate an Excel workbook (`.xlsx` with priced BoQ + audit sheet) and PDF tender schedule documenting all quote sources and override reasons?

---

## 11. What is Explicitly Out of Scope (Anti-Scope)

To prevent scope creep and maintain MVP discipline, the following are **strictly excluded**:
- ❌ Automated scraping of public government tender portals.
- ❌ Automated CSD (Central Supplier Database), CIDB, or B-BBEE government API integrations (captured as self-declared profile metadata only).
- ❌ Automated transaction take-rate billing, commission calculation, or payment gateway processing.
- ❌ Complex algorithmic supplier reputation scoring.
- ❌ AI-based tender win-probability estimation.
- ❌ Enterprise ERP / SAP / BIM integrations.
- ❌ Multi-country currency conversions (MVP is strictly South African ZAR in minor cents).
- ❌ Distributed microservice deployments.

---

## 12. Validation Telemetry & Core Metrics

The application captures immutable audit events ([`AuditEvent`](file:///C:/Users/bhali/tenderpreneur/apps/api/app/core/models.py)) to measure:

1. `boq.created` & `boq.parsed`: Time from document upload to structured candidate review.
2. `line_item.edited`: Frequency of manual corrections (identifies parser accuracy bottlenecks).
3. `quote_request.created` & `quote_request.broadcast`: Number of items externally sourced per tender.
4. `quote.submitted`: Supplier turnaround time (hours between broadcast and submission).
5. `quote.selected` vs `line_item.price_overridden`: Ratio of direct supplier quotes selected vs manual overrides.
6. `export.generated`: Final conversion metric representing a tender successfully priced on time.
