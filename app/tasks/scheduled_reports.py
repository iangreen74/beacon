"""Scheduled task runner for weekly performance reports."""

from typing import List
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import User
from app.services.email_reports import PerformanceReportGenerator
import logging

logger = logging.getLogger(__name__)


def send_weekly_performance_reports() -> None:
    """Send weekly performance reports to all administrators."""
    db = SessionLocal()
    try:
        admins = db.query(User).filter(User.role == "admin").all()
        logger.info(f"Sending weekly reports to {len(admins)} administrators")

        success_count = 0
        for admin in admins:
            if _send_admin_report(db, admin.id):
                success_count += 1

        logger.info(
            f"Weekly reports sent: {success_count}/{len(admins)} successful"
        )
    except Exception as e:
        logger.error(f"Error sending weekly reports: {e}")
    finally:
        db.close()


def _send_admin_report(db: Session, admin_id: int) -> bool:
    """Generate and send report for a single administrator."""
    try:
        generator = PerformanceReportGenerator(db)
        report_data = generator.generate_weekly_report(admin_id)

        if not report_data:
            logger.info(f"No report data generated for admin {admin_id}")
            return False

        return generator.send_report_email(report_data)
    except Exception as e:
        logger.error(f"Error sending report for admin {admin_id}: {e}")
        return False


def get_report_preview(db: Session, admin_id: int) -> dict:
    """Generate report preview for testing purposes."""
    generator = PerformanceReportGenerator(db)
    return generator.generate_weekly_report(admin_id)
