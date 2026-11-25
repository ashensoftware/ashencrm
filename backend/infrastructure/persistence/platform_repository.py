"""Cola durable y datos de plataforma en Postgres.

Dos workers pueden reclamar a la vez: el SELECT toma el paso con
`FOR UPDATE OF s SKIP LOCKED`, así que nunca reciben el mismo. Cada método
toma una conexión del pool y la devuelve al salir del `with` (commit o
rollback), así que el worker no acumula conexiones por tick.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from psycopg import Connection
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from backend.infrastructure.persistence.pg import get_default_pool

CLAIM_SQL = """
SELECT s.*
FROM pipeline_steps s
JOIN pipeline_runs r ON r.id = s.run_id
WHERE s.status = 'pending'
  AND s.available_at <= %(now)s
  AND r.status = 'running'
  AND NOT EXISTS (
    SELECT 1 FROM pipeline_steps prev
    WHERE prev.run_id = s.run_id
      AND prev.sequence < s.sequence
      AND prev.status NOT IN ('succeeded', 'skipped', 'incomplete')
  )
ORDER BY s.sequence, s.id
FOR UPDATE OF s SKIP LOCKED
LIMIT 1
""".strip()

# Nombre histórico; las pruebas y la documentación lo citan.
POSTGRES_CLAIM_SQL = CLAIM_SQL

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
    def __init__(self, pool: ConnectionPool | None = None):
        self._pool = pool or get_default_pool()

    def _connect(self):
        return self._pool.connection()

    def add_audit(self, *, subject: str, role: str, method: str, path: str, status_code: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO audit_log (subject, role, method, path, status_code, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
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
        run_id = str(uuid.uuid4())
        with self._connect() as conn:
            inserted = conn.execute(
                """
                INSERT INTO pipeline_runs
                (id, campaign_id, status, requested_by, idempotency_key, created_at, started_at, config_json)
                VALUES (%s, %s, 'running', %s, %s, %s, %s, %s)
                ON CONFLICT (idempotency_key) DO NOTHING
                RETURNING id
                """,
                (run_id, campaign_id, requested_by, idempotency_key, now, now, Jsonb(config)),
            ).fetchone()
            if inserted is None:
                existing = conn.execute(
                    "SELECT id, status FROM pipeline_runs WHERE idempotency_key = %s",
                    (idempotency_key,),
                ).fetchone()
                return {"id": existing["id"], "status": existing["status"], "reused": True}
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO pipeline_steps
                    (id, run_id, sequence, stage, status, available_at, max_attempts)
                    VALUES (%s, %s, %s, %s, 'pending', %s, 3)
                    """,
                    [(str(uuid.uuid4()), run_id, i, stage, now) for i, stage in enumerate(stages)],
                )
            self._event(conn, run_id, None, "run_created", {"stages": list(stages)})
        return {"id": run_id, "status": "running", "reused": False}

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            run = conn.execute("SELECT * FROM pipeline_runs WHERE id = %s", (run_id,)).fetchone()
            if not run:
                return None
            steps = conn.execute(
                "SELECT * FROM pipeline_steps WHERE run_id = %s ORDER BY sequence",
                (run_id,),
            ).fetchall()
        return {"run": _row(run), "steps": [_row(step) for step in steps]}

    def events(self, run_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM pipeline_events WHERE run_id = %s ORDER BY id",
                (run_id,),
            ).fetchall()
        return [_row(row) for row in rows]

    def set_run_status(self, run_id: str, status: str) -> None:
        now = int(time.time())
        with self._connect() as conn:
            run = conn.execute(
                "SELECT status FROM pipeline_runs WHERE id = %s FOR UPDATE", (run_id,)
            ).fetchone()
            if not run:
                raise KeyError(run_id)
            if status == "paused" and run["status"] not in {"running", "paused"}:
                raise ValueError("El run no se puede pausar")
            if status == "running" and run["status"] != "paused":
                raise ValueError("El run no está en pausa")
            if status == "cancelled":
                conn.execute(
                    "UPDATE pipeline_steps SET status = 'cancelled' WHERE run_id = %s AND status = 'pending'",
                    (run_id,),
                )
                conn.execute(
                    "UPDATE pipeline_runs SET status = 'cancelled', cancel_requested_at = %s, finished_at = %s "
                    "WHERE id = %s",
                    (now, now, run_id),
                )
            elif status == "running":
                conn.execute(
                    "UPDATE pipeline_runs SET status = 'running', finished_at = NULL WHERE id = %s",
                    (run_id,),
                )
            else:
                conn.execute("UPDATE pipeline_runs SET status = %s WHERE id = %s", (status, run_id))
            self._event(conn, run_id, None, f"run_{status}", {})

    def retry_failed(self, run_id: str) -> int:
        now = int(time.time())
        with self._connect() as conn:
            cur = conn.execute(
                """
                UPDATE pipeline_steps
                SET status = 'pending', available_at = %s, locked_by = NULL, error_code = NULL
                WHERE run_id = %s AND status = 'failed' AND attempt < max_attempts
                """,
                (now, run_id),
            )
            count = cur.rowcount
            conn.execute(
                "UPDATE pipeline_runs SET status = 'running', finished_at = NULL "
                "WHERE id = %s AND status <> 'cancelled'",
                (run_id,),
            )
            self._event(conn, run_id, None, "retry_failed", {"count": count})
            return count

    def recover_expired(self, now: int | None = None, lease_seconds: int = 30) -> int:
        moment = int(time.time()) if now is None else now
        cutoff = moment - lease_seconds
        with self._connect() as conn:
            expired = conn.execute(
                """
                UPDATE pipeline_steps
                SET status = 'failed', error_code = 'lease_expired', safe_error_message = 'Heartbeat vencido'
                WHERE status = 'running' AND heartbeat_at IS NOT NULL AND heartbeat_at < %s
                  AND attempt >= max_attempts
                """,
                (cutoff,),
            ).rowcount
            released = conn.execute(
                """
                UPDATE pipeline_steps
                SET status = 'pending', locked_by = NULL, available_at = %s
                WHERE status = 'running' AND heartbeat_at IS NOT NULL AND heartbeat_at < %s
                  AND attempt < max_attempts
                """,
                (moment, cutoff),
            ).rowcount
            return expired + released

    def claim_step(self, worker_id: str, now: int | None = None) -> dict[str, Any] | None:
        moment = int(time.time()) if now is None else now
        self.recover_expired(moment)
        with self._connect() as conn:
            row = conn.execute(CLAIM_SQL, {"now": moment}).fetchone()
            if row is None:
                return None
            conn.execute(
                """
                UPDATE pipeline_steps
                SET status = 'running', locked_by = %s, heartbeat_at = %s, attempt = attempt + 1
                WHERE id = %s
                """,
                (worker_id, moment, row["id"]),
            )
        claimed = _row(row)
        claimed["status"] = "running"
        claimed["locked_by"] = worker_id
        claimed["heartbeat_at"] = moment
        claimed["attempt"] = row["attempt"] + 1
        return claimed

    def heartbeat(self, step_id: str, worker_id: str, now: int | None = None) -> bool:
        moment = int(time.time()) if now is None else now
        with self._connect() as conn:
            cur = conn.execute(
                """
                UPDATE pipeline_steps SET heartbeat_at = %s
                WHERE id = %s AND locked_by = %s AND status = 'running'
                """,
                (moment, step_id, worker_id),
            )
            return cur.rowcount == 1

    def complete_step(self, step_id: str, result: dict) -> None:
        status = result.get("status") or "succeeded"
        if status not in {"succeeded", "skipped", "incomplete", "failed"}:
            status = "succeeded"
        with self._connect() as conn:
            step = conn.execute(
                "SELECT run_id FROM pipeline_steps WHERE id = %s", (step_id,)
            ).fetchone()
            if not step:
                return
            # Serializa el cierre de pasos de un mismo run para que _refresh_run vea el estado final.
            conn.execute("SELECT 1 FROM pipeline_runs WHERE id = %s FOR UPDATE", (step["run_id"],))
            conn.execute(
                """
                UPDATE pipeline_steps
                SET status = %s, result_json = %s, error_code = %s, safe_error_message = %s, locked_by = NULL
                WHERE id = %s
                """,
                (
                    status,
                    Jsonb(result),
                    result.get("error_code"),
                    result.get("message"),
                    step_id,
                ),
            )
            self._event(conn, step["run_id"], step_id, f"step_{status}", {"stage_status": status})
            self._refresh_run(conn, step["run_id"])

    def upsert_business(
        self,
        *,
        provider: str,
        external_id: str,
        display_name: str,
        domain: str | None,
        phone_e164: str | None,
        confidence: float,
    ) -> str:
        with self._connect() as conn:
            row = conn.execute(
                """
                INSERT INTO businesses
                (id, provider, external_id, display_name, domain, phone_e164, status, confidence)
                VALUES (%s, %s, %s, %s, %s, %s, 'active', %s)
                ON CONFLICT (provider, external_id) DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    domain = COALESCE(EXCLUDED.domain, businesses.domain),
                    phone_e164 = COALESCE(EXCLUDED.phone_e164, businesses.phone_e164),
                    confidence = EXCLUDED.confidence,
                    version = businesses.version + 1
                RETURNING id
                """,
                (str(uuid.uuid4()), provider, external_id, display_name, domain, phone_e164, confidence),
            ).fetchone()
            business_id = row["id"]
            conn.execute(
                """
                INSERT INTO field_observations
                (business_id, field_name, value_json, provider, observed_at, confidence)
                VALUES (%s, 'profile', %s, %s, %s, %s)
                """,
                (
                    business_id,
                    Jsonb({"display_name": display_name, "domain": domain}),
                    provider,
                    int(time.time()),
                    confidence,
                ),
            )
            return business_id

    def count_businesses(self) -> int:
        with self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) AS n FROM businesses").fetchone()["n"])

    def add_connection(self, *, label: str, ciphertext: str | None, last4: str | None, workspace: str | None) -> str:
        connection_id = str(uuid.uuid4())
        status = "needs_authorization" if not ciphertext else "ready"
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO provider_connections
                (id, provider, label, auth_method, status, enabled, external_workspace,
                 secret_ciphertext, secret_last4, created_at)
                VALUES (%s, 'lovable', %s, 'oauth', %s, 1, %s, %s, %s, %s)
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
                "UPDATE provider_connections SET enabled = %s WHERE id = %s",
                (1 if enabled else 0, connection_id),
            )

    def suppress(self, contact: str, channel: str, reason: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO suppression_entries (normalized_contact, channel, reason, created_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (normalized_contact, channel) DO UPDATE SET reason = EXCLUDED.reason
                """,
                (contact, channel, reason, int(time.time())),
            )

    def grant_consent(self, contact: str, channel: str, source: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO outreach_consents (normalized_contact, channel, status, source, granted_at)
                VALUES (%s, %s, 'granted', %s, %s)
                ON CONFLICT (normalized_contact, channel) DO UPDATE SET status = 'granted', source = EXCLUDED.source
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
                "SELECT 1 FROM suppression_entries WHERE normalized_contact = %s AND channel = %s",
                (contact, channel),
            ).fetchone()
            if suppressed:
                return "BLOCKED_SUPPRESSED"
            consent = conn.execute(
                "SELECT status FROM outreach_consents WHERE normalized_contact = %s AND channel = %s",
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
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (message_id, business_id, campaign_id, status, 1 if dry_run else 0, preview[:180], int(time.time())),
            )
        return message_id

    def list_outreach_messages(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            return conn.execute("SELECT * FROM outreach_messages ORDER BY created_at, id").fetchall()

    def _refresh_run(self, conn: Connection[Any], run_id: str) -> None:
        rows = conn.execute(
            "SELECT status FROM pipeline_steps WHERE run_id = %s",
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
            "UPDATE pipeline_runs SET status = %s, finished_at = %s WHERE id = %s AND status <> 'paused'",
            (final, finished, run_id),
        )

    def _event(self, conn: Connection[Any], run_id: str, step_id: str | None, event_type: str, payload: dict) -> None:
        conn.execute(
            """
            INSERT INTO pipeline_events (run_id, step_id, event_type, payload_json, created_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (run_id, step_id, event_type, Jsonb(payload), int(time.time())),
        )


def _row(row: dict[str, Any]) -> dict[str, Any]:
    """Mantiene el contrato SQLite: columnas *_json como texto, más `payload`/`config` parseados."""
    data = dict(row)
    for key in ("config_json", "payload_json", "result_json", "value_json"):
        if key in data and data[key] is not None and not isinstance(data[key], str):
            parsed = data[key]
            data[key] = json.dumps(parsed)
            if key == "payload_json":
                data["payload"] = parsed
            elif key == "config_json":
                data["config"] = parsed
        elif key in data and isinstance(data[key], str):
            if key == "payload_json":
                data["payload"] = json.loads(data[key])
            elif key == "config_json":
                data["config"] = json.loads(data[key])
    return data
