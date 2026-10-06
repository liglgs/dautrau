"""Ghi vết mọi lần chạy ELT: run manifest + danh sách artifact tải về.

Mỗi artifact ghi lại URL, tham số, mã trạng thái, băm SHA-256 và đường dẫn cục bộ.
Nhờ vậy một máy mới có thể chạy lại đúng các bước và đối chiếu kết quả.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_sha(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=False, timeout=10,
        )
        return result.stdout.strip() or "unknown"
    except Exception:  # pragma: no cover - môi trường không có git
        return "unknown"


class RunManifest:
    def __init__(self, run_id: str, profile: str, root: Path):
        self.run_id = run_id
        self.profile = profile
        self.root = Path(root)
        self.created_at = datetime.now(UTC).isoformat()
        self.git_sha = git_sha(self.root)
        self.artifacts: list[dict] = []
        self.notes: list[str] = []
        self.stats: dict = {}

    def add_artifact(
        self,
        *,
        source: str,
        kind: str,
        url: str,
        params: dict | None,
        status: int | None,
        payload: bytes | None = None,
        path: str = "",
        error: str | None = None,
        content_type: str = "",
        extra: dict | None = None,
    ) -> dict:
        entry = {
            "artifact_id": f"{source}:{kind}:{len(self.artifacts) + 1:04d}",
            "source": source,
            "kind": kind,
            "url": url,
            "params": params or {},
            "status": status,
            "content_type": content_type,
            "bytes": len(payload) if payload is not None else 0,
            "sha256": sha256_bytes(payload) if payload is not None else "",
            "path": path,
            "error": error,
            "retrieved_at": datetime.now(UTC).isoformat(),
        }
        if extra:
            entry.update(extra)
        self.artifacts.append(entry)
        return entry

    def note(self, message: str) -> None:
        self.notes.append(message)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "profile": self.profile,
            "git_sha": self.git_sha,
            "created_at": self.created_at,
            "artifacts": self.artifacts,
            "notes": self.notes,
            "stats": self.stats,
        }

    def write(self, directory: Path) -> Path:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{self.run_id}.json"
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        latest = directory / "latest.json"
        latest.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return path
