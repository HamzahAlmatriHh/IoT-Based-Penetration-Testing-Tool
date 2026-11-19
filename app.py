"""USB Sentinel defensive telemetry and evidence-metadata API."""

from __future__ import annotations

import hmac
import json
import os
import re
import threading
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_from_directory

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "dist"
ID_RE = re.compile(r"^[a-f0-9-]{36}$")
SENSITIVE_KEYS = re.compile(r"password|credential|private.?key|secret|token|cookie|browser.?data", re.I)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_text(value: Any, limit: int = 500) -> str:
    return str(value if value is not None else "").strip()[:limit]


class StateStore:
    def __init__(self, path: Path, retention_days: int):
        self.path = path
        self.backup = path.with_suffix(path.suffix + ".bak")
        self.retention_days = max(1, retention_days)
        self.lock = threading.RLock()
        self.state = self._load()

    @staticmethod
    def empty() -> dict[str, Any]:
        return {"schemaVersion": 1, "sessions": [], "audit": []}

    def _load(self) -> dict[str, Any]:
        for candidate in (self.path, self.backup):
            try:
                value = json.loads(candidate.read_text(encoding="utf-8"))
                if isinstance(value, dict) and isinstance(value.get("sessions"), list):
                    return value
            except (OSError, ValueError, TypeError):
                pass
        return self.empty()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        if self.path.exists():
            self.backup.write_bytes(self.path.read_bytes())
        temporary.write_text(json.dumps(self.state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, self.path)

    def prune(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        kept = []
        for session in self.state["sessions"]:
            try:
                created = datetime.fromisoformat(session["createdAt"].replace("Z", "+00:00"))
            except (KeyError, ValueError, TypeError):
                created = datetime.now(timezone.utc)
            if created >= cutoff:
                kept.append(session)
        self.state["sessions"] = kept


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config.update(
        MAX_CONTENT_LENGTH=int(os.getenv("USB_SENTINEL_MAX_REQUEST_BYTES", "65536")),
        API_TOKEN=os.getenv("USB_SENTINEL_API_TOKEN", ""),
        STATE_FILE=os.getenv("USB_SENTINEL_STATE_FILE", str(ROOT / "data" / "state.json")),
        RETENTION_DAYS=int(os.getenv("USB_SENTINEL_RETENTION_DAYS", "30")),
        RATE_LIMIT=int(os.getenv("USB_SENTINEL_RATE_LIMIT", "120")),
        TESTING=False,
    )
    if test_config:
        app.config.update(test_config)
    store = StateStore(Path(app.config["STATE_FILE"]), app.config["RETENTION_DAYS"])
    buckets: dict[str, deque[float]] = defaultdict(deque)

    def result(data: Any = None, status: int = 200, error: str | None = None):
        payload: dict[str, Any] = {"ok": error is None}
        payload["error" if error else "data"] = ({"message": error, "status": status} if error else data)
        return jsonify(payload), status

    def authorized() -> bool:
        expected = app.config["API_TOKEN"]
        if app.config["TESTING"] and not expected:
            return True
        supplied = request.headers.get("X-API-Key", "")
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            supplied = auth[7:].strip()
        return bool(expected) and hmac.compare_digest(supplied, expected)

    def body() -> dict[str, Any] | None:
        value = request.get_json(silent=True) if request.is_json else None
        return value if isinstance(value, dict) else None

    def sensitive(value: Any) -> bool:
        if isinstance(value, dict):
            return any(SENSITIVE_KEYS.search(str(key)) or sensitive(item) for key, item in value.items())
        if isinstance(value, list):
            return any(sensitive(item) for item in value)
        return False

    def find(session_id: str) -> dict[str, Any] | None:
        if not ID_RE.fullmatch(session_id):
            return None
        return next((item for item in store.state["sessions"] if item["id"] == session_id), None)

    def audit(action: str, session_id: str | None, detail: str) -> None:
        store.state["audit"].insert(0, {
            "id": str(uuid.uuid4()), "timestamp": utc_now(), "action": action,
            "sessionId": session_id, "detail": clean_text(detail),
            "sourceIp": request.remote_addr or "unknown",
        })
        store.state["audit"] = store.state["audit"][:1000]

    def append(session_id: str, collection: str, record: dict[str, Any]):
        with store.lock:
            session = find(session_id)
            if not session:
                return result(status=404, error="Session not found")
            record.update({"id": str(uuid.uuid4()), "timestamp": utc_now()})
            session[collection].append(record)
            session[collection] = session[collection][-500:]
            session["updatedAt"] = record["timestamp"]
            audit(f"{collection}.created", session_id, record.get("type") or record.get("name") or "record")
            store.save()
            return result(record, 201)

    @app.before_request
    def protect_api():
        if not request.path.startswith("/api/") or request.path == "/api/health":
            return None
        now = time.monotonic()
        bucket = buckets[request.remote_addr or "unknown"]
        while bucket and now - bucket[0] > 60:
            bucket.popleft()
        if len(bucket) >= app.config["RATE_LIMIT"]:
            return result(status=429, error="Rate limit exceeded")
        bucket.append(now)
        if not authorized():
            return result(status=401, error="Valid API token required")
        return None

    @app.after_request
    def security_headers(response):
        response.headers["Cache-Control"] = "no-store" if request.path.startswith("/api/") else "no-cache"
        response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

    @app.errorhandler(413)
    def too_large(_error):
        return result(status=413, error="Request body is too large")

    @app.get("/api/health")
    def health():
        return result({"service": "usb-sentinel", "status": "healthy", "version": 1})

    @app.get("/api/sessions")
    def list_sessions():
        with store.lock:
            sessions = [{
                "id": s["id"], "label": s["label"], "source": s["source"],
                "simulated": s["simulated"], "createdAt": s["createdAt"], "updatedAt": s["updatedAt"],
                "counts": {"telemetry": len(s["telemetry"]), "events": len(s["events"]), "evidence": len(s["evidence"])},
            } for s in store.state["sessions"]]
            return result({"sessions": sessions})

    @app.post("/api/sessions")
    def create_session():
        value = body()
        if value is None:
            return result(status=400, error="JSON object required")
        label, source = clean_text(value.get("label"), 80), clean_text(value.get("source"), 80)
        if not label or not source:
            return result(status=422, error="label and source are required")
        now = utc_now()
        session = {"id": str(uuid.uuid4()), "label": label, "source": source,
                   "simulated": bool(value.get("simulated", False)), "createdAt": now, "updatedAt": now,
                   "telemetry": [], "events": [], "evidence": [], "leds": {}}
        with store.lock:
            store.prune()
            store.state["sessions"].insert(0, session)
            audit("session.created", session["id"], label)
            store.save()
        return result(session, 201)

    @app.get("/api/sessions/<session_id>")
    def get_session(session_id: str):
        with store.lock:
            session = find(session_id)
            return result(session) if session else result(status=404, error="Session not found")

    @app.delete("/api/sessions/<session_id>")
    def delete_session(session_id: str):
        with store.lock:
            session = find(session_id)
            if not session:
                return result(status=404, error="Session not found")
            store.state["sessions"] = [item for item in store.state["sessions"] if item["id"] != session_id]
            audit("session.deleted", session_id, session["label"])
            store.save()
        return result({"deleted": session_id})

    @app.post("/api/sessions/<session_id>/telemetry")
    def telemetry(session_id: str):
        value = body()
        if value is None or sensitive(value):
            return result(status=422, error="Telemetry must not contain sensitive fields")
        device_id, metrics = clean_text(value.get("deviceId"), 80), value.get("metrics")
        if not device_id or not isinstance(metrics, dict) or len(metrics) > 30:
            return result(status=422, error="deviceId and a bounded metrics object are required")
        safe = {clean_text(key, 50): (item if isinstance(item, (int, float, bool)) else clean_text(item, 200)) for key, item in metrics.items()}
        return append(session_id, "telemetry", {"deviceId": device_id, "metrics": safe, "type": "device.telemetry"})

    @app.post("/api/sessions/<session_id>/events")
    def event(session_id: str):
        value = body() or {}
        event_type, message, status = clean_text(value.get("type"), 80), clean_text(value.get("message"), 500), clean_text(value.get("status"), 20)
        if not event_type or not message or status not in {"info", "success", "warning", "error"}:
            return result(status=422, error="type, message, and valid status are required")
        return append(session_id, "events", {"type": event_type, "message": message, "status": status, "simulated": bool(value.get("simulated", False))})

    @app.post("/api/sessions/<session_id>/evidence")
    def evidence(session_id: str):
        value = body() or {}
        name, kind, digest = clean_text(value.get("name"), 120), clean_text(value.get("kind"), 60), clean_text(value.get("sha256"), 64).lower()
        if not name or not kind or (digest and not re.fullmatch(r"[a-f0-9]{64}", digest)):
            return result(status=422, error="name, kind, and an optional valid SHA-256 are required")
        try:
            size = max(0, int(value.get("sizeBytes", 0)))
        except (TypeError, ValueError):
            return result(status=422, error="sizeBytes must be an integer")
        return append(session_id, "evidence", {"name": name, "kind": kind, "sizeBytes": size,
                      "sha256": digest or None, "note": clean_text(value.get("note"), 300), "type": "evidence.metadata"})

    @app.post("/api/sessions/<session_id>/led")
    def led(session_id: str):
        value = body() or {}
        color, state = clean_text(value.get("color"), 10).lower(), clean_text(value.get("state"), 20).lower()
        if color not in {"red", "green", "white", "off"} or state not in {"on", "off", "error"}:
            return result(status=422, error="Valid color and state are required")
        with store.lock:
            session = find(session_id)
            if not session:
                return result(status=404, error="Session not found")
            session["leds"][color] = {"state": state, "timestamp": utc_now()}
            session["updatedAt"] = utc_now()
            audit("led.updated", session_id, f"{color}:{state}")
            store.save()
            return result(session["leds"][color], 201)

    @app.get("/api/audit")
    def get_audit():
        with store.lock:
            return result({"audit": store.state["audit"][:500]})

    @app.get("/")
    def index():
        return send_from_directory(PUBLIC, "index.html")

    @app.get("/<path:asset_path>")
    def asset(asset_path: str):
        return send_from_directory(PUBLIC, asset_path)

    return app


app = create_app()

if __name__ == "__main__":
    if not app.config["API_TOKEN"]:
        raise SystemExit("USB_SENTINEL_API_TOKEN must be set before startup")
    app.run(host=os.getenv("USB_SENTINEL_HOST", "127.0.0.1"),
            port=int(os.getenv("USB_SENTINEL_PORT", "5000")), debug=False, threaded=True)
