"""Cola durable en SQLite (desarrollo y pruebas) y sentencia Postgres para producción.

SKIP LOCKED solo existe en Postgres. El almacén SQLite usa una transacción
IMMEDIATE y un UPDATE condicionado al estado pending, que cubre un proceso
y las pruebas de recuperación. Dos workers Postgres deben usar claim_sql_postgres.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

POSTGRES_CLAIM_SQL = """
SELECT id
FROM pipeline_steps
WHERE status = 'pending'
  AND available_at <= %(now)s
ORDER BY id
FOR UPDATE SKIP LOCKED
LIMIT 1
""".strip()

STAGES = (
    "discover",
    "normalize",
    "dedupe",
    "enrich",
    "score",
    "generate",
    "validate",
    "prepare_outreach",
)


class PlatformRepository:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=5)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS pipeline_runs (
                    id TEXT PRIMARY KEY,
                    campaign_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    requested_by TEXT NOT NULL,
                    idempotency_key TEXT UNIQUE,
                    created_at INTEGER NOT NULL,
                    started_at INTEGER,
                    finished_at INTEGER,
                    cancel_requested_at INTEGER,
                    config_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS pipeline_steps (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    stage TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempt INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    available_at INTEGER NOT NULL,
                    heartbeat_at INTEGER,
                    locked_by TEXT,
                    error_code TEXT,
                    safe_error_message TEXT,
                    result_json TEXT,
                    UNIQUE(run_id, sequence)
                );
                CREATE TABLE IF NOT EXISTS pipeline_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    step_id TEXT,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS businesses (
                    id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    domain TEXT,
                    phone_e164 TEXT,
                    status TEXT NOT NULL,
                    merged_into_id TEXT,
                    confidence REAL NOT NULL DEFAULT 0,
                    version INTEGER NOT NULL DEFAULT 1,
                    UNIQUE(provider, external_id)
                );
                CREATE TABLE IF NOT EXISTS field_observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    business_id TEXT NOT NULL,
                    field_name TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    observed_at INTEGER NOT NULL,
                    confidence REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS provider_connections (
                    id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    label TEXT NOT NULL,
                    auth_method TEXT NOT NULL,
                    status TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    priority INTEGER NOT NULL DEFAULT 0,
                    budget_usd REAL,
                    external_workspace TEXT,
                    scopes TEXT,
                    secret_ciphertext TEXT,
                    secret_last4 TEXT,
                    token_expires_at INTEGER,
                    last_check_at INTEGER,
                    last_error TEXT,
                    created_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS suppression_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    normalized_contact TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    UNIQUE(normalized_contact, channel)
                );
                CREATE TABLE IF NOT EXISTS outreach_consents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    normalized_contact TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    status TEXT NOT NULL,
                    source TEXT NOT NULL,
                    granted_at INTEGER,
                    UNIQUE(normalized_contact, channel)
                );
                CREATE TABLE IF NOT EXISTS outreach_messages (
                    id TEXT PRIMARY KEY,
                    business_id TEXT,
                    campaign_id TEXT,
                    status TEXT NOT NULL,
                    dry_run INTEGER NOT NULL,
                    body_preview TEXT,
                    created_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT NOT NULL,
                    role TEXT NOT NULL,
                    method TEXT NOT NULL,
                    path TEXT NOT NULL,
                    status_code INTEGER NOT NULL,
                    created_at INTEGER NOT NULL
                );
                """
            )

    def add_audit(self, *, subject: str, role: str, method: str, path: str, status_code: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO audit_log (subject, role, method, path, status_code, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (subject, role, method, path[:300], int(status_code), int(time.time())),
            )

    def create_run(
        self,
        *,
        campaign_id: str,
        requested_by: str,
        idempotency_key: str | None,
        config: dict,
        stages: tuple[str, ...] = STAGES,
    ) -> dict[str, Any]:
        now = int(time.time())
        with self._connect() as conn:
            if idempotency_key:
                existing = conn.execute(
                    "SELECT id, status FROM pipeline_runs WHERE idempotency_key = ?",
                    (idempotency_key,),
                ).fetchone()
                if existing:
                    return {"id": existing["id"], "status": existing["status"], "reused": True}
            run_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO pipeline_runs
                (id, campaign_id, status, requested_by, idempotency_key, created_at, started_at, config_json)
                VALUES (?, ?, 'running', ?, ?, ?, ?, ?)
                """,
                (run_id, campaign_id, requested_by, idempotency_key, now, now, json.dumps(config)),
            )
            for index, stage in enumerate(stages):
                conn.execute(
                    """
                    INSERT INTO pipeline_steps
                    (id, run_id, sequence, stage, status, available_at, max_attempts)
                    VALUES (?, ?, ?, ?, 'pending', ?, 3)
                    """,
                    (str(uuid.uuid4()), run_id, index, stage, now),
                )
            self._event(conn, run_id, None, "run_created", {"stages": list(stages)})
        return {"id": run_id, "status": "running", "reused": False}

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            run = conn.execute("SELECT * FROM pipeline_runs WHERE id = ?", (run_id,)).fetchone()
            if not run:
                return None
            steps = conn.execute(
                "SELECT * FROM pipeline_steps WHERE run_id = ? ORDER BY sequence",
                (run_id,),
            ).fetchall()
        return {"run": _row(run), "steps": [_row(step) for step in steps]}

    def events(self, run_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM pipeline_events WHERE run_id = ? ORDER BY id",
                (run_id,),
            ).fetchall()
        return [_row(row) for row in rows]

    def set_run_status(self, run_id: str, status: str) -> None:
        now = int(time.time())
        with self._connect() as conn:
            run = conn.execute("SELECT status FROM pipeline_runs WHERE id = ?", (run_id,)).fetchone()
            if not run:
                raise KeyError(run_id)
            if status == "paused" and run["status"] not in {"running", "paused"}:
                raise ValueError("El run no se puede pausar")
            if status == "running" and run["status"] != "paused":
                raise ValueError("El run no está en pausa")
            if status == "cancelled":
                conn.execute(
                    "UPDATE pipeline_steps SET status = 'cancelled' WHERE run_id = ? AND status = 'pending'",
                    (run_id,),
                )
                conn.execute(
                    "UPDATE pipeline_runs SET status = 'cancelled', cancel_requested_at = ?, finished_at = ? WHERE id = ?",
                    (now, now, run_id),
                )
            elif status == "running":
                conn.execute("UPDATE pipeline_runs SET status = 'running', finished_at = NULL WHERE id = ?", (run_id,))
            else:
                conn.execute("UPDATE pipeline_runs SET status = ? WHERE id = ?", (status, run_id))
            self._event(conn, run_id, None, f"run_{status}", {})

    def retry_failed(self, run_id: str) -> int:
        now = int(time.time())
        with self._connect() as conn:
            cur = conn.execute(
                """
                UPDATE pipeline_steps
                SET status = 'pending', available_at = ?, locked_by = NULL, error_code = NULL
                WHERE run_id = ? AND status = 'failed' AND attempt < max_attempts
                """,
                (now, run_id),
            )
            conn.execute(
                "UPDATE pipeline_runs SET status = 'running', finished_at = NULL WHERE id = ? AND status != 'cancelled'",
                (run_id,),
            )
            self._event(conn, run_id, None, "retry_failed", {"count": cur.rowcount})
            return cur.rowcount

    def recover_expired(self, now: int | None = None, lease_seconds: int = 30) -> int:
        moment = int(time.time()) if now is None else now
        cutoff = moment - lease_seconds
        with self._connect() as conn:
            expired = conn.execute(
                """
                UPDATE pipeline_steps
                SET status = 'failed', error_code = 'lease_expired', safe_error_message = 'Heartbeat vencido'
                WHERE status = 'running' AND heartbeat_at IS NOT NULL AND heartbeat_at < ?
                  AND attempt >= max_attempts
                """,
                (cutoff,),
            )
            released = conn.execute(
                """
                UPDATE pipeline_steps
                SET status = 'pending', locked_by = NULL, available_at = ?
                WHERE status = 'running' AND heartbeat_at IS NOT NULL AND heartbeat_at < ?
                  AND attempt < max_attempts
                """,
                (moment, cutoff),
            )
            return expired.rowcount + released.rowcount

    def claim_step(self, worker_id: str, now: int | None = None) -> dict[str, Any] | None:
        moment = int(time.time()) if now is None else now
        self.recover_expired(moment)
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT s.*
                FROM pipeline_steps s
                JOIN pipeline_runs r ON r.id = s.run_id
                WHERE s.status = 'pending'
                  AND s.available_at <= ?
                  AND r.status = 'running'
                  AND NOT EXISTS (
                    SELECT 1 FROM pipeline_steps prev
                    WHERE prev.run_id = s.run_id
                      AND prev.sequence < s.sequence
                      AND prev.status NOT IN ('succeeded', 'skipped', 'incomplete')
                  )
                ORDER BY s.sequence
                LIMIT 1
                """,
                (moment,),
            ).fetchone()
            if row is None:
                conn.commit()
                return None
            cur = conn.execute(
                """
                UPDATE pipeline_steps
                SET status = 'running', locked_by = ?, heartbeat_at = ?, attempt = attempt + 1
                WHERE id = ? AND status = 'pending'
                """,
                (worker_id, moment, row["id"]),
            )
            if cur.rowcount != 1:
                conn.rollback()
                return None
            conn.commit()
            claimed = dict(row)
            claimed["status"] = "running"
            claimed["locked_by"] = worker_id
            claimed["attempt"] = row["attempt"] + 1
            return claimed
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def heartbeat(self, step_id: str, worker_id: str, now: int | None = None) -> bool:
        moment = int(time.time()) if now is None else now
        with self._connect() as conn:
            cur = conn.execute(
                """
                UPDATE pipeline_steps SET heartbeat_at = ?
                WHERE id = ? AND locked_by = ? AND status = 'running'
                """,
                (moment, step_id, worker_id),
            )
            return cur.rowcount == 1

    def complete_step(self, step_id: str, result: dict) -> None:
        status = result.get("status") or "succeeded"
        if status not in {"succeeded", "skipped", "incomplete", "failed"}:
            status = "succeeded"
        with self._connect() as conn:
            step = conn.execute("SELECT run_id FROM pipeline_steps WHERE id = ?", (step_id,)).fetchone()
            if not step:
                return
            conn.execute(
                """
                UPDATE pipeline_steps
                SET status = ?, result_json = ?, error_code = ?, safe_error_message = ?, locked_by = NULL
                WHERE id = ?
                """,
                (
                    status,
                    json.dumps(result),
                    result.get("error_code"),
                    result.get("message"),
                    step_id,
                ),
            )
            self._event(conn, step["run_id"], step_id, f"step_{status}", {"stage_status": status})
            self._refresh_run(conn, step["run_id"])

    def upsert_business(self, *, provider: str, external_id: str, display_name: str, domain: str | None, phone_e164: str | None, confidence: float) -> str:
        now_id = str(uuid.uuid4())
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id FROM businesses WHERE provider = ? AND external_id = ?",
                (provider, external_id),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE businesses
                    SET display_name = ?, domain = COALESCE(?, domain), phone_e164 = COALESCE(?, phone_e164),
                        confidence = ?, version = version + 1
                    WHERE id = ?
                    """,
                    (display_name, domain, phone_e164, confidence, existing["id"]),
                )
                business_id = existing["id"]
            else:
                conn.execute(
                    """
                    INSERT INTO businesses
                    (id, provider, external_id, display_name, domain, phone_e164, status, confidence)
                    VALUES (?, ?, ?, ?, ?, ?, 'active', ?)
                    """,
                    (now_id, provider, external_id, display_name, domain, phone_e164, confidence),
                )
                business_id = now_id
            conn.execute(
                """
                INSERT INTO field_observations
                (business_id, field_name, value_json, provider, observed_at, confidence)
                VALUES (?, 'profile', ?, ?, ?, ?)
                """,
                (business_id, json.dumps({"display_name": display_name, "domain": domain}), provider, int(time.time()), confidence),
            )
            return business_id

    def count_businesses(self) -> int:
        with self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM businesses").fetchone()[0])

    def add_connection(self, *, label: str, ciphertext: str | None, last4: str | None, workspace: str | None) -> str:
        connection_id = str(uuid.uuid4())
        status = "needs_authorization" if not ciphertext else "ready"
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO provider_connections
                (id, provider, label, auth_method, status, enabled, external_workspace, secret_ciphertext, secret_last4, created_at)
                VALUES (?, 'lovable', ?, 'oauth', ?, 1, ?, ?, ?, ?)
                """,
                (connection_id, label, status, workspace, ciphertext, last4, int(time.time())),
            )
        return connection_id

    def list_connections(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, provider, label, auth_method, status, enabled, priority, budget_usd,
                       external_workspace, scopes, secret_last4, token_expires_at, last_check_at, last_error
                FROM provider_connections
                ORDER BY priority DESC, created_at
                """
            ).fetchall()
        return [_row(row) for row in rows]

    def set_connection_enabled(self, connection_id: str, enabled: bool) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE provider_connections SET enabled = ? WHERE id = ?",
                (1 if enabled else 0, connection_id),
            )

    def suppress(self, contact: str, channel: str, reason: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO suppression_entries (normalized_contact, channel, reason, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(normalized_contact, channel) DO UPDATE SET reason = excluded.reason
                """,
                (contact, channel, reason, int(time.time())),
            )

    def grant_consent(self, contact: str, channel: str, source: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO outreach_consents (normalized_contact, channel, status, source, granted_at)
                VALUES (?, ?, 'granted', ?, ?)
                ON CONFLICT(normalized_contact, channel) DO UPDATE SET status = 'granted', source = excluded.source
                """,
                (contact, channel, source, int(time.time())),
            )

    def outreach_eligibility(self, contact: str | None, channel: str, *, live_allowed: bool) -> str:
        if not live_allowed:
            return "DRY_RUN"
        if not contact:
            return "BLOCKED_NO_CONTACT"
        with self._connect() as conn:
            suppressed = conn.execute(
                "SELECT 1 FROM suppression_entries WHERE normalized_contact = ? AND channel = ?",
                (contact, channel),
            ).fetchone()
            if suppressed:
                return "BLOCKED_SUPPRESSED"
            consent = conn.execute(
                """
                SELECT status FROM outreach_consents
                WHERE normalized_contact = ? AND channel = ?
                """,
                (contact, channel),
            ).fetchone()
        if not consent or consent["status"] != "granted":
            return "BLOCKED_NO_CONSENT"
        return "ELIGIBLE"

    def record_outreach(self, *, business_id: str | None, campaign_id: str, status: str, dry_run: bool, preview: str) -> str:
        message_id = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO outreach_messages (id, business_id, campaign_id, status, dry_run, body_preview, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (message_id, business_id, campaign_id, status, 1 if dry_run else 0, preview[:180], int(time.time())),
            )
        return message_id

    def _refresh_run(self, conn: sqlite3.Connection, run_id: str) -> None:
        rows = conn.execute(
            "SELECT status FROM pipeline_steps WHERE run_id = ?",
            (run_id,),
        ).fetchall()
        statuses = {row["status"] for row in rows}
        if statuses & {"pending", "running"}:
            final = "running"
        elif "failed" in statuses:
            final = "failed"
        elif "incomplete" in statuses:
            final = "incomplete"
        elif "cancelled" in statuses:
            final = "cancelled"
        elif statuses and statuses <= {"succeeded", "skipped"}:
            final = "succeeded"
        else:
            final = "running"
        finished = int(time.time()) if final != "running" else None
        conn.execute(
            "UPDATE pipeline_runs SET status = ?, finished_at = ? WHERE id = ? AND status != 'paused'",
            (final, finished, run_id),
        )

    def _event(self, conn: sqlite3.Connection, run_id: str, step_id: str | None, event_type: str, payload: dict) -> None:
        conn.execute(
            """
            INSERT INTO pipeline_events (run_id, step_id, event_type, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (run_id, step_id, event_type, json.dumps(payload), int(time.time())),
        )


def _row(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    if "payload_json" in data and isinstance(data["payload_json"], str):
        data["payload"] = json.loads(data["payload_json"])
    if "config_json" in data and isinstance(data["config_json"], str):
        data["config"] = json.loads(data["config_json"])
    return data
