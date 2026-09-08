# BOQPRO — PRODUCT VALIDATION & MVP DISCIPLINE

Now that you have completed the initial review of the repository and the ANTIGRAVITY_START_PROMPT.md instructions, I want to establish an important product-development constraint before you begin substantial implementation.

The goal is NOT to build the largest or most technically sophisticated version of Tenderpreneur.

The goal is to prove that the core Tenderpreneur business loop works with real users and real tender pricing workflows.

Treat the following as product principles that constrain your implementation decisions.

==================================================
1. THE CORE PRODUCT THESIS
==================================================

Tenderpreneur is not fundamentally an "AI BoQ parser."

The parser is the entry point.

The longer-term product thesis is:

Tender
→ BoQ
→ Structured line items
→ Supplier demand
→ Supplier quotes
→ Price comparison
→ Final priced BoQ
→ Accumulated pricing intelligence

The eventual strategic opportunity is to become a pricing/procurement intelligence layer for tendering.

However, DO NOT build that future vision now.

Build only the smallest product that can validate the first part of this loop.

==================================================
2. MVP SUCCESS CRITERION
==================================================

Use this as the primary definition of MVP success:

"Can one contractor upload one real BoQ and receive a defensible priced BoQ before their tender deadline?"

The architecture, database, APIs and UI should all serve this question.

A secondary validation question is:

"Can real suppliers respond to specific quote requests quickly enough to make the contractor's workflow materially better?"

Do not optimize prematurely for:
- thousands of users
- thousands of suppliers
- sophisticated recommendation engines
- enterprise procurement functionality
- complex analytics
- elaborate supplier reputation systems
- automated compliance verification
- billing
- multi-country expansion

==================================================
3. DO NOT BUILD THE MARKETPLACE FIRST
==================================================

Avoid treating Tenderpreneur as a traditional two-sided marketplace that needs a large supplier network before it can provide value.

The first product should create value for the contractor even if the supplier network is initially small.

The intended progression is:

PHASE A:
Contractor uploads BoQ
→ Tenderpreneur parses it
→ Contractor corrects it
→ Contractor can price/organise the BoQ
→ Contractor exports it

PHASE B:
Contractor selects items requiring supplier quotes
→ Tenderpreneur identifies available suppliers
→ Quote requests are sent
→ Suppliers respond
→ Contractor compares quotes
→ Contractor selects prices
→ Export includes quote evidence

Initially, the supplier side may be operationally supported or manually managed.

DO NOT create unnecessary automation simply because the architecture permits it.

The system should be capable of manual/operator-assisted marketplace activity during validation.

==================================================
4. THE FIRST MARKETPLACE SHOULD BE NARROW
==================================================

Do not design the MVP around every possible supplier category.

The source brief identifies multiple possible categories, including:

- building materials
- PPE
- IT hardware
- transport/logistics
- specialist trades

But the MVP should support a controlled initial category and region.

Make the category and region configurable in the data model rather than hard-coded.

Do not invent the final launch category or region.

Leave those as an explicit product decision unless the owner provides them.

The architecture must allow expansion later without requiring a rewrite.

==================================================
5. DEADLINE IS A CORE PRODUCT FEATURE
==================================================

Tender deadlines are not incidental metadata.

They are central to the value proposition.

The contractor is often operating under time pressure.

Therefore the UX and domain model should support:

- tender deadline
- quote-request deadline
- countdown/status
- supplier response state
- outstanding items
- fallback/manual pricing

The contractor should be able to understand:

"What still needs pricing?"

"Which suppliers have responded?"

"Which items have no quote?"

"How much time remains?"

Do not build a generic CRM-style interface where deadlines disappear into records.

==================================================
6. THE AI MUST NEVER BE THE AUTHORITY
==================================================

LLM output is probabilistic.

The BoQ parser is an assistant.

Therefore:

LLM
→ structured candidate data
→ schema validation
→ deterministic validation/rules
→ human review/correction
→ persisted BoQ

Never:

LLM
→ directly trusted financial data

Every important parsed field must remain editable.

Parsing uncertainty should be visible where practical.

Do not design the UX in a way that implies:

"AI said it, therefore it is correct."

==================================================
7. AUDITABILITY IS A PRODUCT FEATURE
==================================================

Tenderpreneur's output must be defensible.

For every final price, the system should be able to determine:

- what the line item was
- what supplier quote was used, if applicable
- supplier identity
- quote price
- quote timestamp
- who selected the quote
- whether the contractor manually overrode the price
- why an override occurred, where applicable

This should influence both the data model and UI.

Do not build audit functionality as an afterthought.

==================================================
8. DO NOT OVERBUILD SUPPLIER COMPLIANCE
==================================================

The source brief mentions:

- CIDB
- CSD
- B-BBEE

These are useful trust signals.

They are NOT the MVP itself.

Do not build automated verification integrations unless explicitly requested.

The MVP can capture compliance information as optional supplier profile data.

The future architecture may provide extension points for verification.

==================================================
9. DO NOT BUILD THE FUTURE PRICING-INTELLIGENCE ENGINE YET
==================================================

