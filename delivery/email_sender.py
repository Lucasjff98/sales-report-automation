"""
Delivery module: send the generated Excel report by email over SMTP.

Designed against Outlook / Office 365 SMTP (smtp.office365.com, port 587,
STARTTLS) but works with any standard SMTP server, since the host/port
come from the config file rather than being hardcoded.

NOTE ON OFFICE 365: if your account has Multi-Factor Authentication
enabled (common on organizational accounts), a regular password will
NOT work here. You'll need to generate an "app password" in your
Microsoft account security settings and use that as sender_password.
"""

from __future__ import annotations

import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

DEFAULT_SUBJECT = "Sales Report"
DEFAULT_BODY = "Hi,\n\nPlease find the attached sales report.\n\nBest regards."


def send_report_email(
    config: dict[str, Any],
    attachment_path: str | Path,
    subject: str = DEFAULT_SUBJECT,
    body: str = DEFAULT_BODY,
) -> None:
    """
    Send an email with the report file attached, using SMTP.

    Parameters
    ----------
    config : dict[str, Any]
        Configuration as returned by delivery.config.load_email_config
        (must contain smtp_host, smtp_port, sender_email,
        sender_password, recipients, and optionally use_tls).
    attachment_path : str | Path
        Path to the report file to attach (e.g. the .xlsx produced by
        report.excel_report.generate_report).
    subject : str, optional
        Email subject line.
    body : str, optional
        Plain-text email body.

    Raises
    ------
    FileNotFoundError
        If attachment_path does not exist.
    smtplib.SMTPException
        If the SMTP server rejects authentication or the message send
        (propagated as-is so calling code can decide how to handle it,
        e.g. retry or alert).
    """
    attachment_path = Path(attachment_path)
    if not attachment_path.exists():
        raise FileNotFoundError(f"Attachment file not found: {attachment_path}")

    message = _build_message(config, attachment_path, subject, body)

    with smtplib.SMTP(config["smtp_host"], config["smtp_port"]) as server:
        if config.get("use_tls", True):
            server.starttls()
        server.login(config["sender_email"], config["sender_password"])
        server.sendmail(
            from_addr=config["sender_email"],
            to_addrs=config["recipients"],
            msg=message.as_string(),
        )


def _build_message(
    config: dict[str, Any],
    attachment_path: Path,
    subject: str,
    body: str,
) -> MIMEMultipart:
    message = MIMEMultipart()
    message["From"] = config["sender_email"]
    message["To"] = ", ".join(config["recipients"])
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    file_bytes = attachment_path.read_bytes()
    attachment = MIMEApplication(file_bytes, Name=attachment_path.name)
    attachment["Content-Disposition"] = f'attachment; filename="{attachment_path.name}"'
    message.attach(attachment)

    return message