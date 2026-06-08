from __future__ import annotations

import time
from pathlib import Path

from downloads_cleaner.safety import should_skip_file
from downloads_cleaner.types import AppConfig

from tests.conftest import make_config, touch_file


def assert_skip_code(path: Path, config: AppConfig, code: str) -> None:
    reason = should_skip_file(path, config, time.time())

    assert reason is not None
    assert reason.code == code


def test_incomplete_download_extensions_are_skipped(app_config: AppConfig) -> None:
    for filename in ["a.crdownload", "b.download", "c.part", "d.tmp"]:
        assert_skip_code(touch_file(app_config.paths.downloads / filename), app_config, "incomplete_download")


def test_recently_modified_file_is_skipped(tmp_path: Path) -> None:
    config = make_config(tmp_path, min_age_seconds=120)
    path = touch_file(config.paths.downloads / "fresh.pdf")

    assert_skip_code(path, config, "recently_modified")


def test_hidden_file_is_skipped(app_config: AppConfig) -> None:
    path = touch_file(app_config.paths.downloads / ".DS_Store")

    assert_skip_code(path, app_config, "hidden_file")


def test_directory_is_skipped(app_config: AppConfig) -> None:
    path = app_config.paths.downloads / "folder"
    path.mkdir()

    assert_skip_code(path, app_config, "directory")


def test_regular_stable_file_is_not_skipped(app_config: AppConfig) -> None:
    path = touch_file(app_config.paths.downloads / "stable.pdf")

    reason = should_skip_file(path, app_config, time.time())

    assert reason is None


def test_sorted_internal_file_is_skipped(app_config: AppConfig) -> None:
    path = touch_file(app_config.paths.sorted_base / "pdfs" / "a.pdf")

    assert_skip_code(path, app_config, "managed_dir")


def test_oversized_file_is_skipped(app_config: AppConfig) -> None:
    content = b"x" * (11 * 1024 * 1024)
    path = touch_file(app_config.paths.downloads / "large.mov", content=content)

    assert_skip_code(path, app_config, "file_too_large")
