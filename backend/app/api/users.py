"""
User API routes — profile, onboarding, reputation.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.session import get_db
from app.services.user import user_service
from app.services.moderation import moderation_service
from app.core.config import get_settings

router = APIRouter(prefix="/users", tags=["users"])
settings = get_settings()


# --- Schemas ---

class OnboardingRequest(BaseModel):
    nickname: str = Field(..., min_length=2, max_length=50)
    age: int = Field(..., ge=14, le=99)
    gender: str = Field(..., pattern="^(male|female)$")
    topics: List[str] = Field(default_factory=list)
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    agreed_to_rules: bool = Field(..., description="Must agree to 14+ rules")

class ProfileUpdateRequest(BaseModel):
    nickname: Optional[str] = Field(None, min_length=2, max_length=50)
    age: Optional[int] = Field(None, ge=14, le=99)
    gender: Optional[str] = Field(None, pattern="^(male|female)$")
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    chosen_emoji: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    tg_id: int
    nickname: str
    age: int
    gender: str
    avatar_url: Optional[str]
    bio: Optional[str]
    is_premium: bool
    chosen_emoji: Optional[str]
    likes: int
    dislikes: int
    reputation_percent: float
    total_chat_seconds: int
    is_admin: bool
    is_banned: bool

class BlacklistRequest(BaseModel):
    blocked_user_id: int


# --- Routes ---

@router.post("/onboarding", response_model=UserResponse)
async def onboarding(
    data: OnboardingRequest,
    tg_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Complete onboarding — create or update user profile."""
    if not data.agreed_to_rules:
        raise HTTPException(status_code=400, detail="You must agree to the rules (14+)")

    user, created = await user_service.get_or_create_user(
        db,
        tg_id=tg_user["id"],
        defaults={
            "nickname": data.nickname,
            "age": data.age,
            "gender": data.gender,
            "avatar_url": data.avatar_url,
            "bio": data.bio,
        },
    )

    if not created:
        # Update existing user
        user = await user_service.update_profile(db, user.id, {
            "nickname": data.nickname,
            "age": data.age,
            "gender": data.gender,
            "avatar_url": data.avatar_url,
            "bio": data.bio,
        })

    rep = await user_service.get_reputation_percent(user)
    return UserResponse(
        id=user.id,
        tg_id=user.tg_id,
        nickname=user.nickname,
        age=user.age,
        gender=user.gender.value if hasattr(user.gender, 'value') else user.gender,
        avatar_url=user.avatar_url,
        bio=user.bio,
        is_premium=user.is_premium,
        chosen_emoji=user.chosen_emoji,
        likes=user.likes,
        dislikes=user.dislikes,
        reputation_percent=rep,
        total_chat_seconds=user.total_chat_seconds,
        is_admin=user.tg_id in settings.ADMIN_IDS,
        is_banned=user.is_banned,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    tg_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's profile."""
    user = await user_service.get_user_by_tg_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Complete onboarding first.")

    if user.is_banned:
        raise HTTPException(status_code=403, detail="Your account has been banned.")

    # Check premium expiry
    await user_service.check_premium_expiry(db, user.id)

    rep = await user_service.get_reputation_percent(user)
    return UserResponse(
        id=user.id,
        tg_id=user.tg_id,
        nickname=user.nickname,
        age=user.age,
        gender=user.gender.value if hasattr(user.gender, 'value') else user.gender,
        avatar_url=user.avatar_url,
        bio=user.bio,
        is_premium=user.is_premium,
        chosen_emoji=user.chosen_emoji,
        likes=user.likes,
        dislikes=user.dislikes,
        reputation_percent=rep,
        total_chat_seconds=user.total_chat_seconds,
        is_admin=user.tg_id in settings.ADMIN_IDS,
        is_banned=user.is_banned,
    )


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    data: ProfileUpdateRequest,
    tg_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update profile fields."""
    user = await user_service.get_user_by_tg_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Only premium users can set emoji
    update_data = data.model_dump(exclude_none=True)
    if "chosen_emoji" in update_data and not user.is_premium:
        raise HTTPException(status_code=403, detail="Emoji badges require Premium")

    user = await user_service.update_profile(db, user.id, update_data)
    rep = await user_service.get_reputation_percent(user)
    return UserResponse(
        id=user.id,
        tg_id=user.tg_id,
        nickname=user.nickname,
        age=user.age,
        gender=user.gender.value if hasattr(user.gender, 'value') else user.gender,
        avatar_url=user.avatar_url,
        bio=user.bio,
        is_premium=user.is_premium,
        chosen_emoji=user.chosen_emoji,
        likes=user.likes,
        dislikes=user.dislikes,
        reputation_percent=rep,
        total_chat_seconds=user.total_chat_seconds,
        is_admin=user.tg_id in settings.ADMIN_IDS,
        is_banned=user.is_banned,
    )


@router.get("/leaderboard")
async def leaderboard(
    tg_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get leaderboard — top users by chat time."""
    users = await user_service.get_leaderboard(db, limit=50)
    result = []
    for i, u in enumerate(users):
        rep = await user_service.get_reputation_percent(u)
        result.append({
            "rank": i + 1,
            "nickname": u.nickname,
            "total_chat_seconds": u.total_chat_seconds,
            "is_premium": u.is_premium,
            "chosen_emoji": u.chosen_emoji,
            "likes": u.likes,
            "dislikes": u.dislikes,
            "reputation_percent": rep,
        })
    return {"leaderboard": result}


@router.post("/blacklist")
async def add_blacklist(
    data: BlacklistRequest,
    tg_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a user to your blacklist."""
    user = await user_service.get_user_by_tg_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await moderation_service.add_to_blacklist(user.id, data.blocked_user_id)
    return {"status": "ok"}


@router.delete("/blacklist/{blocked_user_id}")
async def remove_blacklist(
    blocked_user_id: int,
    tg_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a user from your blacklist."""
    user = await user_service.get_user_by_tg_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await moderation_service.remove_from_blacklist(user.id, blocked_user_id)
    return {"status": "ok"}
