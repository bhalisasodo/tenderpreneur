# BoQPro Security Baseline

## Multi-tenancy

Contractor organisations and supplier organisations are separate tenants.

Every private resource query must be scoped to the authenticated organisation.

Never rely on frontend role checks for authorization.

## File uploads

Treat all uploaded documents as hostile input.

- Validate MIME type and extension.
- Enforce size limits.
- Generate storage keys server-side.
- Do not use user filenames as filesystem paths.
- Scan/validate files where infrastructure permits.
- Store outside the web root.
- Never execute uploaded content.
- Never render uploaded HTML directly.

## LLM parsing

- Parse into a strict schema.
- Validate quantities, units and descriptions.
- Reject malformed structured output.
- Keep original source document.
- Preserve parser metadata/confidence.
- Never let model output directly perform privileged actions.

## Audit trail

Financially material actions must be auditable.

At minimum:
- who
- what
- when
- entity
- previous value
- new value
- reason where applicable

## Secrets

Use environment variables or a secret manager.

Never commit:
- API keys
- database passwords
- JWT signing secrets
- provider credentials

## API

- Authentication on protected routes.
- Server-side authorization.
- Input validation.
- Rate limiting for public/auth endpoints.
- Safe error messages.
- Structured logging without sensitive payloads.

## Privacy

Collect only information necessary for marketplace operation and compliance workflows.
