from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from downloads_cleaner.types import (
    AppConfig,
    BehaviorConfig,
    CleanupConfig,
    IncompleteDownloadsConfig,
    PathsConfig,
    RuleConfig,
    SafetyConfig,
)


@pytest.fixture
def app_config(tmp_path: Path) -> AppConfig:
    return make_config(tmp_path)


def make_config(tmp_path: Path, *, min_age_seconds: int = 0) -> AppConfig:
    downloads = tmp_path / "Downloads"
    sorted_base = downloads / "_sorted"
    review = downloads / "_inbox_review"
    trash_candidate = downloads / "_trash_candidate"
    downloads.mkdir()
    return AppConfig(
        paths=PathsConfig(
            downloads=downloads,
            sorted_base=sorted_base,
            review=review,
            trash_candidate=trash_candidate,
            log_file=tmp_path / "downloads-cleaner.log",
        ),
        safety=SafetyConfig(
            min_age_seconds=min_age_seconds,
            dry_run=False,
            direct_delete=False,
            skip_hidden_files=True,
            skip_directories=True,
            max_file_size_mb=10,
        ),
        behavior=BehaviorConfig(
            scan_recursive=False,
            case_insensitive_extension=True,
            create_target_dirs=True,
            conflict_strategy="rename",
            fallback_target="review",
        ),
        incomplete_downloads=IncompleteDownloadsConfig(
            extensions=["crdownload", "download", "part", "tmp"],
            filename_patterns=[
                "*.download",
                "*.crdownload",
                "*.part",
                "*.tmp",
                ".com.google.Chrome.*",
            ],
        ),
        rules=[
            RuleConfig(
                name="screenshots",
                target="images/screenshots",
                extensions=["png", "jpg", "jpeg"],
                filename_patterns=["Screenshot*", "截屏*"],
            ),
            RuleConfig(name="images", target="images", extensions=["jpg", "jpeg", "png"]),
            RuleConfig(name="pdfs", target="pdfs", extensions=["pdf"]),
            RuleConfig(name="archives", target="archives", extensions=["zip"]),
            RuleConfig(name="installers", target="installers", extensions=["dmg"]),
        ],
        cleanup=[
            CleanupConfig(
                name="old_installers",
                source="installers",
                older_than_days=14,
                target="trash_candidate",
            ),
            CleanupConfig(
                name="old_review",
                source="review",
                older_than_days=30,
                target="trash_candidate",
            ),
        ],
    )


def touch_file(path: Path, *, age_days: int = 0, content: bytes = b"x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    if age_days:
        timestamp = time.time() - age_days * 86400
        os.utime(path, (timestamp, timestamp))
    return path
