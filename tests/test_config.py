from __future__ import annotations

from pathlib import Path

import pytest

from downloads_cleaner.config import ConfigError, parse_config


def base_raw_config(downloads: Path) -> dict[str, object]:
    return {
        "paths": {
            "downloads": str(downloads),
            "sorted_base": str(downloads / "_sorted"),
            "review": str(downloads / "_inbox_review"),
            "trash_candidate": str(downloads / "_trash_candidate"),
            "log_file": str(downloads.parent / "log.txt"),
        },
        "safety": {
            "min_age_seconds": 0,
            "dry_run": False,
            "direct_delete": False,
            "skip_hidden_files": True,
            "skip_directories": True,
            "max_file_size_mb": 10,
        },
        "behavior": {
            "scan_recursive": False,
            "case_insensitive_extension": True,
            "create_target_dirs": True,
            "conflict_strategy": "rename",
            "fallback_target": "review",
        },
        "incomplete_downloads": {
            "extensions": ["tmp"],
            "filename_patterns": ["*.tmp"],
        },
        "rules": [
            {
                "name": "pdfs",
                "target": "pdfs",
                "extensions": ["PDF"],
            }
        ],
        "cleanup": [
            {
                "name": "old_pdfs",
                "source": "pdfs",
                "older_than_days": 30,
                "target": "trash_candidate",
            }
        ],
    }


def test_parse_config_normalizes_extensions(tmp_path: Path) -> None:
    downloads = tmp_path / "Downloads"
    downloads.mkdir()

    config = parse_config(base_raw_config(downloads))

    assert config.rules[0].extensions == ["pdf"]


def test_direct_delete_is_rejected(tmp_path: Path) -> None:
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    raw = base_raw_config(downloads)
    safety = raw["safety"]
    assert isinstance(safety, dict)
    safety["direct_delete"] = True

    with pytest.raises(ConfigError, match="direct_delete"):
        parse_config(raw)


def test_absolute_rule_target_is_rejected(tmp_path: Path) -> None:
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    raw = base_raw_config(downloads)
    rules = raw["rules"]
    assert isinstance(rules, list)
    first_rule = rules[0]
    assert isinstance(first_rule, dict)
    first_rule["target"] = "/tmp/pdfs"

    with pytest.raises(ConfigError, match="absolute"):
        parse_config(raw)


def test_cleanup_trash_candidate_source_is_rejected(tmp_path: Path) -> None:
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    raw = base_raw_config(downloads)
    cleanup = raw["cleanup"]
    assert isinstance(cleanup, list)
    first_cleanup = cleanup[0]
    assert isinstance(first_cleanup, dict)
    first_cleanup["source"] = "trash_candidate"

    with pytest.raises(ConfigError, match="trash_candidate"):
        parse_config(raw)
