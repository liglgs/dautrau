"""Tầng tải dữ liệu (Extract) cho ELT: PubMed, DailyMed, FAERS/openFDA, gói 50 mẫu, gói nghiên cứu.

Mọi yêu cầu mạng đều đi qua :class:`Fetcher` để:
  * giới hạn tần suất theo máy chủ (tôn trọng NCBI/NCBI-key, openFDA, DailyMed);
  * ghi lại URL, tham số, mã trạng thái và băm SHA-256 vào run manifest;
  * lưu bản thô vào ``data/elt/raw/<nguồn>/`` để có thể chạy lại phần Parse mà không cần mạng.

Ngoại lệ mạng không được coi là "không có bằng chứng": chúng được ghi thành lỗi có mã.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from scripts.elt import config
from scripts.elt.manifest import RunManifest, sha256_bytes, sha256_file

EXTENSIONS = {
    "application/json": ".json",
    "text/json": ".json",
    "application/xml": ".xml",
    "text/xml": ".xml",
    "text/html": ".html",
    "application/pdf": ".pdf",
    "text/plain": ".txt",
}


@dataclass
class FetchResult:
    source: str
    kind: str
    url: str
    params: dict = field(default_factory=dict)
    status: int | None = None
    body: bytes = b""
    sha256: str = ""
    path: str = ""
    content_type: str = ""
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == 200 and not self.error


class Fetcher:
    def __init__(self, raw_root: Path, manifest: RunManifest, *, offline: bool = False, force: bool = False):
        self.raw_root = Path(raw_root)
        self.manifest = manifest
        self.offline = offline
        self.force = force
        self._last_call: dict[str, float] = {}
        self._client = httpx.Client(
            timeout=30,
            follow_redirects=False,
            trust_env=False,
            headers={"User-Agent": config.USER_AGENT, "Accept": "*/*"},
        )

    # ------------------------------------------------------------------ hạ tầng
    def _throttle(self, host: str) -> None:
        interval = config.HOST_INTERVAL.get(host, config.DEFAULT_INTERVAL)
        previous = self._last_call.get(host)
        if previous is not None:
            wait = interval - (time.monotonic() - previous)
            if wait > 0:
                time.sleep(wait)
        self._last_call[host] = time.monotonic()

    def _save(self, source: str, kind: str, content_type: str, payload: bytes) -> str:
        extension = EXTENSIONS.get(content_type.split(";")[0].strip(), ".bin")
        directory = self.raw_root / source
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{kind}-{sha256_bytes(payload)[:16]}{extension}"
        if not path.exists():
            path.write_bytes(payload)
        return str(path.relative_to(config.ROOT))

    def get(
        self,
        source: str,
        kind: str,
        url: str,
        params: dict | None = None,
        *,
        headers: dict | None = None,
        retries: int = 2,
        label: str | None = None,
    ) -> FetchResult:
        params = params or {}
        host = httpx.URL(url).host or ""
        if self.offline:
            entry = self.manifest.add_artifact(
                source=source, kind=kind, url=url, params=params, status=None,
                error="offline_mode", extra={"label": label},
            )
            return FetchResult(source, kind, url, params, error="offline_mode")

        last_error = ""
        for attempt in range(retries + 1):
            self._throttle(host)
            try:
                response = self._client.get(url, params=params, headers=headers)
            except httpx.HTTPError as exc:
                last_error = f"network: {exc.__class__.__name__}: {exc}"
                time.sleep(0.8 * (attempt + 1))
                continue
            if response.status_code == 200:
                body = response.content
                if len(body) > config.MAX_BYTES:
                    last_error = f"payload_too_large: {len(body)} bytes"
                    break
                path = self._save(source, kind, response.headers.get("content-type", ""), body)
                entry = self.manifest.add_artifact(
                    source=source, kind=kind, url=url, params=params, status=200, payload=body,
                    path=path, content_type=response.headers.get("content-type", ""),
                    extra={"label": label},
                )
                return FetchResult(source, kind, url, params, 200, body, entry["sha256"], path,
                                   response.headers.get("content-type", ""))
            last_error = f"http_{response.status_code}"
            if response.status_code in {429, 500, 502, 503, 504} and attempt < retries:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if (retry_after or "").isdigit() else 0.8 * (attempt + 1)
                time.sleep(min(delay, 10.0))
                continue
            break
        entry = self.manifest.add_artifact(
            source=source, kind=kind, url=url, params=params,
            status=None, error=last_error, extra={"label": label},
        )
        return FetchResult(source, kind, url, params, None, error=last_error)

    def close(self) -> None:
        self._client.close()


# ------------------------------------------------------------------ PubMed
def fetch_pubmed_by_pmids(fetcher: Fetcher, pmids: list[str]) -> list[FetchResult]:
    results: list[FetchResult] = []
    ids = [p.strip() for p in pmids if p.strip()]
    for start in range(0, len(ids), 50):
        chunk = ids[start:start + 50]
        params = {"db": "pubmed", "id": ",".join(chunk), "retmode": "xml"}
        if config.ncbi_api_key():
            params["api_key"] = config.ncbi_api_key()
        params["tool"] = "vigilens-elt"
        params["email"] = config.ncbi_email()
        results.append(
            fetcher.get(
                "pubmed", "efetch", "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
                params, label=f"pmids:{','.join(chunk)}",
            )
        )
    return results


def fetch_dailymed_index(fetcher: Fetcher, drug: str, pagesize: int = 100) -> FetchResult:
    return fetcher.get(
        "dailymed", "spls-index", "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json",
        {"drug_name": drug, "pagesize": str(pagesize)}, label=f"drug:{drug}",
    )


def fetch_dailymed_label(fetcher: Fetcher, setid: str) -> FetchResult:
    return fetcher.get(
        "dailymed", "spl-label", f"https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/{setid}.xml",
        {}, label=f"setid:{setid}",
    )


def fetch_faers_report(fetcher: Fetcher, report_id: str) -> FetchResult:
    return fetcher.get(
        "faers", "report", "https://api.fda.gov/drug/event.json",
        {"search": f'safetyreportid:"{report_id}"', "limit": "1"}, label=f"report:{report_id}",
    )


# ------------------------------------------------------------------ gói 50 mẫu
def download_bundle(manifest: RunManifest, *, force: bool = False) -> dict:
    """Tải gói ứng viên từ Google Drive bằng ``gdown`` và kiểm băm SHA-256 đã biết."""
    spec = config.bundle_spec()
    zip_path = config.ROOT / spec["zip_to"]
    expected = spec["sha256"]
    if zip_path.exists() and not force:
        actual = sha256_file(zip_path)
        if actual == expected:
            manifest.note(f"bundle: đã có {zip_path.name} và băm khớp")
            return {"zip": str(zip_path.relative_to(config.ROOT)), "sha256": actual, "status": "cached"}
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable, "-m", "gdown", "--folder", "--quiet",
        spec["drive_url"], "-O", str(config.DATA / "drive-bundle"),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=1800)
    downloaded = None
    for candidate in sorted((config.DATA / "drive-bundle").rglob("*.zip")):
        if candidate.name == spec["zip_name"] or sha256_file(candidate) == expected:
            downloaded = candidate
            break
    if downloaded is None:
        manifest.add_artifact(source="bundle", kind="download", url=spec["drive_url"], params={},
                              status=None, error=f"gdown_exit_{result.returncode}: {result.stderr.strip()[:400]}")
        raise RuntimeError(f"Không tải được gói 50 mẫu (gdown exit {result.returncode}).")
    payload = downloaded.read_bytes()
    actual = sha256_bytes(payload)
    if actual != expected:
        manifest.add_artifact(source="bundle", kind="download", url=spec["drive_url"], params={},
                              status=200, payload=payload, error="sha256_mismatch",
                              extra={"expected_sha256": expected, "actual_sha256": actual})
        raise RuntimeError(f"Băm gói tải về không khớp: {actual} != {expected}")
    zip_path.write_bytes(payload)
    manifest.add_artifact(source="bundle", kind="download", url=spec["drive_url"], params={},
                          status=200, payload=payload, path=str(zip_path.relative_to(config.ROOT)),
                          extra={"expected_sha256": expected})
    return {"zip": str(zip_path.relative_to(config.ROOT)), "sha256": actual, "status": "downloaded"}


def extract_bundle(manifest: RunManifest) -> dict:
    """Giải nén và kiểm toàn bộ băm trong ``files.sha256.json`` của gói."""
    spec = config.bundle_spec()
    zip_path = config.ROOT / spec["zip_to"]
    target = config.ROOT / spec["extract_to"]
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(target)
    checksum_file = next(target.rglob("files.sha256.json"))
    expected = json.loads(checksum_file.read_text(encoding="utf-8"))
    if isinstance(expected, dict) and "files" in expected:
        expected = expected["files"]
    verified = 0
    failures: list[str] = []
    for name, digest in expected.items():
        candidate = checksum_file.parent / name
        if not candidate.exists():
            failures.append(f"missing:{name}")
            continue
        actual = sha256_file(candidate)
        if actual != digest:
            failures.append(f"sha256:{name}")
        else:
            verified += 1
    manifest.add_artifact(source="bundle", kind="extract", url=str(zip_path), params={}, status=200,
                          extra={"verified_files": verified, "failed_files": failures,
                                 "total_files": len(expected)})
    return {"extracted_to": str(target.relative_to(config.ROOT)), "verified": verified,
            "total": len(expected), "failures": failures}


# ------------------------------------------------------------------ gói nghiên cứu đã cam kết
def verify_research_packet(manifest: RunManifest) -> dict:
    """Đối chiếu gói nghiên cứu trong repo với manifest.json của chính nó (không cần mạng)."""
    packet = config.RESEARCH_DIR
    index_path = packet / "manifest.json"
    if not index_path.exists():
        manifest.add_artifact(source="research_packet", kind="verify", url=str(packet), params={},
                              status=None, error="manifest_missing")
        return {"verified": 0, "failures": ["manifest_missing"]}
    entries = json.loads(index_path.read_text(encoding="utf-8"))
    if isinstance(entries, dict):
        entries = entries.get("entries", [])
    verified = 0
    normalized: list[str] = []
    failures: list[str] = []
    for entry in entries:
        name = entry.get("file")
        if not name:
            continue
        path = packet / name
        if not path.exists():
            failures.append(f"missing:{name}")
            continue
        actual = sha256_file(path)
        if entry.get("sha256") and actual == entry["sha256"]:
            verified += 1
        elif entry.get("sha256_committed") and actual == entry["sha256_committed"]:
            # Tệp đã được lưu lại khi nhập repo (ví dụ đổi xuống dòng CRLF → LF). Bản cam kết
            # có băm riêng, ghi rõ trong manifest; vẫn là lỗi nếu băm thật khác cả hai.
            verified += 1
            normalized.append(name)
        elif not entry.get("sha256"):
            verified += 1
        else:
            failures.append(f"sha256:{name}")
    manifest.add_artifact(source="research_packet", kind="verify", url=str(packet), params={}, status=200,
                          extra={"verified_files": verified, "failed_files": failures,
                                 "normalized_files": normalized, "total_files": len(entries)})
    return {"verified": verified, "total": len(entries), "failures": failures, "normalized": normalized}
