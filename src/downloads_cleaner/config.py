from __future__ import annotations

import os
import tomllib
from pathlib import Path, PurePosixPath
from typing import Literal, TypeAlias

from downloads_cleaner.types import (
    AppConfig,
    BehaviorConfig,
    CleanupConfig,
    ConflictStrategy,
    IncompleteDownloadsConfig,
    PathsConfig,
    RuleConfig,
    SafetyConfig,
)


DEFAULT_CONFIG_PATH = Path("~/.config/downloads-cleaner/rules.toml").expanduser()
SUPPORTED_CONFLICT_STRATEGIES = {"rename", "skip"}
RawTable: TypeAlias = dict[str, object]


class ConfigError(ValueError):
    """Raised when the rules TOML file is missing required or safe values."""


def load_config(path: Path) -> AppConfig:
    config_path = path.expanduser()
    try:
        with config_path.open("rb") as config_file:
            raw: RawTable = tomllib.load(config_file)
    except FileNotFoundError as exc:
        raise ConfigError(f"config file not found: {config_path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML: {exc}") from exc

    return parse_config(raw)


def parse_config(raw: RawTable) -> AppConfig:
    paths_raw = _require_mapping(raw, "paths")
    safety_raw = _require_mapping(raw, "safety")
    behavior_raw = _require_mapping(raw, "behavior")
    incomplete_raw = _require_mapping(raw, "incomplete_downloads")
    rules_raw = _require_list(raw, "rules")
    cleanup_raw = _require_list(raw, "cleanup")

    paths = PathsConfig(
        downloads=expand_path(_require_str(paths_raw, "downloads")),
        sorted_base=expand_path(_require_str(paths_raw, "sorted_base")),
        review=expand_path(_require_str(paths_raw, "review")),
        trash_candidate=expand_path(_require_str(paths_raw, "trash_candidate")),
        log_file=expand_path(_require_str(paths_raw, "log_file")),
    )
    safety = SafetyConfig(
        min_age_seconds=_require_int(safety_raw, "min_age_seconds"),
        dry_run=_require_bool(safety_raw, "dry_run"),
        direct_delete=_require_bool(safety_raw, "direct_delete"),
        skip_hidden_files=_require_bool(safety_raw, "skip_hidden_files"),
        skip_directories=_require_bool(safety_raw, "skip_directories"),
        max_file_size_mb=_require_int(safety_raw, "max_file_size_mb"),
    )
    behavior = BehaviorConfig(
        scan_recursive=_require_bool(behavior_raw, "scan_recursive"),
        case_insensitive_extension=_require_bool(behavior_raw, "case_insensitive_extension"),
        create_target_dirs=_require_bool(behavior_raw, "create_target_dirs"),
        conflict_strategy=_parse_conflict_strategy(_require_str(behavior_raw, "conflict_strategy")),
        fallback_target=_parse_fallback_target(_require_str(behavior_raw, "fallback_target")),
    )
    incomplete_downloads = IncompleteDownloadsConfig(
        extensions=normalize_extensions(_require_str_list(incomplete_raw, "extensions")),
        filename_patterns=_require_str_list(incomplete_raw, "filename_patterns"),
    )
    rules = [_parse_rule(index, item) for index, item in enumerate(rules_raw)]
    cleanup = [_parse_cleanup(index, item) for index, item in enumerate(cleanup_raw)]

    config = AppConfig(
        paths=paths,
        safety=safety,
        behavior=behavior,
        incomplete_downloads=incomplete_downloads,
        rules=rules,
        cleanup=cleanup,
    )
    validate_config(config)
    return config


def expand_path(value: str) -> Path:
    expanded = os.path.expandvars(os.path.expanduser(value))
    path = Path(expanded)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve(strict=False)


def normalize_extensions(exts: list[str]) -> list[str]:
    normalized: list[str] = []
    for ext in exts:
        clean = ext.strip().lstrip(".").lower()
        if clean:
            normalized.append(clean)
    return normalized


