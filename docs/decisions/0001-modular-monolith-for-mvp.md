# ADR 0001 — Modular Monolith for MVP

## Decision

Implement Tenderpreneur as a modular monolith initially.

The backend should have explicit domain modules for BoQ parsing, suppliers, matching, quotes, exports, notifications, authentication, files and audit.

## Why

The source brief requires several logical services but does not justify the operational cost of independently deployed microservices at MVP stage.

A modular monolith preserves separation of concerns while keeping deployment, debugging and local development simple.

## Consequences

Positive:
- Faster MVP delivery.
- Easier local development.
- Fewer distributed-system failure modes.
- Domain boundaries remain available for later extraction.

Negative:
- Requires discipline to prevent module coupling.
- A future high-scale deployment may need service extraction.
