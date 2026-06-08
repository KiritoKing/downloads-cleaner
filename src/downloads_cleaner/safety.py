from __future__ import annotations

import fnmatch
from pathlib import Path

from downloads_cleaner.classifier import get_extension
from downloads_cleaner.types import AppConfig, SkipReason


def should_skip_file(path: Path, config: AppConfig, now: float) -> SkipReason | None:
    try:
        if config.safety.skip_directories and path.is_dir():
            return SkipReason("directory", "directories are skipped")
        if not path.is_file():
            return SkipReason("not_regular_file", "not a regular file")
        if config.safety.skip_hidden_files and is_hidden_file(path):
            return SkipReason("hidden_file", "hidden files are skipped")
        if is_inside_managed_dir(path, config):
            return SkipReason("managed_dir", "managed directory contents are skipped")
        if is_incomplete_download(path, config):
            return SkipReason("incomplete_download", "incomplete download file")
        if is_recently_modified(path, config.safety.min_age_seconds, now):
            return SkipReason("recently_modified", "file modified too recently")
        max_bytes = config.safety.max_file_size_mb * 1024 * 1024
        if max_bytes and path.stat().st_size > max_bytes:
            return SkipReason("file_too_large", "file exceeds max_file_size_mb")
    except OSError as exc:
        return SkipReason("stat_failed", str(exc))
    return None


def is_hidden_file(path: Path) -> bool:
    return path.name.startswith(".")


def is_incomplete_download(path: Path, config: AppConfig) -> bool:
    extension = get_extension(path, config.behavior.case_insensitive_extension)
    if extension in config.incomplete_downloads.extensions:
        return True
    return any(
        fnmatch.fnmatchcase(path.name, pattern)
        for pattern in config.incomplete_downloads.filename_patterns
    )


def is_recently_modified(path: Path, min_age_seconds: int, now: float) -> bool:
    return now - path.stat().st_mtime < min_age_seconds


def is_inside_managed_dir(path: Path, config: AppConfig) -> bool:
    candidate = path.resolve(strict=False)
    managed_dirs = (
        config.paths.sorted_base.resolve(strict=False),
        config.paths.review.resolve(strict=False),
        config.paths.trash_candidate.resolve(strict=False),
    )
    return any(_is_relative_to(candidate, managed_dir) for managed_dir in managed_dirs)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
