---
name: audit-export
description: Implements audit trails and evidence-based BoQ exports.
---

# Audit + Export Skill

Every final price must be traceable.

For selected supplier quotes, preserve:
- supplier
- quote ID/reference
- submitted timestamp
- selected timestamp
- selected price

For manual overrides, preserve:
- previous price
- new price
- actor
- timestamp
- reason

Exports should be plain, evidence-based and suitable for procurement review.
