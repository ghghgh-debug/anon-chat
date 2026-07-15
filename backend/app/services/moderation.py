"""
Moderation service — reports, blacklist, NSFW detection placeholder.
"""

from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.models.models import Report, ReportCategoryEnum, User
from app.services.user import user_service
from app.services.centrifugo import centrifugo_service
from app.core.config import get_settings


# Number of confirmed reports before auto-ban
AUTO_BAN_THRESHOLD = 5


class ModerationService:
    def __init__(self):
        self.settings = get_settings()
        self.redis: Optional[aioredis.Redis] = None

    async def init_redis(self):
        if self.redis is None:
            self.redis = aioredis.from_url(
                self.settings.REDIS_URL,
                decode_responses=True,
            )

    async def create_report(
        self,
        db: AsyncSession,
        chat_id: int,
        reporter_id: int,
        reported_id: int,
        category: ReportCategoryEnum,
    ) -> Report:
        """
        Create a report. Also:
        - Auto-dislike the reported user
        - Check if auto-ban threshold is reached
        """
        report = Report(
            chat_id=chat_id,
            reporter_id=reporter_id,
            reported_id=reported_id,
            category=category,
            status="open",
        )
        db.add(report)
        await db.flush()

        # Auto-dislike on report
        await db.execute(
            update(User)
            .where(User.id == reported_id)
            .values(dislikes=User.dislikes + 1)
        )

        # Check auto-ban threshold
        result = await db.execute(
            select(func.count(Report.id)).where(
                Report.reported_id == reported_id,
                Report.status.in_(["open", "actioned"]),
            )
        )
        report_count = result.scalar() or 0
        if report_count >= AUTO_BAN_THRESHOLD:
            await user_service.ban_user(db, reported_id)
            # Force disconnect banned user from Centrifugo
            user = await user_service.get_user_by_id(db, reported_id)
            if user:
                await centrifugo_service.disconnect_user(user.tg_id)

        await db.flush()
        return report

    async def get_open_reports(
        self, db: AsyncSession, limit: int = 50, offset: int = 0
    ) -> List[Report]:
        """Get pending reports for admin review."""
        result = await db.execute(
            select(Report)
            .where(Report.status == "open")
            .order_by(Report.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def resolve_report(
        self,
        db: AsyncSession,
        report_id: int,
        admin_id: int,
        action: str,  # "ban", "warn", "dismiss"
    ) -> Optional[Report]:
        """Resolve a report with admin action."""
        result = await db.execute(select(Report).where(Report.id == report_id))
        report = result.scalar_one_or_none()
        if not report:
            return None

        if action == "ban":
            report.status = "actioned"
            await user_service.ban_user(db, report.reported_id)
            user = await user_service.get_user_by_id(db, report.reported_id)
            if user:
                await centrifugo_service.disconnect_user(user.tg_id)
        elif action == "warn":
            report.status = "actioned"
            # Could send a warning message via bot here
        elif action == "dismiss":
            report.status = "reviewed"
            # Optionally remove the auto-dislike
        else:
            return None

        report.resolved_by = admin_id
        await db.flush()
        return report

    async def get_report_count(self, db: AsyncSession) -> int:
        """Get count of open reports."""
        result = await db.execute(
            select(func.count(Report.id)).where(Report.status == "open")
        )
        return result.scalar() or 0

    # --- Blacklist ---

    async def add_to_blacklist(self, user_id: int, blocked_id: int) -> None:
        """Add a user to another user's blacklist (stored in Redis for fast matching lookups)."""
        await self.init_redis()
        await self.redis.sadd(f"blacklist:{user_id}", blocked_id)

    async def remove_from_blacklist(self, user_id: int, blocked_id: int) -> None:
        """Remove a user from blacklist."""
        await self.init_redis()
        await self.redis.srem(f"blacklist:{user_id}", blocked_id)

    async def get_blacklist(self, user_id: int) -> List[int]:
        """Get a user's full blacklist."""
        await self.init_redis()
        members = await self.redis.smembers(f"blacklist:{user_id}")
        return [int(m) for m in members]

    async def is_blacklisted(self, user_id: int, target_id: int) -> bool:
        """Check if target_id is in user_id's blacklist."""
        await self.init_redis()
        return await self.redis.sismember(f"blacklist:{user_id}", target_id)

    # --- NSFW Detection (placeholder) ---

    async def check_media_nsfw(self, file_path: str) -> bool:
        """
        Check if an uploaded media file contains NSFW content.
        
        TODO: Integrate with an actual NSFW detection API:
        - Option 1: Use a local model (e.g., nsfw_detector with TensorFlow)
        - Option 2: Use a cloud API (AWS Rekognition, Google Vision Safety)
        - Option 3: Use open-source NSFW classifiers
        
        For now, returns False (allow all). In production, this MUST be implemented.
        """
        return False


moderation_service = ModerationService()
