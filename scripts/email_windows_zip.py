from __future__ import annotations

import argparse
import getpass
import os
import smtplib
from collections.abc import Callable
from email.message import EmailMessage
from pathlib import Path

import keyring

try:
    from scripts.package_windows_zip import package_windows_zip
except ModuleNotFoundError:
    from package_windows_zip import package_windows_zip

DEFAULT_SMTP_HOST = "smtp.mail.me.com"
DEFAULT_SMTP_PORT = 587
DEFAULT_SERVICE_NAME = "text-cleaner-email"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="email_windows_zip",
        description="Build and email the Text Cleaner Windows zip.",
    )
    parser.add_argument("--to", dest="recipient", default=os.environ.get("TO_EMAIL"))
    parser.add_argument(
        "--from",
        dest="sender",
        default=os.environ.get("SMTP_USER") or os.environ.get("TEXT_CLEANER_EMAIL_FROM"),
    )
    parser.add_argument("--smtp-host", default=os.environ.get("SMTP_HOST", DEFAULT_SMTP_HOST))
    parser.add_argument(
        "--smtp-port",
        type=int,
        default=int(os.environ.get("SMTP_PORT", DEFAULT_SMTP_PORT)),
    )
    parser.add_argument("--service-name", default=DEFAULT_SERVICE_NAME)
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Prompt for and store the app-specific password without sending email.",
    )
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="Prompt for a new app-specific password and replace the stored one.",
    )
    return parser


def build_message(sender: str, recipient: str, zip_path: Path) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = "Text Cleaner Windows Zip"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        "Attached is the Text Cleaner Windows package.\n\n"
        "Unzip it, open PowerShell in the extracted text-cleaner folder, "
        "and run .\\run.cmd.\n"
    )
    message.add_attachment(
        zip_path.read_bytes(),
        maintype="application",
        subtype="zip",
        filename=zip_path.name,
    )
    return message


def get_or_prompt_password(
    *,
    keyring_backend,
    service_name: str,
    username: str,
    prompt_password: Callable[[str], str],
    reset_password: bool,
) -> str:
    if not reset_password:
        stored = keyring_backend.get_password(service_name, username)
        if stored:
            return stored

    password = prompt_password(f"App-specific password for {username}: ")
    if not password:
        raise ValueError("app-specific password cannot be empty")
    keyring_backend.set_password(service_name, username, password)
    return password


def send_email(
    *,
    message: EmailMessage,
    host: str,
    port: int,
    username: str,
    password: str,
) -> None:
    with smtplib.SMTP(host, port) as smtp:
        smtp.starttls()
        smtp.login(username, password)
        smtp.send_message(message)


def main(
    argv: list[str] | None = None,
    *,
    prompt_password: Callable[[str], str] = getpass.getpass,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.sender:
        parser.error("sender email is required: pass --from sender@icloud.com")
    if not args.setup and not args.recipient:
        parser.error("destination email is required: pass --to destination@example.com")

    password = get_or_prompt_password(
        keyring_backend=keyring,
        service_name=args.service_name,
        username=args.sender,
        prompt_password=prompt_password,
        reset_password=args.reset_password or args.setup,
    )

    if args.setup:
        print(f"Stored app-specific password in keyring for {args.sender}.")
        return 0

    zip_path = package_windows_zip()
    message = build_message(
        sender=args.sender,
        recipient=args.recipient,
        zip_path=zip_path,
    )
    send_email(
        message=message,
        host=args.smtp_host,
        port=args.smtp_port,
        username=args.sender,
        password=password,
    )
    print(f"Sent {zip_path} to {args.recipient}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
