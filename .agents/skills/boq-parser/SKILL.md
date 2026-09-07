---
name: boq-parser
description: Implements safe structured BoQ parsing with LLM assistance.
---

# BoQ Parser Skill

The parser must produce structured line items:

- description
- unit
- quantity
- category

Optional enrichment:
- benchmark_min
- benchmark_max
- benchmark_source
- parsing_confidence

## Rules

1. Extract before enriching.
2. Validate output against a strict schema.
3. Never silently discard uncertain rows.
4. Preserve source-row references where possible.
5. Make every field manually editable.
6. Treat scanned documents as an OCR/extraction problem before the LLM reasoning step.
7. Keep provider-specific LLM code behind `LLMProvider`.
