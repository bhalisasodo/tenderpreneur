# Parsing Domain

Owns the orchestration of document extraction.

Recommended pipeline:

1. Load source document.
2. Extract text/tables where possible.
3. Send normalized content to an LLM provider.
4. Validate structured output against a strict schema.
5. Apply deterministic cleanup/rules.
6. Persist parsed line items.
7. Record parsing metadata.
8. Expose all fields for manual correction.

The LLM provider must be accessed through an adapter.
