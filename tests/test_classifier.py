from __future__ import annotations

from pathlib import Path

from downloads_cleaner.classifier import classify
from downloads_cleaner.types import AppConfig

from tests.conftest import touch_file


def test_pdf_matches_pdfs(app_config: AppConfig) -> None:
    path = touch_file(app_config.paths.downloads / "a.pdf")

    rule = classify(path, app_config.rules, app_config)

    assert rule is not None
    assert rule.name == "pdfs"


def test_jpg_matches_images(app_config: AppConfig) -> None:
    path = touch_file(app_config.paths.downloads / "b.jpg")

    rule = classify(path, app_config.rules, app_config)

    assert rule is not None
    assert rule.name == "images"


def test_case_insensitive_extensions(app_config: AppConfig) -> None:
    path = touch_file(app_config.paths.downloads / "report.PDF")

    rule = classify(path, app_config.rules, app_config)

    assert rule is not None
    assert rule.name == "pdfs"


def test_filename_pattern_and_rule_order_prefer_screenshots(app_config: AppConfig) -> None:
    path = touch_file(app_config.paths.downloads / "Screenshot 2026-06-08.png")

    rule = classify(path, app_config.rules, app_config)

    assert rule is not None
    assert rule.name == "screenshots"
    assert rule.target == "images/screenshots"


def test_unmatched_returns_none(app_config: AppConfig) -> None:
    path = touch_file(app_config.paths.downloads / "unknown.bin")

    rule = classify(path, app_config.rules, app_config)

    assert rule is None


def test_size_conditions_are_and_conditions(app_config: AppConfig, tmp_path: Path) -> None:
    config = app_config
    size_rule = config.rules[0].__class__(
        name="large_pdf",
        target="documents/large",
        extensions=["pdf"],
        min_size_mb=1,
    )
    path = touch_file(config.paths.downloads / "small.pdf", content=b"x")

    rule = classify(path, [size_rule], config)

    assert rule is None
