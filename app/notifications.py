from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification, User
from app.schemas import NotificationCreate


class NotificationService:
    """Service for managing user notifications."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_notification(
        self,
        user_id: int,
        notification_data: NotificationCreate
    ) -> Notification:
        """Create a new notification for a user."""
        notification = Notification(
            user_id=user_id,
            message=notification_data.message,
            notification_type=notification_data.notification_type,
            related_entity_id=notification_data.related_entity_id,
            created_at=datetime.utcnow(),
            read=False
        )
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def get_user_notifications(
        self,
        user_id: int,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Notification]:
        """Get notifications for a user."""
        query = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            query = query.where(Notification.read == False)
        query = query.order_by(Notification.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def mark_as_read(self, notification_id: int, user_id: int) -> Optional[Notification]:
        """Mark a notification as read."""
        query = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id
        )
        result = await self.db.execute(query)
        notification = result.scalar_one_or_none()
        if notification:
            notification.read = True
            await self.db.commit()
            await self.db.refresh(notification)
        return notification

    async def mark_all_as_read(self, user_id: int) -> int:
        """Mark all notifications as read for a user."""
        query = select(Notification).where(
            Notification.user_id == user_id,
            Notification.read == False
        )
        result = await self.db.execute(query)
        notifications = result.scalars().all()
        count = 0
        for notification in notifications:
            notification.read = True
            count += 1
        await self.db.commit()
        return count

    async def delete_notification(self, notification_id: int, user_id: int) -> bool:
        """Delete a notification."""
        query = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id
        )
        result = await self.db.execute(query)
        notification = result.scalar_one_or_none()
        if notification:
            await self.db.delete(notification)
            await self.db.commit()
            return True
        return False


async def send_notification(
    db: AsyncSession,
    user_id: int,
    message: str,
    notification_type: str = "info",
    related_entity_id: Optional[int] = None
) -> Notification:
    """Helper function to send a notification to a user."""
    service = NotificationService(db)
    notification_data = NotificationCreate(
        message=message,
        notification_type=notification_type,
        related_entity_id=related_entity_id
    )
    return await service.create_notification(user_id, notification_data)
