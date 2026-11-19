# API reference

All routes except `GET /api/health` require `X-API-Key: <token>` or `Authorization: Bearer <token>`. JSON responses use `{ "ok": true, "data": ... }` or `{ "ok": false, "error": { ... } }`.

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/health` | Minimal public health check |
| GET/POST | `/api/sessions` | List or create sessions |
| GET/DELETE | `/api/sessions/{id}` | Read or safely delete one session |
| POST | `/api/sessions/{id}/telemetry` | Ingest bounded device metrics |
| POST | `/api/sessions/{id}/events` | Add an authorized event |
| POST | `/api/sessions/{id}/evidence` | Add evidence metadata only |
| POST | `/api/sessions/{id}/led` | Record an LED state |
| GET | `/api/audit` | Read administrative audit records |

Telemetry example:

```json
{"deviceId":"esp32-s3-lab-device","metrics":{"uptimeMs":120000,"wifiRssi":-58,"freeHeapBytes":240000}}
```

Evidence example:

```json
{"name":"authorized-export.json","kind":"telemetry-export","sizeBytes":2048,"sha256":"<64 lowercase hex characters>","note":"Sanitized export"}
```

Raw files and fields named like passwords, credentials, tokens, cookies, secrets, browser data, or private keys are rejected from telemetry.
