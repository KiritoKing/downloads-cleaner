from __future__ import annotations

from pathlib import Path

from downloads_cleaner.cleanup import collect_cleanup_candidates, run_cleanup
from downloads_cleaner.types import AppConfig

from tests.conftest import touch_file


def test_old_installers_move_to_trash_candidate(app_config: AppConfig) -> None:
    source = touch_file(app_config.paths.sorted_base / "installers" / "old.dmg", age_days=15)

    summary = run_cleanup(app_config, dry_run=False, now=source.stat().st_mtime + 15 * 86400 + 1)

    assert summary.moved == 1
    assert not source.exists()
    assert (app_config.paths.trash_candidate / "old.dmg").exists()


def test_newer_files_are_not_cleanup_candidates(app_config: AppConfig) -> None:
    source = touch_file(app_config.paths.sorted_base / "installers" / "new.dmg", age_days=1)

    candidates = collect_cleanup_candidates(app_config.paths.sorted_base / "installers", 14, source.stat().st_mtime + 86400)

    assert candidates == []


def test_cleanup_ignores_directories(app_config: AppConfig) -> None:
    directory = app_config.paths.sorted_base / "installers" / "folder"
    directory.mkdir(parents=True)

    candidates = collect_cleanup_candidates(app_config.paths.sorted_base / "installers", 0, directory.stat().st_mtime + 1)

    assert candidates == []


def test_trash_candidate_conflicts_are_renamed(app_config: AppConfig) -> None:
    source = touch_file(app_config.paths.sorted_base / "installers" / "old.dmg", age_days=15)
    touch_file(app_config.paths.trash_candidate / "old.dmg")

    summary = run_cleanup(app_config, dry_run=False, now=source.stat().st_mtime + 15 * 86400 + 1)

    assert summary.moved == 1
    assert (app_config.paths.trash_candidate / "old (1).dmg").exists()


def test_cleanup_dry_run_does_not_move(app_config: AppConfig) -> None:
    source = touch_file(app_config.paths.sorted_base / "installers" / "old.dmg", age_days=15)

    summary = run_cleanup(app_config, dry_run=True, now=source.stat().st_mtime + 15 * 86400 + 1)

    assert summary.moved == 1
    assert source.exists()
    assert not app_config.paths.trash_candidate.exists()
