# Tenderpreneur Architecture

## Architectural style

Use a modular full-stack application with a clear API boundary.

```mermaid
flowchart TB
    subgraph Client["Client Apps"]
      SP["Supplier Portal\nmobile-first quote submission"]
      CW["Contractor Web App\nupload BoQ, compare quotes, export"]
    end

    subgraph API["API Layer"]
      GW["API Gateway / Auth"]
    end

    subgraph Core["Core Services"]
      QM["Quote Management Service\nrequests, windows, submissions"]
      SM["Supplier Matching Service\ncategory + region"]
      EX["Export Service\npriced BoQ + audit trail"]
      BP["BoQ Parsing Service\nLLM extraction + rules"]
      NS["Notification Service\nSMS / WhatsApp / email"]
    end

    subgraph Data["Data Layer"]
      DB[("Primary Database\nBoQs, LineItems, Suppliers, QuoteRequests, Quotes")]
      FS[("File Storage\nuploaded docs, exports")]
    end

    subgraph External["External"]
      MSG["SMS / WhatsApp Gateway"]
      LLM["LLM API\ndocument parsing"]
    end

    SP --> GW
    CW --> GW

    GW --> QM
    GW --> SM
    GW --> EX
    GW --> BP

    QM --> NS
    QM --> DB
    SM --> DB
    EX --> DB
    EX --> FS
    BP --> DB
    BP --> FS
    BP --> LLM
    NS --> MSG
```

## Layer responsibilities

### Client apps

One web application can initially expose two role-specific experiences:

- Contractor portal.
- Supplier portal.

Do not create two independently deployed frontends unless there is a concrete reason.

### API layer

Responsible for:

- Authentication.
- Authorization.
- Request validation.
- Rate limiting.
- Routing.
- Consistent error responses.

### Core services

Keep domain modules separated even if deployed as one backend process in MVP.

Suggested backend modules:

```text
boq/
quotes/
suppliers/
matching/
exports/
notifications/
audit/
auth/
files/
parsing/
```

### Data layer

PostgreSQL stores transactional entities and audit events.

Object storage stores:

- Original BoQ files.
- Intermediate parsed documents if needed.
- Generated PDF/Excel exports.

Do not store large binary documents directly in PostgreSQL.

### External services

Wrap external providers behind interfaces:

- `LLMProvider`
- `ObjectStorageProvider`
- `NotificationProvider`
- `ExportRenderer`

This keeps local development testable and makes providers replaceable.

## Deployment model for MVP

Start as:

- One frontend deployment.
- One API deployment.
- One PostgreSQL instance.
- One object-storage bucket.
- Optional worker process for asynchronous jobs.

Do not prematurely split every core service into separate microservices. The service boxes represent domain boundaries, not a requirement for separate deployments.
