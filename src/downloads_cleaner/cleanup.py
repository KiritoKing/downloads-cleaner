from __future__ import annotations

import logging
from pathlib import Path

from downloads_cleaner.config import get_cleanup_source_dir
from downloads_cleaner.mover import move_file
from downloads_cleaner.types import AppConfig, CleanupSummary


def run_cleanup(
    config: AppConfig,
    *,
    dry_run: bool,
    now: float,
    logger: logging.Logger | None = None,
) -> CleanupSummary:
    summary = CleanupSummary()
    log = logger or logging.getLogger("downloads_cleaner")

    for cleanup_rule in config.cleanup:
        source_dir = get_cleanup_source_dir(config, cleanup_rule.source)
        for candidate in collect_cleanup_candidates(source_dir, cleanup_rule.older_than_days, now):
            result = move_file(
                candidate,
                config.paths.trash_candidate,
                dry_run=dry_run,
                conflict_strategy=config.behavior.conflict_strategy,
            )
            if result.action == "moved":
                summary.moved += 1
                log.info(
                    'cleanup_move src="%s" dest="%s" cleanup_rule="%s"',
                    result.src,
                    result.dest,
                    cleanup_rule.name,
                )
            elif result.action == "dry_run":
                summary.moved += 1
                log.info(
                    '[DRY-RUN] cleanup_move src="%s" dest="%s" cleanup_rule="%s"',
                    result.src,
                    result.dest,
                    cleanup_rule.name,
                )
            elif result.action == "skipped":
                summary.skipped += 1
                log.info(
                    'cleanup_skip src="%s" reason="%s" cleanup_rule="%s"',
                    result.src,
                    result.reason,
                    cleanup_rule.name,
                )
            else:
                summary.failed += 1
                log.error(
                    'cleanup_failed src="%s" error="%s" cleanup_rule="%s"',
                    result.src,
                    result.error,
                    cleanup_rule.name,
                )
    return summary


def collect_cleanup_candidates(
    source_dir: Path,
    older_than_days: int,
    now: float,
) -> list[Path]:
    if not source_dir.exists() or not source_dir.is_dir():
        return []

    min_age = older_than_days * 86400
    candidates: list[Path] = []
    for path in source_dir.iterdir():
        try:
            if not path.is_file():
                continue
            if now - path.stat().st_mtime > min_age:
                candidates.append(path)
        except OSError:
            continue
    return candidates
