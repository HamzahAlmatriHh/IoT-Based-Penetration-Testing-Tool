# Threat model

## Assets

- API authentication token.
- Session and audit metadata.
- Device identity and operational telemetry.
- Integrity and availability of stored records.

## Trust boundaries and actors

The browser, ESP32-S3, network, Flask process, and storage are separate trust zones. Threat actors include an unauthorized LAN user, a malicious or compromised telemetry client, an operator who submits sensitive content accidentally, and an attacker with host-level access.

## Threats and controls

| Threat | Controls | Residual risk |
|---|---|---|
| Unauthorized API access | Token on all sensitive routes; localhost default | A stolen token grants API access |
| Eavesdropping | TLS required for network deployment | Plain HTTP remains unsafe if configured |
| Injection/XSS | Structured validation, text rendering, CSP | Browser or dependency defects remain possible |
| DoS | Body-size limit, per-IP rate limit, bounded records | In-memory limiter is not distributed |
| Cross-session disclosure | UUID session routes and authenticated reads | Token holders can access all sessions |
| State corruption | Lock, atomic replace, backup recovery | Disk loss requires external backups |
| Secret disclosure | Environment config, ignored local files, CI secret scan | Users can still paste secrets into free text |
| Misrepresented telemetry | `simulated` labeling | Device identity is not cryptographically attested |

This model does not claim complete security. Deployers remain responsible for TLS, host hardening, token rotation, backups, and network controls.