def validate_config(config: AppConfig) -> None:
    if not config.paths.downloads.exists():
        raise ConfigError(f"paths.downloads must exist: {config.paths.downloads}")
    if not config.paths.downloads.is_dir():
        raise ConfigError(f"paths.downloads must be a directory: {config.paths.downloads}")
    if config.safety.min_age_seconds < 0:
        raise ConfigError("safety.min_age_seconds must be >= 0")
    if config.safety.max_file_size_mb < 0:
        raise ConfigError("safety.max_file_size_mb must be >= 0")
    if config.safety.direct_delete:
        raise ConfigError("safety.direct_delete=true is not supported")
    if config.behavior.scan_recursive:
        raise ConfigError("behavior.scan_recursive=true is not supported in the MVP")

    managed_dirs = {
        config.paths.sorted_base.resolve(strict=False),
        config.paths.review.resolve(strict=False),
        config.paths.trash_candidate.resolve(strict=False),
    }
    if config.paths.downloads.resolve(strict=False) in managed_dirs:
        raise ConfigError("managed directories must not equal paths.downloads")

    names_seen: set[str] = set()
    targets_seen: set[str] = set()
    for rule in config.rules:
        if rule.name in names_seen:
            raise ConfigError(f"duplicate rule name: {rule.name}")
        names_seen.add(rule.name)
        _validate_safe_relative_target(rule.target, f"rules.{rule.name}.target")
        targets_seen.add(rule.target)
        if rule.min_size_mb is not None and rule.min_size_mb < 0:
            raise ConfigError(f"rules.{rule.name}.min_size_mb must be >= 0")
        if rule.max_size_mb is not None and rule.max_size_mb < 0:
            raise ConfigError(f"rules.{rule.name}.max_size_mb must be >= 0")
        if (
            rule.min_size_mb is not None
            and rule.max_size_mb is not None
            and rule.min_size_mb > rule.max_size_mb
        ):
            raise ConfigError(f"rules.{rule.name} min_size_mb must be <= max_size_mb")

    cleanup_sources = targets_seen | {"review"}
    for cleanup in config.cleanup:
        if cleanup.older_than_days < 0:
            raise ConfigError(f"cleanup.{cleanup.name}.older_than_days must be >= 0")
        if cleanup.target != "trash_candidate":
            raise ConfigError(f"cleanup.{cleanup.name}.target must be trash_candidate")
        if cleanup.source == "trash_candidate":
            raise ConfigError(f"cleanup.{cleanup.name}.source must not be trash_candidate")
        if cleanup.source not in cleanup_sources:
            raise ConfigError(
                f"cleanup.{cleanup.name}.source must reference a rule target or review"
            )
        if cleanup.source != "review":
            _validate_safe_relative_target(cleanup.source, f"cleanup.{cleanup.name}.source")


def get_cleanup_source_dir(config: AppConfig, source: str) -> Path:
    if source == "review":
        return config.paths.review
    return config.paths.sorted_base / source


def get_rule_target_dir(config: AppConfig, rule: RuleConfig) -> Path:
    return config.paths.sorted_base / rule.target


def _parse_rule(index: int, item: object) -> RuleConfig:
    if not isinstance(item, dict):
        raise ConfigError(f"rules[{index}] must be a table")
    return RuleConfig(
        name=_require_str(item, "name"),
        target=_require_str(item, "target"),
        extensions=normalize_extensions(_optional_str_list(item, "extensions")),
        filename_patterns=_optional_str_list(item, "filename_patterns"),
        min_size_mb=_optional_int(item, "min_size_mb"),
        max_size_mb=_optional_int(item, "max_size_mb"),
    )


def _parse_cleanup(index: int, item: object) -> CleanupConfig:
    if not isinstance(item, dict):
        raise ConfigError(f"cleanup[{index}] must be a table")
    target = _require_str(item, "target")
    if target != "trash_candidate":
        raise ConfigError(f"cleanup[{index}].target must be trash_candidate")
    return CleanupConfig(
        name=_require_str(item, "name"),
        source=_require_str(item, "source"),
        older_than_days=_require_int(item, "older_than_days"),
        target="trash_candidate",
    )


def _parse_conflict_strategy(value: str) -> ConflictStrategy:
    if value not in SUPPORTED_CONFLICT_STRATEGIES:
        raise ConfigError("behavior.conflict_strategy must be rename or skip")
    if value == "rename":
        return "rename"
    return "skip"


def _parse_fallback_target(value: str) -> Literal["review"]:
    if value != "review":
        raise ConfigError("behavior.fallback_target must be review")
    return value


def _validate_safe_relative_target(value: str, label: str) -> None:
    path = PurePosixPath(value)
    if path.is_absolute():
        raise ConfigError(f"{label} must not be absolute")
    if ".." in path.parts:
        raise ConfigError(f"{label} must not contain '..'")
    if value.strip() == "":
        raise ConfigError(f"{label} must not be empty")


def _require_mapping(raw: RawTable, key: str) -> RawTable:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise ConfigError(f"{key} must be a table")
    return {str(item_key): item_value for item_key, item_value in value.items()}


def _require_list(raw: RawTable, key: str) -> list[object]:
    value = raw.get(key)
    if not isinstance(value, list):
        raise ConfigError(f"{key} must be a list")
    return value


def _require_str(raw: RawTable, key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or value == "":
        raise ConfigError(f"{key} must be a non-empty string")
    return value


def _require_int(raw: RawTable, key: str) -> int:
    value = raw.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"{key} must be an integer")
    return value


def _optional_int(raw: RawTable, key: str) -> int | None:
    value = raw.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"{key} must be an integer")
    return value


def _require_bool(raw: RawTable, key: str) -> bool:
    value = raw.get(key)
    if not isinstance(value, bool):
        raise ConfigError(f"{key} must be a boolean")
    return value


def _require_str_list(raw: RawTable, key: str) -> list[str]:
    value = raw.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError(f"{key} must be a list of strings")
    return list(value)


def _optional_str_list(raw: RawTable, key: str) -> list[str]:
    value = raw.get(key)
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError(f"{key} must be a list of strings")
    return list(value)
