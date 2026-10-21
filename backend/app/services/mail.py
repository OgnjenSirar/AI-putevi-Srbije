"""Slanje odgovora (u demou prema Mailpit-u) uz ocuvanje prepiske (Message-ID, In-Reply-To, References)."""
import logging
import smtplib
import uuid
from email.message import EmailMessage
from email.utils import formatdate

from ..config import get_settings

log = logging.getLogger("mail")
settings = get_settings()


def send_reply(to_addr: str, to_name: str, subject: str, body: str, in_reply_to: str = "",
               references: list[str] | None = None) -> tuple[str, bool, str]:
    msg_id = f"<kc-{uuid.uuid4().hex[:16]}@{settings.mail_domain}>"
    msg = EmailMessage()
    msg["From"] = settings.mail_from
    msg["To"] = f"{to_name} <{to_addr}>" if to_name else to_addr
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = msg_id
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = " ".join((references or []) + [in_reply_to])
    msg["X-KC-Demo"] = "true"
    msg.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as s:
            s.send_message(msg)
        return msg_id, True, ""
    except Exception as e:
        log.warning("Slanje mejla nije uspelo: %s", e)
        return msg_id, False, str(e)
