"""
Unit tests for delivery.email_sender.send_report_email.

The SMTP server is mocked throughout: these tests never open a real
network connection or require real credentials.

Run with:
    pytest tests/test_email_sender.py -v
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from delivery.email_sender import send_report_email


@pytest.fixture
def config() -> dict:
    return {
        "smtp_host": "smtp.office365.com",
        "smtp_port": 587,
        "sender_email": "reports@example.com",
        "sender_password": "app-password-123",
        "recipients": ["boss@example.com"],
        "use_tls": True,
    }


@pytest.fixture
def attachment(tmp_path: Path) -> Path:
    file_path = tmp_path / "report.xlsx"
    file_path.write_bytes(b"fake excel content")
    return file_path


def test_raises_file_not_found_when_attachment_missing(config, tmp_path: Path):
    missing_attachment = tmp_path / "does_not_exist.xlsx"

    with pytest.raises(FileNotFoundError):
        send_report_email(config, missing_attachment)


@patch("delivery.email_sender.smtplib.SMTP")
def test_connects_to_configured_host_and_port(mock_smtp_class, config, attachment):
    mock_server = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_server

    send_report_email(config, attachment)

    mock_smtp_class.assert_called_once_with("smtp.office365.com", 587)


@patch("delivery.email_sender.smtplib.SMTP")
def test_calls_starttls_when_use_tls_is_true(mock_smtp_class, config, attachment):
    mock_server = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_server

    send_report_email(config, attachment)

    mock_server.starttls.assert_called_once()


@patch("delivery.email_sender.smtplib.SMTP")
def test_skips_starttls_when_use_tls_is_false(mock_smtp_class, config, attachment):
    config["use_tls"] = False
    mock_server = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_server

    send_report_email(config, attachment)

    mock_server.starttls.assert_not_called()


@patch("delivery.email_sender.smtplib.SMTP")
def test_logs_in_with_configured_credentials(mock_smtp_class, config, attachment):
    mock_server = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_server

    send_report_email(config, attachment)

    mock_server.login.assert_called_once_with(
        "reports@example.com", "app-password-123"
    )


@patch("delivery.email_sender.smtplib.SMTP")
def test_sends_to_all_configured_recipients(mock_smtp_class, config, attachment):
    config["recipients"] = ["boss@example.com", "finance@example.com"]
    mock_server = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_server

    send_report_email(config, attachment)

    _, kwargs = mock_server.sendmail.call_args
    assert kwargs["to_addrs"] == ["boss@example.com", "finance@example.com"]
    assert kwargs["from_addr"] == "reports@example.com"


@patch("delivery.email_sender.smtplib.SMTP")
def test_message_contains_subject_and_attachment_name(
    mock_smtp_class, config, attachment
):
    mock_server = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_server

    send_report_email(config, attachment, subject="Q1 Sales Report")

    _, kwargs = mock_server.sendmail.call_args
    sent_message = kwargs["msg"]
    assert "Q1 Sales Report" in sent_message
    assert attachment.name in sent_message


@patch("delivery.email_sender.smtplib.SMTP")
def test_uses_default_subject_when_not_provided(mock_smtp_class, config, attachment):
    mock_server = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_server

    send_report_email(config, attachment)

    _, kwargs = mock_server.sendmail.call_args
    assert "Sales Report" in kwargs["msg"]