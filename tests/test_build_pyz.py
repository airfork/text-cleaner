import importlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

build_pyz = importlib.import_module("scripts.build_pyz")
exclude_active_virtualenv = build_pyz.exclude_active_virtualenv
resolve_runtime_python = build_pyz.resolve_runtime_python
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


def test_resolve_runtime_python_skips_candidate_when_version_probe_fails(monkeypatch):
    run_calls = []

    def fake_which(command, path=None):
        assert path == "/usr/bin"
        return f"/usr/bin/{command}"

    def fake_run(command, **kwargs):
        run_calls.append(command)
        assert kwargs["check"] is True
        assert kwargs["env"]["PATH"] == "/usr/bin"
        assert command[1] == "-c"
        assert command[2] == build_pyz.PYTHON_VERSION_PROBE
        if command[0] == "python3":
            raise subprocess.CalledProcessError(1, command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(build_pyz.shutil, "which", fake_which)
    monkeypatch.setattr(build_pyz.subprocess, "run", fake_run)

    runtime_python = resolve_runtime_python("posix", {"PATH": "/usr/bin"})

    assert runtime_python.command == ["python"]
    assert run_calls == [
        ["python3", "-c", build_pyz.PYTHON_VERSION_PROBE],
        ["python", "-c", build_pyz.PYTHON_VERSION_PROBE],
    ]


def test_resolve_runtime_python_falls_back_to_current_python_when_no_probe_succeeds(
    monkeypatch,
):
    run_calls = []

    def fake_which(command, path=None):
        assert path == "/usr/bin"
        return f"/usr/bin/{command}"

    def fake_run(command, **kwargs):
        run_calls.append(command)
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(build_pyz.shutil, "which", fake_which)
    monkeypatch.setattr(build_pyz.subprocess, "run", fake_run)
    monkeypatch.setattr(build_pyz.sys, "executable", "/current/python")

    runtime_python = resolve_runtime_python("posix", {"PATH": "/usr/bin"})

    assert runtime_python.command == ["/current/python"]
    assert run_calls == [
        ["python3", "-c", build_pyz.PYTHON_VERSION_PROBE],
        ["python", "-c", build_pyz.PYTHON_VERSION_PROBE],
    ]


def test_windows_launcher_probes_runtimes_before_running_app():
    run_cmd = (ROOT / "packaging" / "run.cmd").read_text()
    lines = [line.strip().lower() for line in run_cmd.splitlines()]
    py_probe_index = next(i for i, line in enumerate(lines) if line.startswith("py -3 -c "))
    py_run_index = next(
        i for i, line in enumerate(lines) if line.startswith("py -3 ") and ".pyz" in line
    )
    python_probe_index = next(i for i, line in enumerate(lines) if line.startswith("python -c "))
    python_run_index = next(
        i for i, line in enumerate(lines) if line.startswith("python ") and ".pyz" in line
    )

    assert "%ERRORLEVEL%" not in run_cmd
    assert py_probe_index < py_run_index < python_probe_index < python_run_index
    assert ".pyz" not in lines[py_probe_index]
    assert ".pyz" not in lines[python_probe_index]
    assert "if errorlevel 1" in run_cmd.lower()
    assert lines[py_run_index + 1] == "exit /b"
    assert lines[python_run_index + 1] == "exit /b"
    assert "exit /b 0" not in lines[py_run_index + 1]
    assert "exit /b 0" not in lines[python_run_index + 1]


def test_posix_launcher_probes_python_version_before_execing_app():
    run_command = (ROOT / "packaging" / "run.command").read_text()
    lines = [line.strip() for line in run_command.splitlines()]
    python3_probe_index = next(
        i for i, line in enumerate(lines) if line.startswith('if python3 -c "import sys;')
    )
    python3_exec_index = next(i for i, line in enumerate(lines) if line.startswith("exec python3 "))
    python_probe_index = next(
        i for i, line in enumerate(lines) if line.startswith('if python -c "import sys;')
    )
    python_exec_index = next(i for i, line in enumerate(lines) if line.startswith("exec python "))

    assert "sys.version_info >= (3, 11)" in run_command
    assert python3_probe_index < python3_exec_index < python_probe_index < python_exec_index
    assert "text-cleaner.pyz" not in lines[python3_probe_index]
    assert "text-cleaner.pyz" not in lines[python_probe_index]
