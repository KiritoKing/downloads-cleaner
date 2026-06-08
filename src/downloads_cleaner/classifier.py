from __future__ import annotations

import fnmatch
from pathlib import Path

from downloads_cleaner.types import AppConfig, RuleConfig


def classify(path: Path, rules: list[RuleConfig], config: AppConfig) -> RuleConfig | None:
    for rule in rules:
        if match_rule(path, rule, config):
            return rule
    return None


def match_rule(path: Path, rule: RuleConfig, config: AppConfig) -> bool:
    extension = get_extension(path, config.behavior.case_insensitive_extension)
    if rule.extensions and extension not in rule.extensions:
        return False

    if rule.filename_patterns and not any(
        fnmatch.fnmatchcase(path.name, pattern) for pattern in rule.filename_patterns
    ):
        return False

    size_mb = path.stat().st_size / (1024 * 1024)
    if rule.min_size_mb is not None and size_mb < rule.min_size_mb:
        return False
    if rule.max_size_mb is not None and size_mb > rule.max_size_mb:
        return False

    return True


def get_extension(path: Path, case_insensitive: bool = True) -> str:
    extension = path.suffix.lstrip(".")
    if case_insensitive:
        return extension.lower()
    return extension
