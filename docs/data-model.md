# Tenderpreneur Data Model

## Core entities

### Organisation

Represents a contractor organisation or supplier organisation.

Fields:
- id
- type: contractor | supplier
- legal_name
- trading_name
- email
- phone
- region
- created_at
- updated_at

### User

Fields:
- id
- organisation_id
- email
- name
- role
- created_at
- updated_at

### BoQ

Fields:
- id
- contractor_organisation_id
- title
- tender_reference
- tender_deadline
- source_document_id
- status
- created_at
- updated_at

### Document

Fields:
- id
- owner_organisation_id
- storage_key
- original_filename
- mime_type
- size_bytes
- checksum
- created_at

### LineItem

Fields:
- id
- boq_id
- source_row_reference
- description
- unit
- quantity
- category
- benchmark_min
- benchmark_max
- benchmark_source
- benchmark_currency
- final_price
- pricing_status
- parsing_confidence
- created_at
- updated_at

`pricing_status`:
- unsourced
- awaiting_quotes
- quoted
- selected
- manually_priced

### QuoteRequest

Fields:
- id
- line_item_id
- requested_by_user_id
- response_deadline
- status
- created_at
- closed_at

### QuoteRequestSupplier

Join entity:
- quote_request_id
- supplier_organisation_id
- delivered_at
- viewed_at
- status

### Quote

Fields:
- id
- quote_request_id
- supplier_organisation_id
- price
- currency
- notes
- submitted_at
- status

### SupplierProfile

Fields:
- organisation_id
- categories[]
- service_regions[]
- compliance_status fields
- preferred_contact_method
- active

### AuditEvent

Append-only event record.

Fields:
- id
- organisation_id
- actor_user_id
- entity_type
- entity_id
- action
- before_json
- after_json
- metadata_json
- created_at

Important actions include:
- boq.created
- document.uploaded
- boq.parsed
- line_item.edited
- quote_request.created
- quote_request.broadcast
- quote.submitted
- quote.selected
- line_item.price_overridden
- export.generated

## Relationships

```text
Organisation
 ├── Users
 ├── BoQs (contractor)
 └── SupplierProfile (supplier)

BoQ
 ├── Document
 └── LineItems
       └── QuoteRequests
             ├── QuoteRequestSuppliers
             └── Quotes

All material changes → AuditEvents
```

## Design notes

- Use UUIDs or another non-sequential public identifier.
- Store money as integer minor units plus currency, not floating-point decimal values.
- Preserve original parsed values where auditability requires it.
- Never overwrite an audit event.
- Quote selection must be attributable to a user.
