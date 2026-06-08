from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


ConflictStrategy = Literal["rename", "skip"]
MoveAction = Literal["moved", "dry_run", "skipped", "failed"]


@dataclass(frozen=True)
class PathsConfig:
    downloads: Path
    sorted_base: Path
    review: Path
    trash_candidate: Path
    log_file: Path


@dataclass(frozen=True)
class SafetyConfig:
    min_age_seconds: int
    dry_run: bool
    direct_delete: bool
    skip_hidden_files: bool
    skip_directories: bool
    max_file_size_mb: int


@dataclass(frozen=True)
class BehaviorConfig:
    scan_recursive: bool
    case_insensitive_extension: bool
    create_target_dirs: bool
    conflict_strategy: ConflictStrategy
    fallback_target: Literal["review"]


@dataclass(frozen=True)
class IncompleteDownloadsConfig:
    extensions: list[str]
    filename_patterns: list[str]


@dataclass(frozen=True)
class RuleConfig:
    name: str
    target: str
    extensions: list[str] = field(default_factory=list)
    filename_patterns: list[str] = field(default_factory=list)
    min_size_mb: int | None = None
    max_size_mb: int | None = None


@dataclass(frozen=True)
class CleanupConfig:
    name: str
    source: str
    older_than_days: int
    target: Literal["trash_candidate"]


@dataclass(frozen=True)
class AppConfig:
    paths: PathsConfig
    safety: SafetyConfig
    behavior: BehaviorConfig
    incomplete_downloads: IncompleteDownloadsConfig
    rules: list[RuleConfig]
    cleanup: list[CleanupConfig]


@dataclass(frozen=True)
class SkipReason:
    code: str
    message: str


@dataclass(frozen=True)
class MoveResult:
    src: Path
    dest: Path | None
    action: MoveAction
    reason: str | None = None
    error: str | None = None


@dataclass
class RunSummary:
    moved: int = 0
    skipped: int = 0
    failed: int = 0
    cleanup_moved: int = 0


@dataclass
class CleanupSummary:
    moved: int = 0
    skipped: int = 0
    failed: int = 0
