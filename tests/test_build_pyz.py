import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

build_pyz = importlib.import_module("scripts.build_pyz")
exclude_active_virtualenv = build_pyz.exclude_active_virtualenv
python_candidates = build_pyz.python_candidates


def test_python_candidates_prefers_windows_launcher_before_python():
    assert python_candidates("nt") == ["py -3", "python"]


def test_python_candidates_prefers_python3_on_posix():
    assert python_candidates("posix") == ["python3", "python"]


def test_exclude_active_virtualenv_removes_windows_scripts_path():
    path_value = ";".join(
        [
            r"C:\repo\.venv\Scripts",
            r"C:\Windows\System32",
            r"C:\Python311",
        ],
    )

    filtered = exclude_active_virtualenv(path_value, r"C:\repo\.venv", "nt")

    assert filtered == ";".join([r"C:\Windows\System32", r"C:\Python311"])


def test_exclude_active_virtualenv_removes_posix_bin_path():
    path_value = ":".join(
        [
            "/repo/.venv/bin",
            "/usr/local/bin",
            "/usr/bin",
        ],
    )

    filtered = exclude_active_virtualenv(path_value, "/repo/.venv", "posix")

    assert filtered == ":".join(["/usr/local/bin", "/usr/bin"])
