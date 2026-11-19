# Architecture

Flask is the canonical backend and serves both the API and static dashboard. A locked state store serializes updates, writes a temporary file, preserves a backup, and atomically replaces the active JSON file. Each session has independent telemetry, events, LED state, and evidence metadata.

Trust boundaries are: the ESP32 device, the operator browser, the Flask process, and local persistent storage. Every sensitive API read or write requires the configured token. `/api/health` exposes only service health and version.

The firmware sends its own uptime, Wi-Fi signal strength, free heap, and firmware version. It does not emulate a keyboard or execute host-side actions. Evidence ingestion accepts metadata only.
