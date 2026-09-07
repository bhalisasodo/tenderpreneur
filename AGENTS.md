# Tenderpreneur — Agent Instructions

You are the engineering agent responsible for turning this scaffold into a production-quality MVP.

## Source of truth

Before making architectural or product decisions, read:

- `docs/product-spec.md`
- `docs/architecture.md`
- `docs/data-model.md`
- `docs/api-contract.md`
- `docs/security.md`
- `docs/source/concept-c-build-brief.md`

The source brief is authoritative for product scope. Do not silently add Phase 2 features.

## Product naming

The product is **Tenderpreneur**.

"Concept C" is a historical/source-document label only. Do not use it in the application UI, routes, database names, or public-facing copy.

## Engineering principles

- Prefer boring, maintainable architecture over cleverness.
- Keep business logic out of UI components and route handlers where practical.
- Use typed contracts at API boundaries.
- Validate all external input.
- Never trust parsed LLM output without schema validation.
- Every parsed BoQ field must remain manually editable.
- Preserve auditability: quote references, supplier identity, timestamps, and selection/override history must be traceable.
- Treat LLM output as probabilistic assistance, never as authoritative financial truth.
- Do not hard-code supplier credentials, API keys, or secrets.
- Do not add external integrations unless they are explicitly required by the current MVP task.
- Do not build Phase 2 features merely because the data model anticipates them.

## UX principles

- Contractor workflows are deadline-driven.
- Supplier quote submission must be mobile-first and extremely simple.
- Show clear quote/request deadlines.
- Make parsing uncertainty visible.
- Never hide manual correction.
- Avoid decorative complexity in core procurement workflows.

## Security

- Authorization must be enforced server-side.
- Contractor organisations must not see another organisation's private BoQs or quote data.
- Suppliers must only see quote requests they are authorized to respond to.
- Uploaded files must be treated as untrusted.
- Never render raw uploaded HTML.
- Never place sensitive information into client-side logs.
- Rate-limit public/authenticated endpoints where appropriate.

## Testing

Every meaningful feature should include:

- Unit tests for domain logic.
- API/integration tests for endpoint behavior.
- Validation/error-path tests.
- At least one end-to-end happy path for important user journeys once the frontend is functional.

## Definition of done

A feature is not complete when code merely compiles.

It is complete when:

1. The intended user flow works.
2. Invalid input is handled.
3. Authorization boundaries are tested.
4. Relevant tests pass.
5. Documentation/contracts are updated.
6. No unrelated scope has been introduced.

## Agent behavior

Work in small, reviewable increments.

Before changing the architecture, explain why the existing scaffold is insufficient.

When a requirement is ambiguous, preserve the source brief and choose the smallest reversible implementation rather than inventing product behavior.
