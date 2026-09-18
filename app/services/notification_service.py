"""Notification service — console log + SMTP stub + DB record.

Designed to be replaceable with Slack, Teams, or real SMTP later.
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.repositories.repositories import NotificationRepository

logger = logging.getLogger(__name__)
settings = get_settings()


class NotificationService:
    def __init__(self, db: Session):
        self.repo = NotificationRepository(db)

    def send_notification(
        self,
        request_id: str,
        ticket_id: str | None,
        recipient: str,
        subject: str,
        body: str,
        channel: str = "email",
    ) -> bool:
        """Send a notification and record its status. Returns True if sent."""
        notif = self.repo.create(
            request_id=request_id,
            ticket_id=ticket_id,
            channel=channel,
            recipient=recipient,
            subject=subject,
            body=body,
        )

        success = False
        if settings.smtp_enabled:
            success = self._send_email(recipient, subject, body)
        else:
            success = self._console_notify(recipient, subject, body)

        if success:
            self.repo.mark_sent(notif.notification_id)
        else:
            self.repo.mark_failed(notif.notification_id, "Delivery failed — check logs")

        return success

    def notify_escalation(self, request_id: str, ticket_id: str,
                          team: str, contact_email: str,
                          employee_name: str, category: str,
                          description: str, risk: str) -> bool:
        subject = f"[Veridian IT] New {risk} Ticket — {category} — {ticket_id}"
        body = f"""A new IT support ticket has been created and requires your attention.

Ticket ID      : {ticket_id}
Request ID     : {request_id}
Employee       : {employee_name}
Category       : {category}
Risk Level     : {risk}
Assigned Team  : {team}

Description:
{description}

Please log in to the IT dashboard to view full details and the audit trail.

---
Veridian IT Service Agent
"""
        return self.send_notification(
            request_id=request_id,
            ticket_id=ticket_id,
            recipient=contact_email,
            subject=subject,
            body=body,
        )

    def _send_email(self, to: str, subject: str, body: str) -> bool:
        try:
            msg = MIMEMultipart()
            msg["From"] = settings.smtp_from
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)

            logger.info("EMAIL SENT → %s | %s", to, subject)
            return True
        except Exception as exc:
            logger.error("Email delivery failed: %s", exc)
            return False

    def _console_notify(self, to: str, subject: str, body: str) -> bool:
        """Fallback — log notification to console."""
        logger.info(
            "\n%s\n📧 NOTIFICATION (console fallback)\nTo: %s\nSubject: %s\n\n%s\n%s",
            "=" * 60, to, subject, body, "=" * 60,
        )
        return True  # Console log is always "successful"

