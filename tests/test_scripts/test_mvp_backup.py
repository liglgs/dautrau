import hashlib
import os
import sqlite3
import subprocess
import sys

import pytest

from src.models.schemas import ClaimInput, SourceDocument
from src.services.store import MvpStore


@pytest.mark.parametrize("explicit", [False, True])
def test_backup_cli_uses_active_database_and_explicit_path_wins(tmp_path, monkeypatch, explicit):
    active_path = tmp_path / "active.sqlite3"
    original_path = tmp_path / "original.sqlite3"
    active = MvpStore(active_path)
    active_state, _ = active.create_investigation(ClaimInput(claim_text="active", drug="a", event="b"))
    active.close()
    original = MvpStore(original_path)
    original_state, _ = original.create_investigation(ClaimInput(claim_text="original", drug="a", event="b"))
    original.close()
    monkeypatch.setenv("MVP_DB_PATH", str(active_path))
    output = tmp_path / "backup"
    command = [sys.executable, "-m", "scripts.mvp_backup", "backup", "--stopped",
               "--snapshots", str(tmp_path / "snapshots"), "--output", str(output)]
    if explicit:
        command.extend(["--db", str(original_path)])
    result = subprocess.run(command, env=os.environ.copy(), capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    reopened = MvpStore(output / "mvp.sqlite3")
    expected = original_state if explicit else active_state
    assert reopened.get_state(expected.investigation_id).claim.claim_text == expected.claim.claim_text
    reopened.close()


@pytest.mark.parametrize("explicit", [False, True])
def test_backup_cli_uses_active_snapshots_and_explicit_path_wins(tmp_path, monkeypatch, explicit):
    snapshot_root = tmp_path / "restored" / "snapshots"
    raw_folder = snapshot_root / "pubmed"
    raw_folder.mkdir(parents=True)
    raw = b"retrieved after restore"
    digest = hashlib.sha256(raw).hexdigest()
    (raw_folder / f"{digest}.raw").write_bytes(raw)
    db_path = tmp_path / "restored" / "mvp.sqlite3"
    store = MvpStore(db_path)
    state, _ = store.create_investigation(ClaimInput(claim_text="restored", drug="a", event="b"))
    store.save_document(state.investigation_id, SourceDocument(
        doc_id="pubmed:1:1", source="pubmed", source_id="1", text="source quote",
        hash=hashlib.sha256(b"source quote").hexdigest(), metadata={"raw_hash": digest},
    ))
    store.close()
    monkeypatch.setenv("MVP_DB_PATH", str(db_path))
    monkeypatch.setenv("MVP_SNAPSHOT_ROOT", str(tmp_path / "obsolete" if explicit else snapshot_root))
    output = tmp_path / "backup"
    command = [sys.executable, "-m", "scripts.mvp_backup", "backup", "--stopped", "--output", str(output)]
    if explicit:
        command.extend(["--snapshots", str(snapshot_root)])
    result = subprocess.run(command, env=os.environ.copy(), capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert (output / "snapshots" / "pubmed" / f"{digest}.raw").read_bytes() == raw


def test_backup_restores_database_and_verifiable_source(tmp_path):
    from scripts.mvp_backup import backup, restore, verify

    data = tmp_path / "original"
    snapshots = data / "snapshots" / "pubmed"
    snapshots.mkdir(parents=True)
    raw = b"original source"
    digest = hashlib.sha256(raw).hexdigest()
    (snapshots / f"{digest}.raw").write_bytes(raw)
    store = MvpStore(data / "mvp.sqlite3")
    state, _ = store.create_investigation(ClaimInput(claim_text="test", drug="a", event="b"))
    doc = SourceDocument(
        doc_id="pubmed:1:1",
        source="pubmed",
        source_id="1",
        text="source quote",
        hash=hashlib.sha256(b"source quote").hexdigest(),
        metadata={"raw_hash": digest},
    )
    store.save_document(state.investigation_id, doc)
    store.close()
    output = tmp_path / "backup"
    backup(data / "mvp.sqlite3", data / "snapshots", output)
    restored = tmp_path / "restored"
    restore(output, restored)
    assert verify(restored)["documents"] == 1
    reopened = MvpStore(restored / "mvp.sqlite3")
    assert reopened.get_document(state.investigation_id, "pubmed:1:1").text == "source quote"
    reopened.close()
    (output / "snapshots" / "pubmed" / f"{digest}.raw").write_bytes(b"changed")
    with pytest.raises(ValueError, match="snapshot hash"):
        verify(output)


def test_backup_refuses_overwrite(tmp_path):
    from scripts.mvp_backup import backup

    db = tmp_path / "input.sqlite3"
    sqlite3.connect(db).close()
    target = tmp_path / "existing"
    target.mkdir()
    with pytest.raises(FileExistsError):
        backup(db, tmp_path / "snapshots", target)


def test_verify_rejects_unlisted_files_and_restore_descendant(tmp_path):
    from scripts.mvp_backup import backup, restore

    db = tmp_path / "db.sqlite3"
    store = MvpStore(db)
    store.close()
    folder = tmp_path / "backup"
    backup(db, tmp_path / "snapshots", folder)
    with pytest.raises(ValueError, match="inside"):
        restore(folder, folder / "nested")


def test_verify_rejects_unlisted_files(tmp_path):
    from scripts.mvp_backup import backup, verify

    db = tmp_path / "db.sqlite3"
    store = MvpStore(db)
    store.close()
    folder = tmp_path / "backup"
    backup(db, tmp_path / "snapshots", folder)
    (folder / "unlisted.txt").write_text("unverified", encoding="utf-8")
    with pytest.raises(ValueError, match="inventory"):
        verify(folder)


def test_backup_rejects_non_raw_snapshot_symlink(tmp_path):
    from scripts.mvp_backup import backup

    db = tmp_path / "db.sqlite3"
    store = MvpStore(db)
    store.close()
    snapshots = tmp_path / "snapshots"
    snapshots.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    try:
        (snapshots / "linked.txt").symlink_to(outside)
    except OSError:
        pytest.skip("OS does not allow symlink creation")
    with pytest.raises(ValueError, match="link"):
        backup(db, snapshots, tmp_path / "backup")
