from pathlib import Path
import json, hashlib, re
import httpx

root = Path(__file__).parent
data = root / "data-real"
manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
verified = [r for r in manifest if r["verified_payload"]]
assert len(verified) == 18
assert len({r['id'] for r in manifest}) == len(manifest)
for row in verified:
    assert hashlib.sha256((data / row["file"]).read_bytes()).hexdigest() == row["sha256"]
print("18 payload hashes OK; manifest IDs unique")
fragment = Path("C:/Users/Admin/.codex/visualizations/2026/10/03/01a0ffda-1094-7c20-9926-ecabaebd8e10/vigilens-hospital-workbench.html").read_text(encoding="utf-8")
assert len(fragment.encode()) < 1000000
assert not re.search(r"<!doctype|<html|<body|<head>|fetch\(|XMLHttpRequest|WebSocket", fragment, re.I)
assert '\\"' not in fragment and r'\n' not in fragment
(root / "proposal-script.js").write_text(re.search(r"<script>(.*?)</script>", fragment, re.S)[1], encoding="utf-8")
print("Fragment structure OK")
for url in ["http://127.0.0.1:8000/health", "http://127.0.0.1:3100/login"]:
    response = httpx.get(url, timeout=20)
    print(url, response.status_code)
    assert response.status_code == 200
