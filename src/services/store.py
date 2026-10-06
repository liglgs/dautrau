"""SQLite store cho MVP điều tra an toàn thuốc (M02).

Lưu trữ bền vững, một file, không phụ thuộc PostgreSQL của luồng VMEC:
  * ``investigations`` — state JSON + version (khóa lạc quan) + trạng thái chạy;
  * ``events`` — timeline cho frontend polling (``after_id``);
  * ``documents`` — tài liệu nguồn bất biến theo ``(source, source_id, version)``;
  * ``evidence_versions`` — bằng chứng theo phiên bản;
  * ``review_decisions`` — quyết định của reviewer (append-only);
  * ``dossier_versions`` — hồ sơ theo phiên bản + trạng thái duyệt;
  * ``audit_events`` — nhật ký append-only.

Mọi thao tác đi qua một ``threading.RLock`` và một transaction ``with conn``.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.models.schemas import (
    BudgetState,
    ClaimInput,
    Dossier,
    EvidenceUnit,
    InvestigationConfig,
    InvestigationState,
    ReviewDecision,
    ReviewStatus,
    RunStatus,
    SourceDocument,
)
from src.services.errors import idempotency_conflict, invalid_state, not_found, version_conflict
from src.services.request_context import current_request_id

SCHEMA = """
CREATE TABLE IF NOT EXISTS investigations (
    id TEXT PRIMARY KEY,
    claim_json TEXT NOT NULL,
    run_status TEXT NOT NULL,
    assessment_status TEXT,
    checkpoint TEXT,
    next_stage TEXT,
    state_json TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    idempotency_key TEXT UNIQUE,
    request_hash TEXT,
    created_by TEXT DEFAULT 'anonymous',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    investigation_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    message TEXT NOT NULL DEFAULT '',
    payload_json TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_investigation ON events (investigation_id, id);

CREATE TABLE IF NOT EXISTS documents (
    doc_id TEXT PRIMARY KEY,
    investigation_id TEXT NOT NULL,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    hash TEXT NOT NULL,
    text TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (source, source_id, version)
);

CREATE TABLE IF NOT EXISTS investigation_documents (
    investigation_id TEXT NOT NULL,
    doc_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (investigation_id, doc_id)
);

CREATE TABLE IF NOT EXISTS evidence_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evidence_id TEXT NOT NULL,
    investigation_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    doc_id TEXT NOT NULL,
    stance TEXT NOT NULL,
    excluded INTEGER NOT NULL DEFAULT 0,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (investigation_id, evidence_id, version)
);
CREATE INDEX IF NOT EXISTS idx_evidence_investigation ON evidence_versions (investigation_id);

CREATE TABLE IF NOT EXISTS review_decisions (
    decision_id TEXT PRIMARY KEY,
    investigation_id TEXT NOT NULL,
    checkpoint TEXT NOT NULL,
    action TEXT NOT NULL,
    reviewer_id TEXT NOT NULL,
    actor_role TEXT,
    reason TEXT NOT NULL DEFAULT '',
    expected_version INTEGER NOT NULL,
    result_version INTEGER,
    result_status TEXT,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reviews_investigation ON review_decisions (investigation_id);

CREATE TABLE IF NOT EXISTS dossier_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dossier_id TEXT NOT NULL,
    investigation_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    approved_at TEXT,
    approved_by TEXT,
    UNIQUE (investigation_id, version)
);

CREATE TABLE IF NOT EXISTS resume_requests (
    investigation_id TEXT NOT NULL,
    token TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (investigation_id, token)
);

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    investigation_id TEXT,
    actor TEXT NOT NULL,
    actor_role TEXT,
    action TEXT NOT NULL,
    request_id TEXT,
    payload_json TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions (user_id);

