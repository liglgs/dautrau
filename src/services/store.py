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
    reason TEXT NOT NULL DEFAULT '',
    expected_version INTEGER NOT NULL,
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

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    investigation_id TEXT,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    payload_json TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions (user_id);
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
    ) -> tuple[InvestigationState, bool]:
        """Tạo cuộc điều tra mới; trả ``(state, created)``.

        Cùng ``Idempotency-Key`` + cùng payload → trả bản ghi cũ (``created=False``).
        Cùng key nhưng payload khác → 409 ``idempotency_conflict``.
        """
        request_hash = _hash_request(claim)
        with self._lock, self._conn:
            if idempotency_key:
                row = self._conn.execute(
                    "SELECT id, request_hash FROM investigations WHERE idempotency_key = ?", (idempotency_key,)
                ).fetchone()
                if row is not None:
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
            self._audit(identifier, "system", "investigation_created", {"claim": claim.model_dump()})
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
        event: tuple[str, str] | None = None,
        actor: str = "system",
    ) -> InvestigationState:
        """Lưu state với kiểm tra phiên bản (stale version không được ghi đè)."""
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
            self._conn.execute(
                """UPDATE investigations
                   SET state_json = ?, run_status = ?, assessment_status = ?, checkpoint = ?, next_stage = ?,
                       version = ?, updated_at = ?
                   WHERE id = ?""",
                (
                    updated.model_dump_json(),
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
                self._append_event(updated.investigation_id, event[0], event[1])
            self._audit(
                updated.investigation_id,
                actor,
                "state_saved",
                {"version": updated.version, "run_status": str(updated.run_status)},
            )
        return updated

    def list_investigations(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """SELECT i.id, i.run_status, i.assessment_status, i.checkpoint, i.next_stage,
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
                   ORDER BY i.updated_at DESC LIMIT ?""",
                (limit,),
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

    def _audit(self, investigation_id: str | None, actor: str, action: str, payload: dict | None = None) -> None:
        self._conn.execute(
            "INSERT INTO audit_events (investigation_id, actor, action, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (investigation_id, actor, action, json.dumps(payload or {}, ensure_ascii=False), now_iso()),
        )

    def audit(self, investigation_id: str | None, actor: str, action: str, payload: dict | None = None) -> None:
        with self._lock, self._conn:
            self._audit(investigation_id, actor, action, payload)

    def list_audit(self, investigation_id: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        with self._lock:
            if investigation_id is None:
                rows = self._conn.execute(
                    "SELECT * FROM audit_events ORDER BY id ASC LIMIT ?", (limit,)
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM audit_events WHERE investigation_id = ? ORDER BY id ASC LIMIT ?",
                    (investigation_id, limit),
                ).fetchall()
        return [
            {
                "id": row["id"],
                "investigation_id": row["investigation_id"],
                "actor": row["actor"],
                "action": row["action"],
                "payload": json.loads(row["payload_json"] or "{}"),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

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

    def save_evidence(self, investigation_id: str, evidence: EvidenceUnit, *, version: int | None = None) -> EvidenceUnit:
        record_version = version or evidence.version
        with self._lock, self._conn:
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

    def save_review_decision(self, decision: ReviewDecision) -> ReviewDecision:
        with self._lock, self._conn:
            self._conn.execute(
                """INSERT INTO review_decisions
                   (decision_id, investigation_id, checkpoint, action, reviewer_id, reason, expected_version,
                    payload_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    decision.decision_id,
                    decision.investigation_id,
                    str(decision.checkpoint),
                    str(decision.action),
                    decision.reviewer_id,
                    decision.reason,
                    decision.expected_version,
                    decision.model_dump_json(),
                    decision.created_at.isoformat(),
                ),
            )
            self._audit(
                decision.investigation_id,
                decision.reviewer_id,
                f"review_{decision.action}",
                {"checkpoint": str(decision.checkpoint), "expected_version": decision.expected_version},
            )
        return decision

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

    def update_dossier_status(
        self,
        investigation_id: str,
        version: int,
        status: ReviewStatus,
        *,
        approved_by: str | None = None,
        approved_at: datetime | None = None,
    ) -> Dossier:
        """Cập nhật trạng thái một phiên bản hồ sơ (duyệt/từ chối/vô hiệu)."""
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT payload_json FROM dossier_versions WHERE investigation_id = ? AND version = ?",
                (investigation_id, version),
            ).fetchone()
            if row is None:
                raise not_found(f"Không có hồ sơ phiên bản {version}.", {"investigation_id": investigation_id})
            dossier = Dossier.model_validate(json.loads(row["payload_json"]))
            updated = dossier.model_copy(
                update={"status": status, "approved_by": approved_by, "approved_at": approved_at}
            )
            self._conn.execute(
                """UPDATE dossier_versions SET status = ?, payload_json = ?, approved_by = ?, approved_at = ?
                   WHERE investigation_id = ? AND version = ?""",
                (
                    str(status),
                    updated.model_dump_json(),
                    approved_by,
                    approved_at.isoformat() if approved_at else None,
                    investigation_id,
                    version,
                ),
            )
            self._audit(
                investigation_id,
                approved_by or "system",
                "dossier_status_changed",
                {"version": version, "status": str(status)},
            )
        return updated

    def invalidate_dossiers(self, investigation_id: str) -> list[int]:
        """Vô hiệu hóa mọi phiên bản hồ sơ chưa bị từ chối; trả về danh sách version đã đổi."""
        changed: list[int] = []
        with self._lock:
            versions = [
                int(row["version"])
                for row in self._conn.execute(
                    "SELECT version FROM dossier_versions WHERE investigation_id = ? AND status != 'rejected'",
                    (investigation_id,),
                ).fetchall()
            ]
        for version in versions:
            self.update_dossier_status(investigation_id, version, ReviewStatus.REJECTED)
            changed.append(version)
        return changed

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

    # ----------------------------------------------------------------------------------
    # Sessions
    # ----------------------------------------------------------------------------------

    def create_session(self, user_id: str, role: str, expires_in_seconds: int = 86400) -> str:
        from datetime import timedelta

        session_id = f"sess_{uuid4().hex}"
        created = datetime.now(UTC)
        expires = created + timedelta(seconds=expires_in_seconds)
        with self._lock, self._conn:
            self._conn.execute(
                """INSERT INTO sessions (session_id, user_id, role, created_at, expires_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (session_id, user_id, role, created.isoformat(), expires.isoformat()),
            )
        return session_id

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT session_id, user_id, role, created_at, expires_at FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if row is None:
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

    def delete_session(self, session_id: str) -> bool:
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            return cur.rowcount > 0
