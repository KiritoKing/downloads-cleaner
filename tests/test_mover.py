from __future__ import annotations

from pathlib import Path

from downloads_cleaner.mover import move_file, resolve_conflict

from tests.conftest import touch_file


def test_move_file_to_new_target(tmp_path: Path) -> None:
    src = touch_file(tmp_path / "Downloads" / "a.pdf")
    target_dir = tmp_path / "Downloads" / "_sorted" / "pdfs"

    result = move_file(src, target_dir, dry_run=False, conflict_strategy="rename")

    assert result.action == "moved"
    assert result.dest == target_dir / "a.pdf"
    assert not src.exists()
    assert (target_dir / "a.pdf").exists()


def test_conflict_uses_incrementing_suffix(tmp_path: Path) -> None:
    target = touch_file(tmp_path / "target" / "foo.pdf")
    touch_file(tmp_path / "target" / "foo (1).pdf")

    resolved = resolve_conflict(target, "rename")

    assert resolved == tmp_path / "target" / "foo (2).pdf"


def test_conflict_without_extension(tmp_path: Path) -> None:
    target = touch_file(tmp_path / "target" / "foo")

    resolved = resolve_conflict(target, "rename")

    assert resolved == tmp_path / "target" / "foo (1)"


def test_dry_run_does_not_move_or_create_target_dir(tmp_path: Path) -> None:
    src = touch_file(tmp_path / "Downloads" / "a.pdf")
    target_dir = tmp_path / "Downloads" / "_sorted" / "pdfs"

    result = move_file(src, target_dir, dry_run=True, conflict_strategy="rename")

    assert result.action == "dry_run"
    assert src.exists()
    assert not target_dir.exists()


def test_skip_strategy_skips_existing_target(tmp_path: Path) -> None:
    src = touch_file(tmp_path / "Downloads" / "foo.pdf")
    target_dir = tmp_path / "Downloads" / "_sorted" / "pdfs"
    touch_file(target_dir / "foo.pdf")

    result = move_file(src, target_dir, dry_run=False, conflict_strategy="skip")

    assert result.action == "skipped"
    assert result.reason == "target_exists"
    assert src.exists()
