from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Text, BigInteger
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import List, Optional
import enum
from datetime import datetime, timezone

from app.db.base import Base, TimestampMixin

class GenderEnum(str, enum.Enum):
    male = "male"
    female = "female"
    any = "any"

class AgeCategoryEnum(str, enum.Enum):
    teen = "teen"  # 14-17
    adult = "adult"  # 18+

class MessageTypeEnum(str, enum.Enum):
    text = "text"
    photo = "photo"
    video = "video"
    voice = "voice"

class ReportCategoryEnum(str, enum.Enum):
    spam = "spam"
    insult = "insult"
    nsfw = "nsfw"
    scam = "scam"
    other = "other"

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    nickname: Mapped[str] = mapped_column(String(50))
    age: Mapped[int] = mapped_column(Integer)
    age_category: Mapped[AgeCategoryEnum] = mapped_column(Enum(AgeCategoryEnum), default=AgeCategoryEnum.adult)
    gender: Mapped[GenderEnum] = mapped_column(Enum(GenderEnum))
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    premium_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    chosen_emoji: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    app_language: Mapped[str] = mapped_column(String(2), default="ru")
    referred_by_referral_id: Mapped[Optional[int]] = mapped_column(ForeignKey("referrals.id"), nullable=True)
    
    likes: Mapped[int] = mapped_column(Integer, default=0)
    dislikes: Mapped[int] = mapped_column(Integer, default=0)
    total_chat_seconds: Mapped[int] = mapped_column(Integer, default=0)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)

class Chat(Base, TimestampMixin):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_a_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user_b_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    # Fixed: Use timezone-aware datetime (was datetime.utcnow which returns naive)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_reason: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # manual/report/timeout
    language: Mapped[str] = mapped_column(String(2), default="ru")

    messages: Mapped[List["Message"]] = relationship("Message", back_populates="chat")

class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"))
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    type: Mapped[MessageTypeEnum] = mapped_column(Enum(MessageTypeEnum), default=MessageTypeEnum.text)
    content_url_or_text: Mapped[str] = mapped_column(Text)
    
    chat: Mapped["Chat"] = relationship("Chat", back_populates="messages")

class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    chat_id: Mapped[Optional[int]] = mapped_column(ForeignKey("chats.id"), nullable=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reported_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    category: Mapped[ReportCategoryEnum] = mapped_column(Enum(ReportCategoryEnum))
    status: Mapped[str] = mapped_column(String(20), default="open") # open/reviewed/actioned
    resolved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True) # Admin ID

class Rating(Base, TimestampMixin):
    __tablename__ = "ratings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"))
    from_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    to_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    value: Mapped[str] = mapped_column(String(10)) # like/dislike

class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    type: Mapped[str] = mapped_column(String(50)) # topup/premium/remove_dislike
    stars_amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20)) # pending/completed/failed

class Referral(Base, TimestampMixin):
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    created_by_admin_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    uses_count: Mapped[int] = mapped_column(Integer, default=0)

class ReferralClaim(Base, TimestampMixin):
    """Referral captured from /start until the user finishes onboarding."""
    __tablename__ = "referral_claims"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    referral_id: Mapped[int] = mapped_column(ForeignKey("referrals.id"))

class AdminLog(Base, TimestampMixin):
    __tablename__ = "admin_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    admin_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100))
    target_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
