---
name: quote-marketplace
description: Implements supplier matching, quote requests and quote comparison.
---

# Quote Marketplace Skill

MVP matching is deterministic:

`line item category + relevant region → eligible suppliers`

Quote requests must have:

- line item reference
- supplier recipient
- response deadline
- delivery status
- quote status

Supplier submissions must include price and currency.

Server-side deadline enforcement is mandatory.
