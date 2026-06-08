from __future__ import annotations

from pathlib import Path

from downloads_cleaner.main import main

from tests.conftest import touch_file


def write_cli_config(tmp_path: Path) -> Path:
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    config_path = tmp_path / "rules.toml"
    config_path.write_text(
        f"""
[paths]
downloads = "{downloads}"
sorted_base = "{downloads / "_sorted"}"
review = "{downloads / "_inbox_review"}"
trash_candidate = "{downloads / "_trash_candidate"}"
log_file = "{tmp_path / "downloads-cleaner.log"}"

[safety]
min_age_seconds = 0
dry_run = false
direct_delete = false
skip_hidden_files = true
skip_directories = true
max_file_size_mb = 1024

[behavior]
scan_recursive = false
case_insensitive_extension = true
create_target_dirs = true
conflict_strategy = "rename"
fallback_target = "review"

[incomplete_downloads]
extensions = ["crdownload", "download", "part", "tmp"]
filename_patterns = ["*.tmp"]

[[rules]]
name = "pdfs"
target = "pdfs"
extensions = ["pdf"]

[[cleanup]]
name = "old_pdfs"
source = "pdfs"
older_than_days = 30
target = "trash_candidate"
""".strip(),
        encoding="utf-8",
    )
    return config_path


def test_run_dry_run_does_not_move_real_files(tmp_path: Path) -> None:
    config_path = write_cli_config(tmp_path)
    downloads = tmp_path / "Downloads"
    source = touch_file(downloads / "a.pdf")

    code = main(["run", "--config", str(config_path), "--dry-run"])

    assert code == 0
    assert source.exists()
    assert not (downloads / "_sorted").exists()


def test_run_moves_file_and_fallback(tmp_path: Path) -> None:
    config_path = write_cli_config(tmp_path)
    downloads = tmp_path / "Downloads"
    touch_file(downloads / "a.pdf")
    touch_file(downloads / "unknown.bin")

    code = main(["run", "--config", str(config_path), "--no-cleanup"])

    assert code == 0
    assert (downloads / "_sorted" / "pdfs" / "a.pdf").exists()
    assert (downloads / "_inbox_review" / "unknown.bin").exists()
