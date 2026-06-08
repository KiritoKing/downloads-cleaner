from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from downloads_cleaner.classifier import classify
from downloads_cleaner.cleanup import run_cleanup
from downloads_cleaner.config import (
    ConfigError,
    DEFAULT_CONFIG_PATH,
    get_rule_target_dir,
    load_config,
)
from downloads_cleaner.logging_utils import setup_logging
from downloads_cleaner.mover import move_file
from downloads_cleaner.safety import should_skip_file
from downloads_cleaner.types import AppConfig, RunSummary


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            return run_command(args)
        if args.command == "validate-config":
            return validate_config_command(args)
        if args.command == "print-plan":
            return print_plan_command(args)
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="downloads-cleaner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="classify Downloads files and run cleanup")
    _add_common_options(run_parser)
    run_parser.add_argument("--no-cleanup", action="store_true", help="skip cleanup phase")
    run_parser.add_argument(
        "--only-cleanup",
        action="store_true",
        help="skip root classification and only run cleanup",
    )

    validate_parser = subparsers.add_parser("validate-config", help="validate rules TOML")
    validate_parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)

    plan_parser = subparsers.add_parser("print-plan", help="print files and destinations")
    _add_common_options(plan_parser)

    return parser


def run_command(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    dry_run = config.safety.dry_run or args.dry_run
    logger = setup_logging(config.paths.log_file, args.verbose)
    logger.info('run_start dry_run=%s config="%s"', dry_run, args.config)

    summary = RunSummary()
    now = time.time()

    if args.only_cleanup and args.no_cleanup:
        print("--only-cleanup and --no-cleanup cannot be used together", file=sys.stderr)
        return 2

    if not args.only_cleanup:
        _ensure_management_dirs(config, dry_run=dry_run)
        _run_classification(config, dry_run=dry_run, now=now, logger=logger, summary=summary)

    if not args.no_cleanup:
        cleanup_summary = run_cleanup(config, dry_run=dry_run, now=now, logger=logger)
        summary.cleanup_moved = cleanup_summary.moved
        summary.skipped += cleanup_summary.skipped
        summary.failed += cleanup_summary.failed

    logger.info(
        "run_end moved=%s skipped=%s errors=%s cleanup_moved=%s",
        summary.moved,
        summary.skipped,
        summary.failed,
        summary.cleanup_moved,
    )
    return 1 if summary.failed else 0


def validate_config_command(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    print(f"config ok: {args.config}")
    print(f"downloads: {config.paths.downloads}")
    return 0


def print_plan_command(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    dry_run = True
    logger = setup_logging(config.paths.log_file, args.verbose)
    now = time.time()
    summary = RunSummary()
    _run_classification(
        config,
        dry_run=dry_run,
        now=now,
        logger=logger,
        summary=summary,
        print_actions=True,
    )
    return 1 if summary.failed else 0


def collect_candidate_files(config: AppConfig) -> list[Path]:
    if config.behavior.scan_recursive:
        return list(config.paths.downloads.rglob("*"))
    return list(config.paths.downloads.iterdir())


def _run_classification(
    config: AppConfig,
    *,
    dry_run: bool,
    now: float,
    logger: logging.Logger,
    summary: RunSummary,
    print_actions: bool = False,
) -> None:
    for file_path in collect_candidate_files(config):
        try:
            skip_reason = should_skip_file(file_path, config, now)
            if skip_reason:
                summary.skipped += 1
                logger.info(
                    'skip src="%s" reason="%s" message="%s"',
                    file_path,
                    skip_reason.code,
                    skip_reason.message,
                )
                if print_actions:
                    print(f"skip {file_path} reason={skip_reason.code}")
                continue

            rule = classify(file_path, config.rules, config)
            target_dir = get_rule_target_dir(config, rule) if rule else config.paths.review
            result = move_file(
                file_path,
                target_dir,
                dry_run=dry_run,
                conflict_strategy=config.behavior.conflict_strategy,
            )

            if result.action == "moved":
                summary.moved += 1
                logger.info(
                    'move src="%s" dest="%s" rule="%s"',
                    result.src,
                    result.dest,
                    rule.name if rule else "fallback_review",
                )
            elif result.action == "dry_run":
                summary.moved += 1
                logger.info(
                    '[DRY-RUN] move src="%s" dest="%s" rule="%s"',
                    result.src,
                    result.dest,
                    rule.name if rule else "fallback_review",
                )
                if print_actions:
                    print(f"[DRY-RUN] {result.src} -> {result.dest}")
            elif result.action == "skipped":
                summary.skipped += 1
                logger.info(
                    'skip src="%s" reason="%s"',
                    result.src,
                    result.reason,
                )
                if print_actions:
                    print(f"skip {result.src} reason={result.reason}")
            else:
                summary.failed += 1
                logger.error('move_failed src="%s" error="%s"', result.src, result.error)
                if print_actions:
                    print(f"failed {result.src} error={result.error}", file=sys.stderr)
        except Exception as exc:
            summary.failed += 1
            logger.error(
                'move_failed src="%s" error="%s: %s"',
                file_path,
                type(exc).__name__,
                exc,
            )


def _ensure_management_dirs(config: AppConfig, *, dry_run: bool) -> None:
    if dry_run:
        return
    config.paths.sorted_base.mkdir(parents=True, exist_ok=True)
    config.paths.review.mkdir(parents=True, exist_ok=True)
    config.paths.trash_candidate.mkdir(parents=True, exist_ok=True)


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--dry-run", action="store_true", help="print/log without moving files")
    parser.add_argument("--verbose", action="store_true", help="also write log output to stdout")


if __name__ == "__main__":
    raise SystemExit(main())
