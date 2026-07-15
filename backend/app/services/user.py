"""
User service — profile management, reputation, premium, blacklist.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User, Rating, GenderEnum
from app.core.config import get_settings


class UserService:
    def __init__(self):
        self.settings = get_settings()

    async def get_or_create_user(
        self, db: AsyncSession, tg_id: int, defaults: dict = None
    ) -> tuple[User, bool]:
        """
        Get existing user by Telegram ID, or create a new one.
        Returns (user, created).
        """
        result = await db.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()

        if user:
            return user, False

        # Create new user with defaults
        user_data = {
            "tg_id": tg_id,
            "nickname": f"User{tg_id % 10000}",
            "age": 14,
            "gender": GenderEnum.any,
            "likes": 0,
            "dislikes": 0,
            "total_chat_seconds": 0,
            "is_premium": False,
            "is_banned": False,
        }
        if defaults:
            user_data.update(defaults)

        # Auto-grant premium to admins
        if tg_id in self.settings.ADMIN_IDS:
            user_data["is_premium"] = True
            user_data["premium_until"] = datetime.now(timezone.utc) + timedelta(days=36500)

        user = User(**user_data)
        db.add(user)
        await db.flush()
        return user, True

    async def get_user_by_tg_id(
        self, db: AsyncSession, tg_id: int
    ) -> Optional[User]:
        result = await db.execute(select(User).where(User.tg_id == tg_id))
        return result.scalar_one_or_none()

    async def get_user_by_id(
        self, db: AsyncSession, user_id: int
    ) -> Optional[User]:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def update_profile(
        self, db: AsyncSession, user_id: int, data: dict
    ) -> Optional[User]:
        """Update user profile fields. Only allows safe fields."""
        allowed_fields = {"nickname", "age", "age_category", "gender", "avatar_url", "bio", "chosen_emoji", "app_language"}
        safe_data = {k: v for k, v in data.items() if k in allowed_fields}
        if not safe_data:
            return None

        await db.execute(
            update(User).where(User.id == user_id).values(**safe_data)
        )
        await db.flush()
        return await self.get_user_by_id(db, user_id)

    async def add_rating(
        self,
        db: AsyncSession,
        chat_id: int,
        from_user_id: int,
        to_user_id: int,
        value: str,
    ) -> None:
        """
        Add a like or dislike rating. Updates the target user's counters.
        Prevents duplicate ratings for the same chat.
        """
        # Check for duplicate
        existing = await db.execute(
            select(Rating).where(
                Rating.chat_id == chat_id,
                Rating.from_user_id == from_user_id,
            )
        )
        if existing.scalar_one_or_none():
            return  # Already rated

        rating = Rating(
            chat_id=chat_id,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            value=value,
        )
        db.add(rating)

        # Update counters on target user
        if value == "like":
            await db.execute(
                update(User).where(User.id == to_user_id).values(likes=User.likes + 1)
            )
        elif value == "dislike":
            await db.execute(
                update(User)
                .where(User.id == to_user_id)
                .values(dislikes=User.dislikes + 1)
            )

        await db.flush()

    async def remove_dislike(
        self, db: AsyncSession, user_id: int
    ) -> bool:
        """Remove one dislike from user's profile (premium feature, costs stars)."""
        user = await self.get_user_by_id(db, user_id)
        if not user or user.dislikes <= 0:
            return False
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(dislikes=User.dislikes - 1)
        )
        await db.flush()
        return True

    async def activate_premium(
        self, db: AsyncSession, user_id: int, duration_days: int
    ) -> User:
        """Activate premium for a user for the given number of days."""
        user = await self.get_user_by_id(db, user_id)
        if not user:
            return None

        now = datetime.now(timezone.utc)
        # Extend existing premium if still active
        if user.premium_until and user.premium_until > now:
            new_until = user.premium_until + timedelta(days=duration_days)
        else:
            new_until = now + timedelta(days=duration_days)

        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_premium=True, premium_until=new_until)
        )
        await db.flush()
        return await self.get_user_by_id(db, user_id)

    async def check_premium_expiry(self, db: AsyncSession, user_id: int) -> bool:
        """Check if premium has expired and deactivate if so. Returns True if still premium."""
        user = await self.get_user_by_id(db, user_id)
        if not user:
            return False

        # Admins always premium
        if user.tg_id in self.settings.ADMIN_IDS:
            return True

        if user.is_premium and user.premium_until:
            if user.premium_until < datetime.now(timezone.utc):
                await db.execute(
                    update(User)
                    .where(User.id == user_id)
                    .values(is_premium=False)
                )
                await db.flush()
                return False
        return user.is_premium

    async def ban_user(self, db: AsyncSession, user_id: int) -> None:
        """Ban a user."""
        await db.execute(
            update(User).where(User.id == user_id).values(is_banned=True)
        )
        await db.flush()

    async def unban_user(self, db: AsyncSession, user_id: int) -> None:
        """Unban a user."""
        await db.execute(
            update(User).where(User.id == user_id).values(is_banned=False)
        )
        await db.flush()

    async def get_leaderboard(
        self, db: AsyncSession, limit: int = 50
    ) -> List[User]:
        """Get top users by total chat seconds."""
        result = await db.execute(
            select(User)
            .where(User.is_banned == False)
            .order_by(User.total_chat_seconds.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_reputation_percent(self, user: User) -> float:
        """Calculate positive reputation percentage."""
        total = user.likes + user.dislikes
        if total == 0:
            return 100.0
        return round((user.likes / total) * 100, 1)

    async def get_user_count(self, db: AsyncSession) -> int:
        """Get total registered user count."""
        result = await db.execute(select(func.count(User.id)))
        return result.scalar() or 0


user_service = UserService()
