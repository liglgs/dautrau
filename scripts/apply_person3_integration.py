"""Apply the checksum-checked shared-file patch; never edit Git metadata."""

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def apply(root: Path) -> None:
    manifest = json.loads((ROOT / "docs/person3/integration-manifest.json").read_text(encoding="utf-8"))
    statuses = []
    for relative, expected in manifest["files"].items():
        path = root / relative
        if not path.is_file():
            raise RuntimeError(f"Missing {relative}. Merge origin/main before applying integration.")
        digest = hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
        statuses.append("after" if digest == expected["after"] else "before" if digest == expected["before"] else "different")
        if statuses[-1] == "different":
            raise RuntimeError(f"{relative} differs from the reviewed main base; rebase the patch without overwriting local work.")
    if all(status == "after" for status in statuses):
        print("Person 3 integration already applied.")
        return
    if any(status == "after" for status in statuses):
        raise RuntimeError("Partial integration detected. Review before applying again.")
    patch = ROOT / "docs/person3/integration.patch"
    subprocess.run(["git", "apply", "--unidiff-zero", "--check", str(patch)], cwd=root, check=True)
    subprocess.run(["git", "apply", "--unidiff-zero", str(patch)], cwd=root, check=True)
    print(f"Applied Person 3 integration to {len(manifest['files'])} shared files. Git history and stash unchanged.")


if __name__ == "__main__":
    try:
        apply(ROOT)
    except RuntimeError as error:
        raise SystemExit(str(error)) from None
