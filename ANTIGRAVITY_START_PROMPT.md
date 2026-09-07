# Antigravity Handoff Prompt

You are taking over the Tenderpreneur repository scaffold.

Read `AGENTS.md` first, then read:

- `docs/product-spec.md`
- `docs/architecture.md`
- `docs/data-model.md`
- `docs/api-contract.md`
- `docs/security.md`
- `docs/source/concept-c-build-brief.md`

The platform is called **Tenderpreneur**. "Concept C" is only the label used in the original build brief.

## Your first task

Do not immediately build the entire application.

First:

1. Inspect the complete repository.
2. Validate the proposed architecture against the source build brief.
3. Identify any contradictions or missing implementation decisions.
4. Produce `docs/implementation-plan.md` with:
   - architecture validation
   - final stack choices
   - directory/module plan
   - database migration plan
   - API implementation order
   - frontend implementation order
   - testing strategy
   - local development strategy
5. Do not introduce Phase 2 features.
6. Ask for approval before making large architectural deviations.

## Then build in this order

### Milestone 1 — Foundation

- Set up `apps/api`.
- Set up `apps/web`.
- Add PostgreSQL configuration.
- Add environment configuration.
- Add health checks.
- Add database migration tooling.
- Add authentication/authorization foundation without overbuilding identity management.
- Add shared API contracts.

### Milestone 2 — BoQ ingestion

Implement:

- BoQ creation.
- Document upload metadata.
- PDF/Excel/text ingestion abstraction.
- LLM parsing abstraction.
- Structured line-item schema validation.
- Manual line-item correction.
- Parsing confidence/uncertainty where useful.
- Persistence of the original document and parsed representation.

Do not let the LLM directly write arbitrary database records.

### Milestone 3 — Supplier marketplace loop

Implement:

- Supplier registration.
- Supplier category + region profile.
- Quote request creation.
- Supplier matching by category + region.
- Quote-request broadcast.
- Supplier mobile quote submission.
- Quote status/deadline handling.

Use an adapter for SMS/WhatsApp/email notifications. Do not make a specific gateway mandatory for local development.

### Milestone 4 — Comparison and export

Implement:

- Per-line-item quote comparison.
- Lowest / fastest / preferred views.
- Contractor selection.
- Manual price override.
- Immutable audit events for material pricing decisions.
- PDF/Excel export with quote references and timestamps.

## Required validation

Before declaring MVP complete, demonstrate this end-to-end path:

Contractor → upload BoQ → parse → correct line item → select items to source → match suppliers → broadcast request → supplier submits quote → contractor compares → contractor selects/overrides → export priced BoQ → audit trail remains inspectable.

Keep implementation incremental and test every milestone.
