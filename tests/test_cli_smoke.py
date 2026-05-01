from text_cleaner.cli import main


def test_version_command_prints_version(capsys):
    exit_code = main(["--version"])

    assert exit_code == 0
    assert "text-cleaner 0.1.0" in capsys.readouterr().out
