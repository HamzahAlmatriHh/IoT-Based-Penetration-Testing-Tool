# USB Sentinel technical audit

Date: 2026-11-19

## Executive summary

The repository contained a visually useful dashboard and a working Flask persistence model, but it was not suitable for public defensive-security use. The firmware performed USB HID keyboard injection, downloaded and executed a remote PowerShell script, embedded Wi-Fi credentials, and mixed device control with offensive host automation. The dashboard also maintained two incompatible backends and did not consistently protect read and write APIs.

## Findings

### Architecture

- `app.py` and `server.mjs` implemented overlapping state APIs with different routes, ports, authentication rules, and schemas.
- The browser was tied to hard-coded laboratory addresses and a 54-stage offensive collection model.
- State was stored in a mutable JSON file. Atomic replacement existed, but recovery, validation, retention, and session ownership were incomplete.
- Integration scripts described Telegram, credential, persistence, C2, and registry-hive workflows that are outside the public defensive scope.

### Security

- `main.cpp` embedded a Wi-Fi password.
- The firmware exposed USB HID keyboard behavior and automatically downloaded and executed a remote PowerShell script with execution-policy bypass flags.
- API reads were not consistently authenticated, and some writes trusted a subnet by default.
- The Node backend defaulted to loopback but implemented a conflicting authentication and ingestion model.
- User-controlled telemetry was length-limited but not validated against a documented schema.
- No consistent rate limiting, retention enforcement, secret-scanning workflow, or dependency review was present.
- Runtime state and potentially sensitive demonstration data were committed under `data/`.

### Quality and maintainability

- There was no canonical application package or configuration object.
- Automated tests covered only part of the legacy session API.
- No CI workflow validated Python, JavaScript, firmware builds, or secrets.
- Public contribution, vulnerability-reporting, architecture, threat-model, and change-management documents were missing.
- The bundled audio asset had no verifiable license metadata and should not be redistributed.

### Hardware verification limits

- The ESP32-S3 can report its own connectivity, uptime, firmware identity, and LED state.
- The existing hardware does not independently enumerate or identify arbitrary USB devices. Any such event must be supplied by an authorized external source and clearly labeled as reported or simulated.
- Hardware telemetry has not been physically verified as part of this repository refactor. CI can validate compilation only.

## Remediation decision

- Make Flask the single production backend.
- Remove Node server, PowerShell integrations, bundled runtime data, unlicensed audio, HID injection, remote execution, and offensive terminology/workflows.
- Require token authentication for all sensitive reads and writes; keep only a minimal public health check.
- Default to loopback and require explicit configuration for network exposure.
- Introduce typed validation, bounded request sizes, rate limiting, session isolation, atomic persistence with backup recovery, retention controls, audit logging, and safe deletion.
- Refactor firmware to Wi-Fi telemetry and LED status only, with secrets supplied through an ignored local configuration file.
- Add tests, CI, dependency updates, documentation, issue templates, and contribution/security policies.

## Verification status

Findings above were obtained through source inspection. Claims about runtime behavior are limited to tests and build commands recorded by the project CI or local verification output. No claim of complete security or physical hardware validation is made.
