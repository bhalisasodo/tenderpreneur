# BoQPro Product Specification

## 1. Problem

A contractor that wins a tender often has to turn a BoQ/scope into a defensible price under time pressure. Manual reading, price estimation and supplier calls are slow, error-prone and difficult to audit.

BoQPro combines BoQ parsing with a verified supplier quote marketplace.

## 2. Product promise

> Upload a BoQ or scope of work → get it parsed into priced line items → get real quotes from vetted suppliers → export a benchmarked, audit-ready price before the deadline.

## 3. Users

### Contractor / bidder

A tendering SMME that needs a defensible price quickly and may not have a procurement or QS department.

Primary needs:
- Fast document ingestion.
- Structured line items.
- Correctable parsing.
- Supplier sourcing.
- Quote comparison.
- Audit evidence.
- Export.

### Supplier

A supplier of building materials, PPE, IT hardware, transport/logistics or specialist trade services.

Primary needs:
- Relevant quote requests.
- Simple mobile submission.
- Clear deadlines.
- Visibility into win/loss outcomes over time.

## 4. Contractor flow

1. Upload BoQ/scope as PDF, Excel, scanned document, or pasted text.
2. Parse into description, unit, quantity and category.
3. Suggest category and benchmark range where benchmark data exists.
4. Contractor chooses which line items need supplier quotes.
5. Match suppliers by category and region.
6. Send quote requests.
7. Receive quotes within a defined response window.
8. Compare and select a quote or override manually.
9. Compile final priced BoQ with quote evidence.
10. Export PDF/Excel.

## 5. Supplier flow

1. Register.
2. Select categories and service region.
3. Provide optional compliance information.
4. Receive matching requests.
5. Submit price per line item.
6. Quote becomes visible to contractor according to request rules.
7. Supplier outcome is recorded.

## 6. MVP

- Document upload + LLM-based parsing.
- Manual line-item edit/override.
- Supplier registration.
- Quote-request broadcast.
- Supplier quote submission.
- Contractor quote comparison.
- PDF/Excel export with quote references.

## 7. Explicitly deferred

Do not build these in MVP unless the owner explicitly asks:

- Historical rate benchmarking database as a mature product.
- Supplier reputation scoring.
- CSD/CIDB/B-BBEE verification integration.
- Transaction take-rate billing.
- SaaS billing.
- Multi-currency bulk import.
- Concept E integrations.

The architecture may leave clean extension points for them.

## 8. Product constraints

### Parsing

Parsing is a time-saver, not an authority. Every parsed field must be correctable.

### Supplier cold start

MVP should support a controlled supplier pool. Matching must not assume a huge marketplace exists.

### Quote deadlines

Quote requests need explicit response windows and visible countdown/deadline state.

### Auditability

Exports should be evidence-based: quote reference, supplier, price, timestamp and selection/override history.

## 9. Open product decisions

These remain intentionally unresolved:

- Initial 1–2 supplier categories.
- Initial launch region.
- Supplier recruitment approach.
- Whether compliance evidence is mandatory at MVP or deferred.