There is a potentially powerful future flywheel:

More quotes
→ more historical pricing data
→ better benchmarks
→ better pricing recommendations
→ more contractor value
→ more contractors
→ more quotes

This is strategically important.

But do not attempt to manufacture this database before real usage exists.

The MVP should simply capture clean, structured quote data in a way that allows historical analysis later.

Do not build a sophisticated market-price prediction engine without actual data.

==================================================
10. MANUAL OPERATIONS ARE ALLOWED
==================================================

During validation, manual work behind the scenes is acceptable.

Do not automate a process merely because it can be automated.

For example, initially it may be acceptable for an operator to:

- review a parsed BoQ
- help recruit suppliers
- monitor quote requests
- follow up with suppliers
- intervene when matching fails

The software should progressively eliminate these manual steps once there is evidence that they need automation.

The immediate objective is learning and validating the workflow.

==================================================
11. AVOID PREMATURE MICROSERVICES
==================================================

The architecture contains logical services:

- BoQ Parsing
- Supplier Matching
- Quote Management
- Export
- Notifications

Treat these as domain boundaries.

Do NOT automatically turn them into separately deployed microservices.

For MVP, prefer a modular monolith unless there is a demonstrated technical reason otherwise.

The current architecture should optimize for:

- speed of development
- simplicity
- testability
- maintainability
- ability to iterate quickly

not theoretical scale.

==================================================
12. PRODUCT EXPERIMENTS COME BEFORE SCALE
==================================================

After completing the implementation plan, identify the smallest experiments that can validate the product.

At minimum, define acceptance criteria around:

EXPERIMENT 1:
Can a real BoQ be uploaded and correctly transformed into editable line items?

EXPERIMENT 2:
Can a contractor correct parsing errors without friction?

EXPERIMENT 3:
Can selected line items be converted into quote requests?

EXPERIMENT 4:
Can a real supplier receive a request and submit a quote from a phone?

EXPERIMENT 5:
Can a contractor compare quotes and select a defensible price?

EXPERIMENT 6:
Can Tenderpreneur produce a usable priced BoQ containing evidence of the pricing decisions?

These should become the backbone of the MVP test plan.

==================================================
13. IMPLEMENTATION PRIORITY
==================================================

Prioritize functionality in this order:

1. BoQ ingestion
2. BoQ parsing
3. Manual correction
4. Contractor pricing workflow
5. Supplier registration/profile
6. Quote request creation
7. Supplier quote submission
8. Quote comparison
9. Quote selection/manual override
10. Audit trail
11. PDF/Excel export
12. Notifications/automation improvements

Do not allow infrastructure work to consume disproportionate development time before the core workflow works.

==================================================
14. WHAT NOT TO BUILD
==================================================

Unless explicitly requested later, do NOT build:

- sophisticated supplier reputation algorithms
- automated CIDB verification
- automated CSD verification
- automated B-BBEE verification
- payment processing
- marketplace commissions
- SaaS billing
- multi-currency systems
- advanced procurement analytics
- AI tender win-probability scoring
- autonomous procurement agents
- complex supplier recommendation models
- enterprise ERP integrations
- large-scale analytics dashboards
- multi-country support

The architecture can leave extension points for these.

They are not MVP acceptance criteria.

==================================================
15. REQUIRED PRODUCT ARTIFACT
==================================================

Before substantial coding begins, update/create:

docs/mvp-validation-strategy.md

It must contain:

1. Core product hypothesis
2. Primary user
3. Primary job-to-be-done
4. MVP success criterion
5. Contractor workflow
6. Supplier workflow
7. Critical assumptions
8. Biggest risks
9. Manual operations we can tolerate initially
10. MVP acceptance criteria
11. What is explicitly out of scope
12. Metrics/events the application should capture to validate the thesis

Keep this document concise and practical.

==================================================
16. IMPORTANT: PRESERVE REVERSIBILITY
==================================================

When there is uncertainty, choose the smallest reversible implementation.

Do not make irreversible architectural commitments based on assumptions about future scale.

Do not invent requirements.

Do not silently expand scope.

If a product decision is genuinely unresolved, document it under:

"Decision required from owner"

rather than guessing.

==================================================
17. FINAL PRINCIPLE
==================================================

Build the smallest version of Tenderpreneur that can create this moment:

A contractor has a real tender.

They upload the BoQ.

Tenderpreneur understands it.

The contractor fixes anything the AI got wrong.

Tenderpreneur helps source real supplier prices.

The contractor sees the responses.

They choose defensible prices.

Tenderpreneur produces the final priced BoQ with evidence.

If we can make THAT work reliably, we have something worth scaling.

Everything else comes after that.

Now:

1. Review your existing implementation plan against these principles.
2. Update the plan where necessary.
3. Create `docs/mvp-validation-strategy.md`.
4. Explicitly identify any conflicts between the original build brief and these product-development constraints.
5. Do not begin large-scale implementation until this validation layer is incorporated into the implementation plan.
6. Report back with the revised implementation plan and the MVP validation strategy before proceeding with substantial feature development.
