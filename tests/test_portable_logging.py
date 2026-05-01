from pathlib import Path

from text_cleaner.logging_setup import configure_logging, write_diagnostics
from text_cleaner.portable import resolve_portable_dir


def test_resolve_portable_dir_uses_explicit_path(tmp_path):
    chosen = tmp_path / "portable"

    result = resolve_portable_dir(explicit=chosen, argv0=Path("/tmp/app/text-cleaner.pyz"))

    assert result == chosen.resolve()


def test_resolve_portable_dir_uses_archive_parent_when_no_explicit_path(tmp_path):
    archive = tmp_path / "text-cleaner.pyz"
    archive.write_text("archive bytes", encoding="utf-8")

    result = resolve_portable_dir(explicit=None, argv0=archive)

    assert result == tmp_path.resolve()


def test_configure_logging_writes_log_file(tmp_path):
    logger = configure_logging(tmp_path)

    logger.info("hello from test")

    log_file = tmp_path / "logs" / "text-cleaner.log"
    assert log_file.exists()
    assert "hello from test" in log_file.read_text(encoding="utf-8")


def test_write_diagnostics_creates_timestamped_dump(tmp_path):
    logger = configure_logging(tmp_path)
    logger.info("diagnostic source")

    dump = write_diagnostics(tmp_path)

    assert dump.parent == tmp_path / "logs"
    assert dump.name.startswith("diagnostics-")
    assert "diagnostic source" in dump.read_text(encoding="utf-8")
