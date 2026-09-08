# BoQPro API Contract

Base path: `/api/v1`

The exact serialization library may be chosen by the implementation, but the domain contract below should remain stable.

## Authentication

`Authorization: Bearer <token>`

All contractor/supplier resources must be organisation-scoped server-side.

## Health

`GET /health`

Response:

```json
{
  "status": "ok"
}
```

## BoQs

### Create

`POST /boqs`

```json
{
  "title": "Example Tender",
  "tender_reference": "TND-001",
  "tender_deadline": "2026-10-15T12:00:00Z"
}
```

### Upload source document

`POST /boqs/{boq_id}/documents`

Multipart file upload.

Supported MVP inputs:
- PDF
- XLSX/XLS
- common image formats for scans
- pasted text through a separate endpoint if useful

### Start parsing

`POST /boqs/{boq_id}/parse`

Parsing should be asynchronous where document size/provider latency makes that necessary.

### Get BoQ

`GET /boqs/{boq_id}`

Returns BoQ metadata, line items and parsing status.

### Edit line item

`PATCH /boqs/{boq_id}/line-items/{line_item_id}`

Only supplied fields are changed.

### Delete BoQ

`DELETE /boqs/{boq_id}`

Permanently deletes the BoQ, its line items, quote requests, quotes, and linked source document (if unshared).
Returns `204 No Content`.


## Quote requests

### Create quote request

`POST /quote-requests`

```json
{
  "line_item_id": "uuid",
  "response_deadline": "2026-10-10T12:00:00Z"
}
```

### Broadcast

`POST /quote-requests/{quote_request_id}/broadcast`

The backend matches suppliers using category + region and creates delivery records.

### List contractor quote requests

`GET /quote-requests?boq_id={id}`

## Supplier

### Register supplier profile

`POST /suppliers/profile`

```json
{
  "categories": ["building-materials"],
  "service_regions": ["KwaZulu-Natal"],
  "preferred_contact_method": "whatsapp"
}
```

### Supplier requests

`GET /suppliers/quote-requests`

Only requests delivered to the authenticated supplier are returned.

## Quotes

### Submit quote

`POST /quote-requests/{quote_request_id}/quotes`

```json
{
  "price_minor": 125000,
  "currency": "ZAR",
  "notes": "Includes delivery"
}
```

The API must reject submissions after the request deadline unless an explicit business rule later permits them.

### Compare quotes

`GET /boqs/{boq_id}/quote-comparison`

Return line items with available quotes and useful comparison fields.

### Select quote

`POST /quote-requests/{quote_request_id}/select`

```json
{
  "quote_id": "uuid"
}
```

### Manual price override

`POST /boqs/{boq_id}/line-items/{line_item_id}/price-override`

```json
{
  "price_minor": 100000,
  "currency": "ZAR",
  "reason": "Preferred supplier quote excluded from scope"
}
```

This must create an audit event.

## Exports

### Create export

`POST /boqs/{boq_id}/exports`

```json
{
  "format": "pdf"
}
```

Supported MVP formats:
- pdf
- xlsx

### Get export

`GET /exports/{export_id}`

Response should expose status and a secure download mechanism when ready.

## Error format

Use a consistent shape:

```json
{
  "error": {
    "code": "LINE_ITEM_NOT_FOUND",
    "message": "The requested line item does not exist.",
    "details": {}
  }
}
```

Do not expose provider stack traces or secrets to clients.
