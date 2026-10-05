"""Back up/restore the stopped local MVP database and immutable raw snapshots."""

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path


def inventory(folder):
    folder = Path(folder)
    root = folder.resolve()
    if folder.is_symlink() or (hasattr(folder, "is_junction") and folder.is_junction()):
        raise ValueError("Snapshot/backup links are not allowed")
    files = {}
    for path in folder.rglob("*"):
        if (
            path.is_symlink()
            or (hasattr(path, "is_junction") and path.is_junction())
            or not path.resolve().is_relative_to(root)
        ):
            raise ValueError("Snapshot/backup links are not allowed")
        if path.is_file():
            files[path.relative_to(folder).as_posix()] = path
    return files


def verify(folder):
    folder = Path(folder)
    actual = inventory(folder)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    listed = manifest["files"]
    if "mvp.sqlite3" not in listed or set(actual) != set(listed) | {"manifest.json"}:
        raise ValueError("Backup inventory differs from manifest")
    for relative, digest in manifest["files"].items():
        path = (folder / relative).resolve()
        if not path.is_relative_to(folder.resolve()) or not path.is_file():
            raise ValueError("Missing or unsafe backup file")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("Database/snapshot hash mismatch")
    with closing(
        sqlite3.connect(f"{(folder / 'mvp.sqlite3').resolve().as_uri()}?mode=ro&immutable=1", uri=True)
    ) as connection:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Database integrity check failed")
        documents = connection.execute("SELECT payload_json FROM documents").fetchall()
        for (payload,) in documents:
            document = json.loads(payload)
            if hashlib.sha256(document["text"].encode()).hexdigest() != document["hash"]:
                raise ValueError("Parsed document hash mismatch")
            raw_hash = document.get("metadata", {}).get("raw_hash")
            if raw_hash:
                if not re.fullmatch(r"[0-9a-f]{64}", raw_hash) or document["source"] not in {
                    "pubmed",
                    "dailymed",
                    "faers",
                }:
                    raise ValueError("Invalid snapshot hash/source")
                raw = folder / "snapshots" / document["source"] / f"{raw_hash}.raw"
                if not raw.is_file() or hashlib.sha256(raw.read_bytes()).hexdigest() != raw_hash:
                    raise ValueError("snapshot hash mismatch for source document")
    return {"documents": len(documents), "files": len(manifest["files"])}


def backup(db_path, snapshot_root, output):
    db_path, snapshot_root, output = Path(db_path), Path(snapshot_root), Path(output)
    if output.exists():
        raise FileExistsError("Backup destination already exists")
    if not db_path.is_file():
        raise FileNotFoundError(db_path)
    if output.resolve().is_relative_to(snapshot_root.resolve()):
        raise ValueError("Backup destination cannot be inside snapshots")
    output.mkdir(parents=True)
    with closing(sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)) as source:
        with closing(sqlite3.connect(output / "mvp.sqlite3")) as target:
            source.backup(target)
    if snapshot_root.exists():
        for relative, path in inventory(snapshot_root).items():
            target = output / "snapshots" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    else:
        (output / "snapshots").mkdir()
    files = {
        p.relative_to(output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in output.rglob("*")
        if p.is_file()
    }
    (output / "manifest.json").write_text(json.dumps({"version": 1, "files": files}, indent=2), encoding="utf-8")
    return verify(output)


def restore(source, output):
    source, output = Path(source), Path(output)
    if output.resolve().is_relative_to(source.resolve()):
        raise ValueError("Restore destination cannot be inside source backup")
    result = verify(source)
    if output.exists():
        raise FileExistsError("Restore destination already exists; restore to a new directory")
    output.mkdir(parents=True)
    for relative, path in inventory(source).items():
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    verify(output)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    save = sub.add_parser("backup")
    save.add_argument("--db", default=os.environ.get("MVP_DB_PATH", "data/mvp.sqlite3"))
    save.add_argument("--snapshots", default=os.environ.get("MVP_SNAPSHOT_ROOT", "data/snapshots"))
    save.add_argument("--output", required=True)
    save.add_argument("--stopped", action="store_true", required=True, help="Confirm the app is stopped")
    load = sub.add_parser("restore")
    load.add_argument("--source", required=True)
    load.add_argument("--output", required=True)
    check = sub.add_parser("verify")
    check.add_argument("--source", required=True)
    args = parser.parse_args()
    if args.command == "backup":
        result = backup(args.db, args.snapshots, args.output)
    elif args.command == "restore":
        result = restore(args.source, args.output)
    else:
        result = verify(args.source)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