CREATE TABLE IF NOT EXISTS app_users (
    user_id TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    role TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    password_hash TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'system'
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_app_users_email ON app_users (email);
CREATE INDEX IF NOT EXISTS idx_app_users_role ON app_users (role);

CREATE TABLE IF NOT EXISTS api_tokens (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    label TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    expires_at TEXT,
    revoked_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_api_tokens_user ON api_tokens (user_id);
"""


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _hash_request(claim: ClaimInput) -> str:
    import hashlib

    return hashlib.sha256(claim.model_dump_json().encode("utf-8")).hexdigest()


def _last_review_payload(action: Any, checkpoint: Any, created_at: Any) -> dict[str, Any] | None:
    """Gói gọn quyết định review mới nhất để API trả ra ngoài (``None`` khi chưa ai duyệt)."""
    if action is None:
        return None
    return {"action": str(action), "checkpoint": str(checkpoint) if checkpoint else None, "created_at": created_at}


def _audit_row(row: Any) -> dict[str, Any]:
    """Chuyển một dòng ``audit_events`` thành dict cho API.

    Bản ghi cũ chỉ có chuỗi vai trong ``actor``; đánh dấu ``legacy_actor`` để người đọc biết mà
    không phải đoán, và không cần sửa lại lịch sử đã ghi.
    """
    keys = row.keys()
    return {
        "id": row["id"],
        "investigation_id": row["investigation_id"],
        "actor": row["actor"],
        "actor_role": row["actor_role"] if "actor_role" in keys else None,
        "action": row["action"],
        "request_id": row["request_id"] if "request_id" in keys else None,
        "legacy_actor": "actor_role" not in keys or row["actor_role"] is None,
        "payload": json.loads(row["payload_json"] or "{}"),
        "created_at": row["created_at"],
    }


class MvpStore:
    """Kho lưu trữ SQLite cho MVP."""

    def __init__(self, path: str | Path = ":memory:"):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        with self._lock, self._conn:
            self._conn.executescript(SCHEMA)
        self._migrate()

    def _migrate(self) -> None:
        """Nâng cấp file SQLite cũ lên schema hiện tại (idempotent).

        * ``evidence_versions``: đổi ``UNIQUE (evidence_id, version)`` thành
          ``UNIQUE (investigation_id, evidence_id, version)`` — hai cuộc điều tra cùng kịch bản dùng
          chung ``evidence_id`` từ fixture (ví dụ ``EVI-PUBMED-LACTIC``) nên khoá cũ làm lượt chạy
          thứ hai lỗi ``UNIQUE constraint failed``.
        * ``investigation_documents``: liên kết tài liệu bất biến dùng chung với từng cuộc điều tra;
          backfill từ cột ``documents.investigation_id`` của các bản ghi cũ.
        """
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'evidence_versions'"
            ).fetchone()
            if row is not None and "UNIQUE (investigation_id, evidence_id, version)" not in row["sql"]:
                self._conn.executescript(
                    """
                    ALTER TABLE evidence_versions RENAME TO evidence_versions_old;
                    CREATE TABLE evidence_versions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        evidence_id TEXT NOT NULL,
                        investigation_id TEXT NOT NULL,
                        version INTEGER NOT NULL,
                        doc_id TEXT NOT NULL,
                        stance TEXT NOT NULL,
                        excluded INTEGER NOT NULL DEFAULT 0,
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        UNIQUE (investigation_id, evidence_id, version)
                    );
                    INSERT INTO evidence_versions (id, evidence_id, investigation_id, version, doc_id, stance, excluded, payload_json, created_at)
                        SELECT id, evidence_id, investigation_id, version, doc_id, stance, excluded, payload_json, created_at
                        FROM evidence_versions_old;
                    DROP TABLE evidence_versions_old;
                    CREATE INDEX IF NOT EXISTS idx_evidence_investigation ON evidence_versions (investigation_id);
                    """
                )
            self._conn.execute(
                """INSERT OR IGNORE INTO investigation_documents (investigation_id, doc_id, created_at)
                   SELECT investigation_id, doc_id, created_at FROM documents"""
            )
            cols = [col[1] for col in self._conn.execute("PRAGMA table_info(investigations)").fetchall()]
            if cols and "created_by" not in cols:
                self._conn.execute("ALTER TABLE investigations ADD COLUMN created_by TEXT DEFAULT 'anonymous'")
            # Cột thêm sau (AUTH-03): nhật ký phải trả lời được "ai làm gì", không chỉ "vai nào".
            self._add_column("sessions", "revoked_at", "TEXT")
            self._add_column("audit_events", "actor_role", "TEXT")
            self._add_column("audit_events", "request_id", "TEXT")
            # Cột kết quả của quyết định duyệt (RV-07): một quyết định phải nói được nó đã dẫn tới
            # phiên bản nào và trạng thái gì, thay vì để người đọc tự suy từ thứ tự thời gian.
            self._add_column("review_decisions", "actor_role", "TEXT")
            self._add_column("review_decisions", "result_version", "INTEGER")
            self._add_column("review_decisions", "result_status", "TEXT")

    def _add_column(self, table: str, column: str, ddl_type: str) -> None:
        """Thêm cột nếu file SQLite cũ chưa có (idempotent)."""
        existing = [row[1] for row in self._conn.execute(f"PRAGMA table_info({table})").fetchall()]
        if existing and column not in existing:
            self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}")

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # ----------------------------------------------------------------------------------
    # Investigations
    # ----------------------------------------------------------------------------------

    def create_investigation(
        self,
        claim: ClaimInput,
        *,
        idempotency_key: str | None = None,
        investigation_id: str | None = None,
        created_by: str = "anonymous",
        actor_role: str | None = None,
    ) -> tuple[InvestigationState, bool]:
        """Tạo cuộc điều tra mới; trả ``(state, created)``.

        Cùng ``Idempotency-Key`` + cùng payload → trả bản ghi cũ (``created=False``).
        Cùng key nhưng payload khác → 409 ``idempotency_conflict``.
        """
        request_hash = _hash_request(claim)
        with self._lock, self._conn:
            if idempotency_key:
                # AUTH-02: khoá chống lặp chỉ có hiệu lực trong phạm vi **người tạo**. Tra cứu phải
                # kèm ``created_by``; nếu khoá đã thuộc người khác thì từ chối 409 — tuyệt đối không
                # trả về ca của người đó. Đây chính là đường rò rỉ dữ liệu đã bị bịt.
                row = self._conn.execute(
                    "SELECT id, request_hash, created_by FROM investigations WHERE idempotency_key = ?",
                    (idempotency_key,),
                ).fetchone()
                if row is not None:
                    if row["created_by"] != created_by:
                        raise idempotency_conflict(idempotency_key)
                    if row["request_hash"] != request_hash:
                        raise idempotency_conflict(idempotency_key)
                    return self._load_state(row["id"]), False
            identifier = investigation_id or f"INV-{uuid4().hex[:12]}"
            timestamp = now_iso()
            cfg = claim.config or InvestigationConfig()
            budget = BudgetState(
                max_steps=cfg.max_steps,
                max_documents=cfg.max_documents,
            )
            state = InvestigationState(
                investigation_id=identifier,
                claim=claim,
                config=cfg,
                budget=budget,
                run_status=RunStatus.QUEUED,
                created_by=created_by,
            )
            self._conn.execute(
                """INSERT INTO investigations
                   (id, claim_json, run_status, assessment_status, checkpoint, next_stage, state_json,
                    version, idempotency_key, request_hash, created_by, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    identifier,
                    claim.model_dump_json(),
                    str(RunStatus.QUEUED),
                    None,
                    None,
                    None,
                    state.model_dump_json(),
                    1,
                    idempotency_key,
                    request_hash,
                    created_by,
                    timestamp,
                    timestamp,
                ),
            )
            self._append_event(identifier, "created", "Tạo cuộc điều tra mới.")
            self._audit(
                identifier,
                created_by,
                "investigation_created",
                {"claim": claim.model_dump()},
                actor_role=actor_role,
            )
        return state, True

    def get_state(self, investigation_id: str) -> InvestigationState:
        with self._lock:
            return self._load_state(investigation_id)

    def _load_state(self, investigation_id: str) -> InvestigationState:
        row = self._conn.execute(
            "SELECT state_json FROM investigations WHERE id = ?", (investigation_id,)
        ).fetchone()
        if row is None:
            raise not_found("cuộc điều tra", investigation_id)
        return InvestigationState.model_validate(json.loads(row["state_json"]))

    def save_state(
        self,
        state: InvestigationState,
        *,
        expected_version: int | None = None,
        event: tuple[str, str] | tuple[str, str, dict[str, Any]] | None = None,
        actor: str = "system",
        actor_role: str | None = None,
    ) -> InvestigationState:
        """Lưu state với kiểm tra phiên bản (stale version không được ghi đè).

        ``event`` nhận ``(kind, message)`` hoặc ``(kind, message, payload)``. Dạng ba phần tử cho
        phép gắn dữ liệu có cấu trúc vào đúng dòng nhật ký đã có, thay vì phải thêm một dòng mới
        làm nhiễu trình tự sự kiện mà giao diện đang đọc.
        """
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT version FROM investigations WHERE id = ?", (state.investigation_id,)
            ).fetchone()
            if row is None:
                raise not_found("cuộc điều tra", state.investigation_id)
            current = int(row["version"])
            if expected_version is not None and expected_version != current:
                raise version_conflict(expected_version, current)
            updated = state.model_copy(update={"version": current + 1, "updated_at": datetime.now(UTC)})
            # API-05: ghi lại cả ``claim_json``. Trước đây cột này giữ nguyên câu hỏi gốc, nên sau
            # khi sửa câu hỏi (``edit_claim``) màn chi tiết hiện dữ liệu mới còn màn danh sách vẫn
            # hiện thuốc/biến cố cũ — hai màn hình nói hai chuyện khác nhau.
            self._conn.execute(
                """UPDATE investigations
                   SET state_json = ?, claim_json = ?, run_status = ?, assessment_status = ?,
                       checkpoint = ?, next_stage = ?, version = ?, updated_at = ?
                   WHERE id = ?""",
                (
                    updated.model_dump_json(),
                    updated.claim.model_dump_json(),
                    str(updated.run_status),
                    str(updated.assessment_status) if updated.assessment_status else None,
                    str(updated.checkpoint) if updated.checkpoint else None,
                    updated.next_stage,
                    updated.version,
                    updated.updated_at.isoformat(),
                    updated.investigation_id,
                ),
            )
            if event is not None:
                payload = event[2] if len(event) > 2 else None
                self._append_event(updated.investigation_id, event[0], event[1], payload)
            self._audit(
                updated.investigation_id,
                actor,
                "state_saved",
                {"version": updated.version, "run_status": str(updated.run_status)},
                actor_role=actor_role,
            )
        return updated

    def list_investigations(
        self,
        limit: int = 50,
        *,
        created_by: str | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Danh sách cuộc điều tra, mới nhất trước.

        ``created_by`` lọc **trong câu truy vấn** (trước ``LIMIT``). AUTH-02: lọc ở tầng Python
        sau khi đã cắt trang làm ca cũ biến mất khỏi danh sách và làm ``limit`` trả về thiếu.
        """
        where = "WHERE i.created_by = ?" if created_by is not None else ""
        params: list[Any] = [created_by] if created_by is not None else []
        with self._lock:
            rows = self._conn.execute(
                f"""SELECT i.id, i.run_status, i.assessment_status, i.checkpoint, i.next_stage,
                          i.version, i.claim_json, i.created_by, i.created_at, i.updated_at,
                          d.status AS review_status,
                          r.action AS last_review_action,
                          r.checkpoint AS last_review_checkpoint,
                          r.created_at AS last_review_at
                   FROM investigations AS i
                   LEFT JOIN dossier_versions AS d
                     ON d.investigation_id = i.id
                    AND d.version = (SELECT MAX(version) FROM dossier_versions WHERE investigation_id = i.id)
                   LEFT JOIN review_decisions AS r
                     ON r.rowid = (SELECT rowid FROM review_decisions
                                    WHERE investigation_id = i.id
                                    ORDER BY created_at DESC, rowid DESC LIMIT 1)
                   {where}
                   ORDER BY i.updated_at DESC LIMIT ? OFFSET ?""",
                (*params, limit, max(offset, 0)),
            ).fetchall()
        result = []
        for row in rows:
            claim = json.loads(row["claim_json"])
            result.append(
                {
                    "investigation_id": row["id"],
                    "run_status": row["run_status"],
                    "assessment_status": row["assessment_status"],
                    "checkpoint": row["checkpoint"],
                    "next_stage": row["next_stage"],
                    "version": row["version"],
                    "drug": claim.get("drug"),
                    "event": claim.get("event"),
                    "review_status": row["review_status"],
                    "last_review": _last_review_payload(
                        row["last_review_action"], row["last_review_checkpoint"], row["last_review_at"]
                    ),
                    "created_by": row["created_by"] if "created_by" in row.keys() else "anonymous",
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            )
        return result

    def review_status(self, investigation_id: str) -> str | None:
        """Trạng thái phiên bản hồ sơ mới nhất (``None`` khi chưa có hồ sơ).

        ``run_status=completed`` không nói lên hồ sơ đã được duyệt hay bị từ chối, nên API trả
        riêng trường này để giao diện không tự suy diễn.
        """
        dossier = self.latest_dossier(investigation_id)
        return str(dossier.status) if dossier is not None else None

    def timestamps(self, investigation_id: str) -> dict[str, str | None]:
        """``created_at``/``updated_at`` của một cuộc điều tra (để API khỏi bịa mốc thời gian)."""
        with self._lock:
            row = self._conn.execute(
                "SELECT created_at, updated_at FROM investigations WHERE id = ?", (investigation_id,)
            ).fetchone()
        if row is None:
            return {"created_at": None, "updated_at": None}
        return {"created_at": row["created_at"], "updated_at": row["updated_at"]}

    def last_review(self, investigation_id: str) -> dict[str, Any] | None:
        """Quyết định review mới nhất của con người, bất kể checkpoint nào.

        ``review_status`` chỉ nói về phiên bản hồ sơ; một ca bị từ chối ở checkpoint ``assessment``
        không có hồ sơ nào nên vẫn là ``None``. Trường này giữ lại dấu vết con người đã can thiệp.
        """
        with self._lock:
            row = self._conn.execute(
                """SELECT action, checkpoint, created_at FROM review_decisions
                   WHERE investigation_id = ? ORDER BY created_at DESC, rowid DESC LIMIT 1""",
                (investigation_id,),
            ).fetchone()
        if row is None:
            return None
        return _last_review_payload(row["action"], row["checkpoint"], row["created_at"])

    def mark_running_as_interrupted(self) -> list[str]:
        """Phục hồi sau restart/crash: run đang dở → ``interrupted``, giữ nguyên counters/checkpoint."""
        with self._lock, self._conn:
            rows = self._conn.execute(
                "SELECT id FROM investigations WHERE run_status IN (?, ?)",
                (str(RunStatus.RUNNING), str(RunStatus.QUEUED)),
            ).fetchall()
            identifiers = [row["id"] for row in rows]
        recovered: list[str] = []
        for identifier in identifiers:
            state = self.get_state(identifier)
            if state.run_status is RunStatus.QUEUED:
                continue
            updated = state.model_copy(
                update={"run_status": RunStatus.INTERRUPTED, "stop_reason": None}
            )
            self.save_state(updated, event=("interrupted", "Tiến trình dừng bất thường; đánh dấu interrupted."))
            self.audit(identifier, "system", "recovered_interrupted", {"version": updated.version})
            recovered.append(identifier)
        return recovered

    # ----------------------------------------------------------------------------------
    # Events / audit
    # ----------------------------------------------------------------------------------

    def _append_event(self, investigation_id: str, kind: str, message: str, payload: dict | None = None) -> int:
        cursor = self._conn.execute(
            "INSERT INTO events (investigation_id, kind, message, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (investigation_id, kind, message, json.dumps(payload or {}, ensure_ascii=False), now_iso()),
        )
        return int(cursor.lastrowid or 0)

    def append_event(self, investigation_id: str, kind: str, message: str = "", payload: dict | None = None) -> int:
        with self._lock, self._conn:
            return self._append_event(investigation_id, kind, message, payload)

    def list_events(self, investigation_id: str, *, after_id: int = 0, limit: int = 200) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """SELECT id, kind, message, payload_json, created_at FROM events
                   WHERE investigation_id = ? AND id > ? ORDER BY id ASC LIMIT ?""",
                (investigation_id, after_id, limit),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "kind": row["kind"],
                "message": row["message"],
                "payload": json.loads(row["payload_json"] or "{}"),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def _audit(
        self,
        investigation_id: str | None,
        actor: str,
        action: str,
        payload: dict | None = None,
        *,
        actor_role: str | None = None,
        request_id: str | None = None,
    ) -> None:
        # Mã yêu cầu lấy từ middleware khi lời gọi không truyền tường minh, để dòng nhật ký trùng
        # với ``request_id`` mà người dùng thấy trong phản hồi lỗi.
        self._conn.execute(
            """INSERT INTO audit_events
               (investigation_id, actor, actor_role, action, request_id, payload_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                investigation_id,
                actor,
                actor_role,
                action,
                request_id if request_id is not None else current_request_id(),
                json.dumps(payload or {}, ensure_ascii=False),
                now_iso(),
            ),
        )

    def audit(
        self,
        investigation_id: str | None,
        actor: str,
        action: str,
        payload: dict | None = None,
        *,
        actor_role: str | None = None,
        request_id: str | None = None,
    ) -> None:
        """Ghi nhật ký. ``actor`` là **mã người** (AUTH-03), ``actor_role`` để vẫn lọc được theo vai."""
        with self._lock, self._conn:
            self._audit(investigation_id, actor, action, payload, actor_role=actor_role, request_id=request_id)

    def list_audit(
        self,
        investigation_id: str | None = None,
        limit: int = 200,
        *,
        actor: str | None = None,
    ) -> list[dict[str, Any]]:
        """Nhật ký append-only. ``actor`` lọc theo mã người (dùng cho phạm vi ``audit:read:own``)."""
        clauses: list[str] = []
        params: list[Any] = []
        if investigation_id is not None:
            clauses.append("investigation_id = ?")
            params.append(investigation_id)
        if actor is not None:
            clauses.append("actor = ?")
            params.append(actor)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._lock:
            rows = self._conn.execute(
                f"SELECT * FROM audit_events {where} ORDER BY id ASC LIMIT ?", (*params, limit)
            ).fetchall()
        result = []
        for row in rows:
            result.append(_audit_row(row))
        return result

    def list_audit_scoped(
        self,
        *,
        user_id: str,
        limit: int = 200,
        investigation_id: str | None = None,
        actor: str | None = None,
    ) -> list[dict[str, Any]]:
        """Nhật ký trong phạm vi một người: ca do họ tạo, hoặc hành động của chính họ.

        Phạm vi lọc nằm trong câu truy vấn, không lọc sau ``LIMIT`` — nếu không, một người có
        nhiều bản ghi sẽ đẩy bản ghi của người khác vào trang và bị cắt mất.
        """
        clauses = ["(investigation_id IN (SELECT id FROM investigations WHERE created_by = ?) OR actor = ?)"]
        params: list[Any] = [user_id, user_id]
        if investigation_id is not None:
            clauses.append("investigation_id = ?")
            params.append(investigation_id)
        if actor is not None:
            clauses.append("actor = ?")
            params.append(actor)
        with self._lock:
            rows = self._conn.execute(
                f"SELECT * FROM audit_events WHERE {' AND '.join(clauses)} ORDER BY id ASC LIMIT ?",
                (*params, limit),
            ).fetchall()
        return [_audit_row(row) for row in rows]

    # ----------------------------------------------------------------------------------
    # Documents / evidence
    # ----------------------------------------------------------------------------------

    def save_document(self, investigation_id: str, document: SourceDocument) -> bool:
        """Lưu tài liệu bất biến và liên kết với cuộc điều tra; trả True nếu liên kết là mới.

        Nội dung tài liệu dùng chung giữa các cuộc điều tra (khoá ``(source, source_id, version)``);
        mỗi cuộc điều tra có một liên kết riêng trong ``investigation_documents`` nên cùng một tài liệu
        vẫn đọc được ở cuộc điều tra thứ hai.
        """
        with self._lock, self._conn:
            existing = self._conn.execute(
                "SELECT doc_id, hash FROM documents WHERE source = ? AND source_id = ? AND version = ?",
                (document.source, document.source_id, document.version),
            ).fetchone()
            if existing is not None:
                if existing["hash"] != document.hash:
                    raise invalid_state(
                        "Cùng (source, source_id, version) nhưng hash khác — tài liệu là bất biến.",
                        {"doc_id": document.doc_id, "source_id": document.source_id},
                    )
                if existing["doc_id"] != document.doc_id:
                    # Nội dung dùng chung nhưng doc_id không ổn định ⇒ bằng chứng sẽ trỏ sai tài liệu.
                    raise invalid_state(
                        "Cùng (source, source_id, version) nhưng doc_id khác — doc_id phải ổn định theo tài liệu.",
                        {"doc_id": document.doc_id, "existing_doc_id": existing["doc_id"]},
                    )
            else:
                taken = self._conn.execute(
                    "SELECT source_id FROM documents WHERE doc_id = ?", (document.doc_id,)
                ).fetchone()
                if taken is not None:
                    raise invalid_state(
                        "doc_id đã tồn tại với nội dung khác — tài liệu là bất biến.",
                        {"doc_id": document.doc_id, "existing_source_id": taken["source_id"]},
                    )
                self._conn.execute(
                    """INSERT INTO documents
                       (doc_id, investigation_id, source, source_id, version, hash, text, payload_json, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        document.doc_id,
                        investigation_id,
                        document.source,
                        document.source_id,
                        document.version,
                        document.hash,
                        document.text,
                        document.model_dump_json(),
                        now_iso(),
                    ),
                )
            cursor = self._conn.execute(
                """INSERT OR IGNORE INTO investigation_documents (investigation_id, doc_id, created_at)
                   VALUES (?, ?, ?)""",
                (investigation_id, document.doc_id, now_iso()),
            )
        return cursor.rowcount > 0

    def get_document(self, investigation_id: str, doc_id: str) -> SourceDocument:
        with self._lock:
            row = self._conn.execute(
                """SELECT d.payload_json FROM documents d
                   JOIN investigation_documents a ON a.doc_id = d.doc_id
                   WHERE a.investigation_id = ? AND d.doc_id = ?""",
                (investigation_id, doc_id),
            ).fetchone()
        if row is None:
            raise not_found("tài liệu", doc_id)
        return SourceDocument.model_validate(json.loads(row["payload_json"]))

    def list_documents(self, investigation_id: str) -> list[SourceDocument]:
        with self._lock:
            rows = self._conn.execute(
                """SELECT d.payload_json FROM documents d
                   JOIN investigation_documents a ON a.doc_id = d.doc_id
                   WHERE a.investigation_id = ?
                   ORDER BY d.created_at ASC""",
                (investigation_id,),
            ).fetchall()
        return [SourceDocument.model_validate(json.loads(row["payload_json"])) for row in rows]

    def _insert_evidence_version(self, investigation_id: str, evidence: EvidenceUnit, *, version: int | None = None) -> None:
        """Ghi thêm một phiên bản bằng chứng. Gọi trong giao dịch đang mở của người gọi."""
        record_version = version or evidence.version
        self._conn.execute(
            """INSERT INTO evidence_versions
               (evidence_id, investigation_id, version, doc_id, stance, excluded, payload_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                evidence.evidence_id,
                investigation_id,
                record_version,
                evidence.doc_id,
                str(evidence.stance),
                1 if evidence.excluded else 0,
                evidence.model_copy(update={"version": record_version}).model_dump_json(),
                now_iso(),
            ),
        )

    def save_evidence(self, investigation_id: str, evidence: EvidenceUnit, *, version: int | None = None) -> EvidenceUnit:
        record_version = version or evidence.version
        with self._lock, self._conn:
            self._insert_evidence_version(investigation_id, evidence, version=version)
        return evidence.model_copy(update={"version": record_version})

    def list_evidence(self, investigation_id: str, *, include_excluded: bool = True) -> list[EvidenceUnit]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT payload_json, version FROM evidence_versions WHERE investigation_id = ?",
                (investigation_id,),
            ).fetchall()
        latest: dict[str, tuple[int, EvidenceUnit]] = {}
        for row in rows:
            item = EvidenceUnit.model_validate(json.loads(row["payload_json"]))
            current = latest.get(item.evidence_id)
            if current is None or row["version"] > current[0]:
                latest[item.evidence_id] = (int(row["version"]), item)
        items = [item for _, item in latest.values()]
        if not include_excluded:
            items = [item for item in items if not item.excluded]
        return items

    # ----------------------------------------------------------------------------------
    # Reviews / dossier
    # ----------------------------------------------------------------------------------

    def _insert_review_decision(
        self,
        decision: ReviewDecision,
        *,
        result_version: int | None = None,
        result_status: str | None = None,
        actor_role: str | None = None,
    ) -> None:
        """Ghi một quyết định review. Gọi trong giao dịch đang mở của người gọi."""
        self._conn.execute(
            """INSERT INTO review_decisions
               (decision_id, investigation_id, checkpoint, action, reviewer_id, actor_role, reason,
                expected_version, result_version, result_status, payload_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                decision.decision_id,
                decision.investigation_id,
                str(decision.checkpoint),
                str(decision.action),
                decision.reviewer_id,
                actor_role,
                decision.reason,
                decision.expected_version,
                result_version,
                result_status,
                decision.model_dump_json(),
                decision.created_at.isoformat(),
            ),
        )

    # ------------------------------------------------------------------ chạy tiếp (RV-06)

    def register_resume_request(self, investigation_id: str, token: str) -> bool:
        """Ghi nhận một yêu cầu chạy tiếp; ``True`` nếu đây là lần đầu.

        RV-06: trước đây việc chống double-click nằm trong RAM của tiến trình API. Khởi động lại
        tiến trình là mất, và khi có nhiều tiến trình thì mỗi tiến trình nhớ một kiểu. Ghi xuống
        kho thì khoá chống lặp sống sót qua khởi động lại và dùng chung cho mọi tiến trình.
        """
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "INSERT OR IGNORE INTO resume_requests (investigation_id, token, created_at) VALUES (?, ?, ?)",
                (investigation_id, token, now_iso()),
            )
            return cursor.rowcount == 1

    def has_resume_request(self, investigation_id: str, token: str) -> bool:
        """Đã từng nhận yêu cầu chạy tiếp với token này chưa (chỉ đọc, không tiêu thụ khoá).

        Cần hàm chỉ đọc vì thứ tự kiểm tra quan trọng: một cú bấm trùng phải được nhận ra **trước**
        khi kiểm phiên bản — lượt chạy nền do cú bấm đầu tiên khởi động làm phiên bản nhảy liên tục,
        nên nếu kiểm phiên bản trước thì cú bấm thứ hai bị trả 409 thay vì câu trả lời "đã xử lý rồi".
        """
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM resume_requests WHERE investigation_id = ? AND token = ?",
                (investigation_id, token),
            ).fetchone()
        return row is not None

    def forget_resume_request(self, investigation_id: str, token: str) -> None:
        """Bỏ ghi nhận khi lần chạy tiếp không thực sự bắt đầu (lỗi/không chiếm được khoá)."""
        with self._lock, self._conn:
            self._conn.execute(
                "DELETE FROM resume_requests WHERE investigation_id = ? AND token = ?",
                (investigation_id, token),
            )

    def commit_review(
        self,
        decision: ReviewDecision,
        state: InvestigationState,
        *,
        expected_version: int,
        event: tuple[str, str],
        dossier_status: tuple[int, ReviewStatus, str | None, datetime | None] | None = None,
        evidence: EvidenceUnit | None = None,
        invalidate_dossiers: bool = False,
        actor_role: str | None = None,
    ) -> InvestigationState:
        """Áp dụng một quyết định review trong **một** giao dịch (RV-07).

        Trước đây quyết định được ghi trước rồi mới áp dụng từng bước, nên một quyết định sai vẫn
        nằm lại trong nhật ký, và hai người duyệt cùng lúc thì người sau ghi đè người trước.
        Ở đây mọi thay đổi (bằng chứng, hồ sơ, state, quyết định, sự kiện, nhật ký) hoặc cùng
        thành công, hoặc cùng không. Giao dịch tự kiểm tra lại ``expected_version`` ngay trước khi
        ghi, nên một cập nhật xen giữa sẽ làm quyết định cũ bị từ chối bằng 409 thay vì bị ghi đè.
        """
        investigation_id = state.investigation_id
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT version FROM investigations WHERE id = ?", (investigation_id,)
            ).fetchone()
            if row is None:
                raise not_found("cuộc điều tra", investigation_id)
            current = int(row["version"])
            if current != expected_version:
                raise version_conflict(expected_version, current)

            if evidence is not None:
                self._insert_evidence_version(investigation_id, evidence)

            if dossier_status is not None:
                version, status, approved_by, approved_at = dossier_status
                self._set_dossier_status(
                    investigation_id, version, status, approved_by=approved_by, approved_at=approved_at
                )
                self._audit(
                    investigation_id,
                    approved_by or decision.reviewer_id,
                    "dossier_status_changed",
                    {"version": version, "status": str(status)},
                    actor_role=actor_role,
                )

            if invalidate_dossiers:
                for version in self._invalidate_dossiers(investigation_id):
                    # Hồ sơ bị vô hiệu do quyết định này, nên quy về người ra quyết định.
                    self._audit(
                        investigation_id,
                        decision.reviewer_id,
                        "dossier_status_changed",
                        {"version": version, "status": str(ReviewStatus.REJECTED)},
                        actor_role=actor_role,
                    )

            updated = state.model_copy(update={"version": current + 1, "updated_at": datetime.now(UTC)})
            cursor = self._conn.execute(
                """UPDATE investigations
                   SET state_json = ?, claim_json = ?, run_status = ?, assessment_status = ?,
                       checkpoint = ?, next_stage = ?, version = ?, updated_at = ?
                   WHERE id = ? AND version = ?""",
                (
                    updated.model_dump_json(),
                    updated.claim.model_dump_json(),
                    str(updated.run_status),
                    str(updated.assessment_status) if updated.assessment_status else None,
                    str(updated.checkpoint) if updated.checkpoint else None,
                    updated.next_stage,
                    updated.version,
                    updated.updated_at.isoformat(),
                    investigation_id,
                    current,
                ),
            )
            if cursor.rowcount != 1:
                # Chốt thứ hai ở tầng SQL: nếu ai đó chen vào giữa hai lệnh, cả giao dịch bị hủy.
                raise version_conflict(expected_version, current)

            self._insert_review_decision(
                decision,
                result_version=updated.version,
                result_status=str(updated.run_status),
                actor_role=actor_role,
            )
            self._conn.execute(
                "INSERT INTO events (investigation_id, kind, message, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
                (investigation_id, event[0], event[1], "{}", now_iso()),
            )
            self._audit(
                investigation_id,
                decision.reviewer_id,
                f"review_{decision.action}",
                {
                    "decision_id": decision.decision_id,
                    "checkpoint": str(decision.checkpoint),
                    "expected_version": decision.expected_version,
                    "result_version": updated.version,
                },
                actor_role=actor_role,
            )
        return updated

    def list_review_decisions(self, investigation_id: str) -> list[ReviewDecision]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT payload_json FROM review_decisions WHERE investigation_id = ? ORDER BY created_at ASC",
                (investigation_id,),
            ).fetchall()
        return [ReviewDecision.model_validate(json.loads(row["payload_json"])) for row in rows]

    def get_review_decision(self, decision_id: str) -> ReviewDecision | None:
        """Đọc một quyết định review theo ID (dùng để chặn replay)."""
        with self._lock:
            row = self._conn.execute(
                "SELECT payload_json FROM review_decisions WHERE decision_id = ?", (decision_id,)
            ).fetchone()
        return ReviewDecision.model_validate(json.loads(row["payload_json"])) if row else None

    def _set_dossier_status(
        self,
        investigation_id: str,
        version: int,
        status: ReviewStatus,
        *,
        approved_by: str | None = None,
        approved_at: datetime | None = None,
    ) -> Dossier:
        """Ghi trạng thái hồ sơ. Gọi trong giao dịch đang mở của người gọi.

        OUT-05: **không** xóa dấu duyệt cũ khi không có dấu duyệt mới. Trước đây hàm này luôn gán
        ``approved_by``/``approved_at`` theo tham số (mặc định ``None``), nên chỉ cần một hồ sơ đã
        duyệt bị đẩy sang "từ chối" là mất luôn bằng chứng ai đã duyệt và duyệt lúc nào.
        """
        row = self._conn.execute(
            "SELECT payload_json FROM dossier_versions WHERE investigation_id = ? AND version = ?",
            (investigation_id, version),
        ).fetchone()
        if row is None:
            raise not_found(f"Không có hồ sơ phiên bản {version}.", {"investigation_id": investigation_id})
        dossier = Dossier.model_validate(json.loads(row["payload_json"]))
        updated = dossier.model_copy(
            update={
                "status": status,
                "approved_by": approved_by if approved_by is not None else dossier.approved_by,
                "approved_at": approved_at if approved_at is not None else dossier.approved_at,
            }
        )
        self._conn.execute(
            """UPDATE dossier_versions SET status = ?, payload_json = ?, approved_by = ?, approved_at = ?
               WHERE investigation_id = ? AND version = ?""",
            (
                str(status),
                updated.model_dump_json(),
                updated.approved_by,
                updated.approved_at.isoformat() if updated.approved_at else None,
                investigation_id,
                version,
            ),
        )
        return updated

    def _invalidate_dossiers(self, investigation_id: str) -> list[int]:
        """Vô hiệu hóa mọi hồ sơ chưa bị từ chối. Gọi trong giao dịch đang mở của người gọi."""
        versions = [
            int(row["version"])
            for row in self._conn.execute(
                "SELECT version FROM dossier_versions WHERE investigation_id = ? AND status != 'rejected'",
                (investigation_id,),
            ).fetchall()
        ]
        for version in versions:
            self._set_dossier_status(investigation_id, version, ReviewStatus.REJECTED)
        return versions

    def save_dossier(self, dossier: Dossier) -> Dossier:
        with self._lock, self._conn:
            existing = self._conn.execute(
                "SELECT version FROM dossier_versions WHERE investigation_id = ? AND version = ?",
                (dossier.investigation_id, dossier.version),
            ).fetchone()
            if existing is not None:
                raise version_conflict(dossier.version, dossier.version)
            self._conn.execute(
                """INSERT INTO dossier_versions
                   (dossier_id, investigation_id, version, status, payload_json, created_at, approved_at, approved_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    dossier.dossier_id,
                    dossier.investigation_id,
                    dossier.version,
                    str(dossier.status),
                    dossier.model_dump_json(),
                    dossier.created_at.isoformat(),
                    dossier.approved_at.isoformat() if dossier.approved_at else None,
                    dossier.approved_by,
                ),
            )
            self._audit(
                dossier.investigation_id,
                dossier.approved_by or "system",
                "dossier_saved",
                {"version": dossier.version, "status": str(dossier.status)},
            )
        return dossier

    def latest_dossier(self, investigation_id: str) -> Dossier | None:
        with self._lock:
            row = self._conn.execute(
                """SELECT payload_json FROM dossier_versions WHERE investigation_id = ?
                   ORDER BY version DESC LIMIT 1""",
                (investigation_id,),
            ).fetchone()
        return Dossier.model_validate(json.loads(row["payload_json"])) if row else None

    def approved_dossier(self, investigation_id: str) -> Dossier | None:
        with self._lock:
            row = self._conn.execute(
                """SELECT payload_json FROM dossier_versions WHERE investigation_id = ? AND status = 'approved'
                   ORDER BY version DESC LIMIT 1""",
                (investigation_id,),
            ).fetchone()
        return Dossier.model_validate(json.loads(row["payload_json"])) if row else None

    def list_dossiers(self, investigation_id: str) -> list[Dossier]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT payload_json FROM dossier_versions WHERE investigation_id = ? ORDER BY version ASC",
                (investigation_id,),
            ).fetchall()
        return [Dossier.model_validate(json.loads(row["payload_json"])) for row in rows]

    def count_investigations(self, *, created_by: str | None = None) -> int:
        """Tổng số cuộc điều tra khớp bộ lọc — để API trả ``total`` mà không đếm bằng độ dài trang."""
        where = "WHERE created_by = ?" if created_by is not None else ""
        params: tuple[Any, ...] = (created_by,) if created_by is not None else ()
        with self._lock:
            row = self._conn.execute(f"SELECT COUNT(*) AS n FROM investigations {where}", params).fetchone()
        return int(row["n"]) if row is not None else 0

    # ----------------------------------------------------------------------------------
    # Người dùng, khoá máy, phiên (AUTH-01/02/03)
    # ----------------------------------------------------------------------------------

    def create_user(
        self,
        *,
        user_id: str,
        email: str,
        role: str,
        display_name: str = "",
        password_hash: str | None = None,
        created_by: str = "system",
        actor_role: str | None = None,
    ) -> dict[str, Any]:
        """Tạo tài khoản. ``email`` duy nhất — trùng thì ném lỗi ràng buộc của cơ sở dữ liệu.

        ``created_by`` là **mã người cấp tài khoản**; sự kiện được ghi nhật ký trong cùng giao dịch
        với INSERT, nên không có tài khoản nào tồn tại mà không rõ ai tạo.
        """
        timestamp = now_iso()
        with self._lock, self._conn:
            self._conn.execute(
                """INSERT INTO app_users
                   (user_id, email, display_name, role, status, password_hash, created_at, updated_at, created_by)
                   VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?)""",
                (user_id, email.lower().strip(), display_name or email, role, password_hash, timestamp, timestamp, created_by),
            )
            self._audit(
                None,
                created_by,
                "user_created",
                {"user_id": user_id, "email": email.lower().strip(), "role": role},
                actor_role=actor_role,
            )
        return self.get_user(user_id)

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM app_users WHERE user_id = ?", (user_id,)).fetchone()
        return dict(row) if row is not None else None

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM app_users WHERE email = ?", (email.lower().strip(),)
            ).fetchone()
        return dict(row) if row is not None else None

    def list_users(self, *, limit: int = 200, offset: int = 0) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM app_users ORDER BY created_at ASC LIMIT ? OFFSET ?", (limit, max(offset, 0))
            ).fetchall()
        return [dict(row) for row in rows]

    def update_user(
        self,
        user_id: str,
        *,
        role: str | None = None,
        status: str | None = None,
        display_name: str | None = None,
        password_hash: str | None = None,
        actor: str = "system",
        actor_role: str | None = None,
    ) -> dict[str, Any] | None:
        """Đổi vai/trạng thái. Đổi vai hoặc khoá tài khoản thì **thu hồi mọi phiên** của người đó.

        ``actor`` là **mã người thực hiện** thay đổi, không phải người bị đổi — nhật ký phải trả lời
        được "ai đã cấp quyền cho ai".
        """
        fields: list[str] = []
        params: list[Any] = []
        for column, value in (
            ("role", role),
            ("status", status),
            ("display_name", display_name),
            ("password_hash", password_hash),
        ):
            if value is not None:
                fields.append(f"{column} = ?")
                params.append(value)
        if not fields:
            return self.get_user(user_id)
        fields.append("updated_at = ?")
        params.append(now_iso())
        params.append(user_id)
        with self._lock, self._conn:
            cur = self._conn.execute(f"UPDATE app_users SET {', '.join(fields)} WHERE user_id = ?", params)
            if cur.rowcount == 0:
                return None
            if role is not None or status is not None:
                self._conn.execute(
                    "UPDATE sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
                    (now_iso(), user_id),
                )
                # B1.7 mục 3: đổi vai và khoá tài khoản phải để lại vết. Ghi **sau** khi đã thu hồi
                # phiên, trong cùng giao dịch, để nhật ký không bao giờ nói dối về trạng thái.
                self._audit(
                    None,
                    actor,
                    "user_role_changed" if role is not None else "user_status_changed",
                    {"user_id": user_id, "role": role, "status": status},
                    actor_role=actor_role,
                )
        return self.get_user(user_id)

    def issue_token(self, *, user_id: str, raw_token: str, label: str = "", expires_at: str | None = None) -> str:
        """Lưu **băm** của khoá máy; trả về chính băm đó làm khoá chính."""
        from src.services.identity import hash_token

        digest = hash_token(raw_token)
        with self._lock, self._conn:
            self._conn.execute(
                """INSERT INTO api_tokens (token_hash, user_id, label, created_at, expires_at, revoked_at)
                   VALUES (?, ?, ?, ?, ?, NULL)""",
                (digest, user_id, label, now_iso(), expires_at),
            )
        return digest

    def resolve_token(self, raw_token: str) -> dict[str, Any] | None:
        """Tra tài khoản theo khoá thô; ``None`` khi khoá lạ, đã thu hồi, hết hạn, hoặc tài khoản bị khoá."""
        from src.services.identity import hash_token

        digest = hash_token(raw_token)
        with self._lock:
            row = self._conn.execute(
                """SELECT t.token_hash, t.user_id, t.expires_at, t.revoked_at,
                          u.email, u.display_name, u.role, u.status
                   FROM api_tokens AS t
                   JOIN app_users AS u ON u.user_id = t.user_id
                   WHERE t.token_hash = ?""",
                (digest,),
            ).fetchone()
        if row is None or row["revoked_at"] is not None:
            return None
        if row["expires_at"] is not None and row["expires_at"] <= now_iso():
            return None
        if row["status"] != "active":
            return None
        return dict(row)

    def revoke_token(self, raw_token: str) -> bool:
        from src.services.identity import hash_token

        with self._lock, self._conn:
            cur = self._conn.execute(
                "UPDATE api_tokens SET revoked_at = ? WHERE token_hash = ? AND revoked_at IS NULL",
                (now_iso(), hash_token(raw_token)),
            )
            return cur.rowcount > 0

    # ----------------------------------------------------------------------------------
    # Sessions
    # ----------------------------------------------------------------------------------

    def create_session(self, user_id: str, role: str, expires_in_seconds: int = 43200) -> str:
        """Phiên nội bộ, TTL 12 giờ (B1.4). Vai chỉ để đối chiếu — quyền luôn đọc từ ``app_users``."""
        from datetime import timedelta

        session_id = f"sess_{uuid4().hex}"
        created = datetime.now(UTC)
        expires = created + timedelta(seconds=expires_in_seconds)
        with self._lock, self._conn:
            self._conn.execute(
                """INSERT INTO sessions (session_id, user_id, role, created_at, expires_at, revoked_at)
                   VALUES (?, ?, ?, ?, ?, NULL)""",
                (session_id, user_id, role, created.isoformat(), expires.isoformat()),
            )
        return session_id

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self._lock, self._conn:
            row = self._conn.execute(
                """SELECT session_id, user_id, role, created_at, expires_at, revoked_at
                   FROM sessions WHERE session_id = ?""",
                (session_id,),
            ).fetchone()
            if row is None:
                return None
            if row["revoked_at"] is not None:
                return None
            if row["expires_at"] <= now_iso():
                self._conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
                return None
            return {
                "session_id": row["session_id"],
                "user_id": row["user_id"],
                "role": row["role"],
                "created_at": row["created_at"],
                "expires_at": row["expires_at"],
            }

    def revoke_session(self, session_id: str) -> bool:
        """Thu hồi phiên (đăng xuất). Giữ lại bản ghi để nhật ký còn đối chiếu được."""
        with self._lock, self._conn:
            cur = self._conn.execute(
                "UPDATE sessions SET revoked_at = ? WHERE session_id = ? AND revoked_at IS NULL",
                (now_iso(), session_id),
            )
            return cur.rowcount > 0
