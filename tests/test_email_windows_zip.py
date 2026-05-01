import importlib
import smtplib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

email_windows_zip = importlib.import_module("scripts.email_windows_zip")


class FakeKeyring:
    def __init__(self, password: str | None = None) -> None:
        self.password = password
        self.set_calls: list[tuple[str, str, str]] = []

    def get_password(self, service: str, username: str) -> str | None:
        return self.password

    def set_password(self, service: str, username: str, password: str) -> None:
        self.set_calls.append((service, username, password))
        self.password = password


class FakeSMTP:
    instances: list["FakeSMTP"] = []

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.started_tls = False
        self.login_calls: list[tuple[str, str]] = []
        self.messages = []
        FakeSMTP.instances.append(self)

    def __enter__(self) -> "FakeSMTP":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def starttls(self) -> None:
        self.started_tls = True

    def login(self, username: str, password: str) -> None:
        self.login_calls.append((username, password))

    def send_message(self, message) -> None:
        self.messages.append(message)


def test_build_message_attaches_zip(tmp_path):
    zip_path = tmp_path / "text-cleaner-windows.zip"
    zip_path.write_bytes(b"zip bytes")

    message = email_windows_zip.build_message(
        sender="sender@icloud.com",
        recipient="dest@example.com",
        zip_path=zip_path,
    )

    assert message["From"] == "sender@icloud.com"
    assert message["To"] == "dest@example.com"
    assert message["Subject"] == "Text Cleaner Windows Zip"
    attachments = list(message.iter_attachments())
    assert len(attachments) == 1
    assert attachments[0].get_filename() == "text-cleaner-windows.zip"
    assert attachments[0].get_content_type() == "application/zip"
    assert attachments[0].get_payload(decode=True) == b"zip bytes"


def test_get_or_prompt_password_uses_existing_keyring_password():
    keyring = FakeKeyring(password="stored-password")

    password = email_windows_zip.get_or_prompt_password(
        keyring_backend=keyring,
        service_name="text-cleaner-email",
        username="sender@icloud.com",
        prompt_password=lambda prompt: "new-password",
        reset_password=False,
    )

    assert password == "stored-password"
    assert keyring.set_calls == []


def test_get_or_prompt_password_prompts_and_stores_when_missing():
    keyring = FakeKeyring()

    password = email_windows_zip.get_or_prompt_password(
        keyring_backend=keyring,
        service_name="text-cleaner-email",
        username="sender@icloud.com",
        prompt_password=lambda prompt: "new-password",
        reset_password=False,
    )

    assert password == "new-password"
    assert keyring.set_calls == [
        ("text-cleaner-email", "sender@icloud.com", "new-password"),
    ]


def test_get_or_prompt_password_resets_existing_password():
    keyring = FakeKeyring(password="old-password")

    password = email_windows_zip.get_or_prompt_password(
        keyring_backend=keyring,
        service_name="text-cleaner-email",
        username="sender@icloud.com",
        prompt_password=lambda prompt: "new-password",
        reset_password=True,
    )

    assert password == "new-password"
    assert keyring.set_calls == [
        ("text-cleaner-email", "sender@icloud.com", "new-password"),
    ]


def test_send_email_uses_starttls_login_and_send(monkeypatch, tmp_path):
    FakeSMTP.instances = []
    zip_path = tmp_path / "text-cleaner-windows.zip"
    zip_path.write_bytes(b"zip bytes")
    message = email_windows_zip.build_message(
        sender="sender@icloud.com",
        recipient="dest@example.com",
        zip_path=zip_path,
    )
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)

    email_windows_zip.send_email(
        message=message,
        host="smtp.mail.me.com",
        port=587,
        username="sender@icloud.com",
        password="app-password",
    )

    smtp = FakeSMTP.instances[0]
    assert smtp.host == "smtp.mail.me.com"
    assert smtp.port == 587
    assert smtp.started_tls is True
    assert smtp.login_calls == [("sender@icloud.com", "app-password")]
    assert smtp.messages == [message]


def test_main_setup_stores_password_without_building_or_sending(monkeypatch):
    keyring = FakeKeyring()
    build_calls: list[str] = []
    send_calls: list[str] = []

    monkeypatch.setattr(email_windows_zip, "keyring", keyring)
    monkeypatch.setattr(
        email_windows_zip,
        "package_windows_zip",
        lambda: build_calls.append("build"),
    )
    monkeypatch.setattr(email_windows_zip, "send_email", lambda **kwargs: send_calls.append("send"))

    exit_code = email_windows_zip.main(
        ["--setup", "--from", "sender@icloud.com"],
        prompt_password=lambda prompt: "app-password",
    )

    assert exit_code == 0
    assert keyring.set_calls == [
        ("text-cleaner-email", "sender@icloud.com", "app-password"),
    ]
    assert build_calls == []
    assert send_calls == []


def test_main_builds_zip_and_sends(monkeypatch, tmp_path):
    zip_path = tmp_path / "text-cleaner-windows.zip"
    zip_path.write_bytes(b"zip bytes")
    sent = {}
    keyring = FakeKeyring(password="stored-password")

    monkeypatch.setattr(email_windows_zip, "keyring", keyring)
    monkeypatch.setattr(email_windows_zip, "package_windows_zip", lambda: zip_path)

    def fake_send_email(**kwargs):
        sent.update(kwargs)

    monkeypatch.setattr(email_windows_zip, "send_email", fake_send_email)

    exit_code = email_windows_zip.main(
        ["--from", "sender@icloud.com", "--to", "dest@example.com"],
        prompt_password=lambda prompt: "new-password",
    )

    assert exit_code == 0
    assert sent["host"] == "smtp.mail.me.com"
    assert sent["port"] == 587
    assert sent["username"] == "sender@icloud.com"
    assert sent["password"] == "stored-password"
    assert sent["message"]["To"] == "dest@example.com"
