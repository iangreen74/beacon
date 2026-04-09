"""Notification service for sending trend alerts via email.

Handles formatting and delivery of sentiment trend notifications
to team managers and administrators.
"""

import logging
from typing import List, Optional
from datetime import datetime

try:
    import aiosmtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    SMTP_AVAILABLE = True
except ImportError:
    SMTP_AVAILABLE = False

from app.schemas import TrendAlert

logger = logging.getLogger(__name__)


class NotificationService:
    """Sends email notifications for detected sentiment trends."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        from_email: str,
    ):
        if not SMTP_AVAILABLE:
            logger.warning("aiosmtplib not available, notifications will be logged only")

        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.from_email = from_email

    def _format_trend_email(self, alert: TrendAlert) -> str:
        """Format trend alert as HTML email content."""
        trend_emoji = {
            "declining": "📉",
            "improving": "📈",
            "stable": "➡️",
        }

        emoji = trend_emoji.get(alert.trend_direction, "")
        avg_display = f"{alert.moving_average:.1f}" if alert.moving_average else "N/A"

        html = f"""
        <html>
        <body>
            <h2>{emoji} Team Sentiment Alert: {alert.team_name}</h2>
            <p><strong>Trend Direction:</strong> {alert.trend_direction.capitalize()}</p>
            <p><strong>Moving Average (7 days):</strong> {avg_display}/10</p>
            <p><strong>Anomalies Detected:</strong> {alert.anomaly_count}</p>
            <hr>
            <p>This is an automated sentiment trend alert. Please review your team's pulse responses.</p>
            <p><em>Analyzed at: {alert.analyzed_at.strftime('%Y-%m-%d %H:%M UTC')}</em></p>
        </body>
        </html>
        """
        return html

    async def send_trend_alert(
        self, alert: TrendAlert, recipient_emails: List[str]
    ) -> bool:
        """Send trend alert email to specified recipients."""
        if not SMTP_AVAILABLE:
            logger.info(
                f"Would send alert for team {alert.team_name} to {recipient_emails}"
            )
            return False

        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = f"Sentiment Trend Alert: {alert.team_name}"
            message["From"] = self.from_email
            message["To"] = ", ".join(recipient_emails)

            html_content = self._format_trend_email(alert)
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)

            async with aiosmtplib.SMTP(
                hostname=self.smtp_host, port=self.smtp_port
            ) as smtp:
                await smtp.login(self.smtp_username, self.smtp_password)
                await smtp.send_message(message)

            logger.info(f"Sent trend alert for team {alert.team_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to send trend alert: {str(e)}")
            return False

    async def send_batch_alerts(
        self, alerts: List[TrendAlert], admin_email: str
    ) -> int:
        """Send multiple trend alerts to admin email."""
        sent_count = 0
        for alert in alerts:
            success = await self.send_trend_alert(alert, [admin_email])
            if success:
                sent_count += 1
        return sent_count
