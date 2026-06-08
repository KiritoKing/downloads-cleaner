from __future__ import annotations

import shutil
from pathlib import Path

from downloads_cleaner.types import ConflictStrategy, MoveResult


def move_file(
    src: Path,
    target_dir: Path,
    *,
    dry_run: bool,
    conflict_strategy: ConflictStrategy,
) -> MoveResult:
    dest = resolve_destination(src, target_dir, conflict_strategy)
    if dest is None:
        return MoveResult(src=src, dest=None, action="skipped", reason="target_exists")

    try:
        ensure_dir(target_dir, dry_run=dry_run)
        if dry_run:
            return MoveResult(src=src, dest=dest, action="dry_run")
        shutil.move(str(src), str(dest))
        return MoveResult(src=src, dest=dest, action="moved")
    except Exception as exc:
        return MoveResult(
            src=src,
            dest=dest,
            action="failed",
            error=f"{type(exc).__name__}: {exc}",
        )


def resolve_destination(
    src: Path,
    target_dir: Path,
    conflict_strategy: ConflictStrategy,
) -> Path | None:
    target_path = target_dir / src.name
    return resolve_conflict(target_path, conflict_strategy)


def resolve_conflict(target_path: Path, strategy: ConflictStrategy) -> Path | None:
    if not target_path.exists():
        return target_path
    if strategy == "skip":
        return None
    if strategy != "rename":
        raise ValueError(f"unsupported conflict strategy: {strategy}")

    stem = target_path.stem
    suffix = target_path.suffix
    parent = target_path.parent
    for index in range(1, 10000):
        candidate = parent / f"{stem} ({index}){suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"could not resolve filename conflict for {target_path}")


def ensure_dir(path: Path, dry_run: bool) -> None:
    if dry_run:
        return
    path.mkdir(parents=True, exist_ok=True)
