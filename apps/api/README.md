# Tenderpreneur API

FastAPI backend scaffold.

## Planned modules

```text
app/
├── api/            # HTTP routes
├── core/           # configuration, security, errors
├── db/             # database/session/migrations
├── domains/
│   ├── auth/
│   ├── boq/
│   ├── parsing/
│   ├── suppliers/
│   ├── matching/
│   ├── quotes/
│   ├── exports/
│   ├── notifications/
│   ├── files/
│   └── audit/
├── integrations/   # LLM, storage, notification providers
└── main.py
```

Do not implement all modules at once. Follow the milestone order in `ANTIGRAVITY_START_PROMPT.md`.
