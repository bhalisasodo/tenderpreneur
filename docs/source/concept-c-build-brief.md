# Build Brief: AI BoQ Pricing & Verified Supplier-Quote Marketplace
### (Concept C — LaunchGremlin)

**Status:** Ready to scope/build. Demand validation skipped — cost to build is low.
**Owner:** Bhalisa / LaunchGremlin
**Date:** 24 August 2026

---

## 1. Problem Statement

A contractor wins the right to bid on a tender and must turn a Bill of Quantities (BoQ) or
scope of work into a defensible price before the closing date. Today this means manually
reading line items, guessing at material/labour costs, and phoning around for supplier
quotes — slow, error-prone, and with no audit trail to justify the price if challenged.
No AI-native SA tool currently combines BoQ parsing with a live, multi-supplier quote
marketplace.

## 2. Product in One Sentence

Upload a BoQ or scope of work → get it parsed into priced line items → get real quotes
from vetted suppliers against those line items → export a benchmarked, audit-ready price
before the deadline.

## 3. Target Users (two sides of the marketplace)

**Demand side — the contractor/bidder**
- SMME preparing a bid, needs a defensible price fast, has no procurement/QS department
- Pain: time pressure, pricing guesswork, no proof of "reasonable price" if queried

**Supply side — the supplier**
- Building materials, PPE, IT hardware, transport/logistics, or specialist trade suppliers
- Pain: no efficient channel to reach contractors who need quotes now; relies on referrals

## 4. Core User Flows

### 4.1 Contractor flow
1. Upload BoQ / scope document (PDF, Excel, or scanned) or paste tender text
2. System parses into structured line items: description, unit, quantity, category
3. System suggests a category + a benchmark price range per line item (from historical
   quote data + public rate guides where available)
4. Contractor selects which line items to send out for supplier quotes (materials,
   subcontracted labour, etc.) vs. price themselves
5. System auto-sends quote requests to matched, vetted suppliers in the relevant category
   and region
6. Supplier quotes come back into the same line-item view within a set window (e.g. 24-48h)
7. Contractor picks best quote per item (or manually overrides) → system compiles a final
   priced BoQ with a supplier-quote audit trail attached
8. Export as a submission-ready priced BoQ (PDF/Excel) with quote references

### 4.2 Supplier flow
1. Supplier registers, selects categories + service region + CIDB/CSD/B-BBEE status (optional
   but boosts matching priority)
2. Receives quote requests matching their category/region as they come in
3. Submits a price per line item within the request window
4. Wins or loses the line item; win-rate and responsiveness tracked to build a supplier
   reputation score over time

## 5. MVP Feature List (build first)

- [ ] Document upload + LLM-based BoQ/scope parsing into structured line items
- [ ] Manual line-item edit/override (parsing will never be 100% — must be correctable)
- [ ] Supplier registration (category, region, basic compliance fields)
- [ ] Quote-request broadcast to matched suppliers per line item
- [ ] Supplier quote submission (simple form, mobile-friendly — WhatsApp-style simplicity)
- [ ] Contractor comparison view (per line item: lowest / fastest / preferred quote)
- [ ] Export priced BoQ with attached quote references (PDF/Excel)

## 6. Phase 2 Features (after MVP validated by usage)

- Historical rate-benchmarking database (build from your own accumulated quote data —
  don't try to buy/scrape this upfront, it compounds naturally)
- Supplier reputation score (win rate, response time, delivery reliability if fed by
  Concept E later)
- CSD/CIDB/B-BBEE verification integration for supplier trust signals
- Take-rate or listing-fee billing on completed transactions
- Multi-currency / bulk-import for larger BoQs (100+ line items)

## 7. Data Model (high level)

- **BoQ** → has many **LineItems**
- **LineItem** → description, unit, quantity, category, benchmark_price (nullable),
  final_price (nullable), status (unsourced / quoted / selected)
- **QuoteRequest** → belongs to LineItem, broadcast to matched Suppliers
- **Quote** → belongs to QuoteRequest + Supplier, price, notes, submitted_at
- **Supplier** → categories[], region, compliance fields, reputation_score (later)
- **Contractor** → org details, BoQs[]

## 8. Key Technical/Product Risks

| Risk | Mitigation |
|---|---|
| BoQ parsing accuracy on messy/scanned PDFs | Always allow manual line-item correction; treat parsing as a time-saver, not a black box |
| Supplier cold-start (no suppliers = no value) | Recruit an initial supplier base manually in 1-2 categories/regions before wide contractor launch — don't launch both sides at once |
| Quote turnaround too slow for tender deadlines | Set and enforce a tight response window; show contractors a live countdown so they know when to fall back to manual sourcing |
| Price/audit-trail not accepted by SCM units | Keep exports plain and evidence-based (quote references, timestamps) rather than presentational |

## 9. Monetisation

- **MVP stage:** free, to build liquidity on both sides
- **Later:** take-rate on completed supplier transactions, and/or a SaaS fee for the
  BoQ-parsing/export tool itself (usable even without the marketplace side)

## 10. Suggested Build Order

1. BoQ upload + parsing + manual correction (usable standalone, no supplier network needed yet)
2. Supplier registration + manual quote-request broadcast (start with 1 category, e.g.
   building materials, 1 region)
3. Contractor comparison + export
4. Expand categories/regions once the first loop works end-to-end

## 11. Open Questions to Resolve Before/During Build

- Which 1-2 supplier categories and which region to launch first (recommend starting
  where you already have contractor relationships from LeadGremlin work)
- How suppliers are initially recruited (manual outreach vs. self-serve signup)
- Whether to require any compliance proof from suppliers at MVP stage or defer to Phase 2

---
*Companion document to the "AI-Assisted Tools for South African Tenderpreneurs" market
report, 24 August 2026.*
