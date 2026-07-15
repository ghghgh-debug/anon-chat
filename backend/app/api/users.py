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
<<<<<<< HEAD
=======
from app.models.models import Referral, ReferralClaim
from sqlalchemy import select
>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8
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
<<<<<<< HEAD
    agreed_to_rules: bool = Field(..., description="Must agree to 14+ rules")
=======
    agreed_to_rules: bool = Field(..., description="Must agree to rules")
    app_language: str = Field(default="ru", pattern="^(ru|en|uz)$")
>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8

class ProfileUpdateRequest(BaseModel):
    nickname: Optional[str] = Field(None, min_length=2, max_length=50)
    age: Optional[int] = Field(None, ge=14, le=99)
    gender: Optional[str] = Field(None, pattern="^(male|female)$")
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    chosen_emoji: Optional[str] = None
<<<<<<< HEAD
=======
    app_language: Optional[str] = Field(None, pattern="^(ru|en|uz)$")
>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8

class UserResponse(BaseModel):
    id: int
    tg_id: int
    nickname: str
    age: int
<<<<<<< HEAD
=======
    age_category: str
>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8
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
<<<<<<< HEAD
=======
    app_language: str
>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8

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
<<<<<<< HEAD
        raise HTTPException(status_code=400, detail="You must agree to the rules (14+)")
=======
        raise HTTPException(status_code=400, detail="You must agree to the rules")

    # Auto-calculate age category
    from app.models.models import AgeCategoryEnum
    age_category = AgeCategoryEnum.teen if data.age < 18 else AgeCategoryEnum.adult
>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8

    user, created = await user_service.get_or_create_user(
        db,
        tg_id=tg_user["id"],
        defaults={
            "nickname": data.nickname,
            "age": data.age,
<<<<<<< HEAD
            "gender": data.gender,
            "avatar_url": data.avatar_url,
            "bio": data.bio,
=======
            "age_category": age_category,
            "gender": data.gender,
            "avatar_url": data.avatar_url,
            "bio": data.bio,
            "app_language": data.app_language,
>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8
        },
    )

    if not created:
        # Update existing user
        user = await user_service.update_profile(db, user.id, {
            "nickname": data.nickname,
            "age": data.age,
<<<<<<< HEAD
            "gender": data.gender,
            "avatar_url": data.avatar_url,
            "bio": data.bio,
        })

=======
            "age_category": age_category,
            "gender": data.gender,
            "avatar_url": data.avatar_url,
            "bio": data.bio,
            "app_language": data.app_language,
        })

    # A referral is captured by the bot before the Mini App onboarding begins.
    # It is applied once, so reopening a referral link cannot inflate counters.
    claim_result = await db.execute(select(ReferralClaim).where(ReferralClaim.tg_id == tg_user["id"]))
    claim = claim_result.scalar_one_or_none()
    if claim and not user.referred_by_referral_id:
        referral = await db.get(Referral, claim.referral_id)
        if referral:
            user.referred_by_referral_id = referral.id
            referral.uses_count += 1
        await db.delete(claim)
        await db.flush()

>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8
    rep = await user_service.get_reputation_percent(user)
    return UserResponse(
        id=user.id,
        tg_id=user.tg_id,
        nickname=user.nickname,
        age=user.age,
<<<<<<< HEAD
=======
        age_category=user.age_category.value if hasattr(user.age_category, 'value') else user.age_category,
>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8
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
<<<<<<< HEAD
=======
        app_language=user.app_language,
>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8
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

<<<<<<< HEAD
=======
    # Recalculate age category if needed
    from app.models.models import AgeCategoryEnum
    expected_category = AgeCategoryEnum.teen if user.age < 18 else AgeCategoryEnum.adult
    if user.age_category != expected_category:
        user.age_category = expected_category
        await db.flush()

>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8
    rep = await user_service.get_reputation_percent(user)
    return UserResponse(
        id=user.id,
        tg_id=user.tg_id,
        nickname=user.nickname,
        age=user.age,
<<<<<<< HEAD
=======
        age_category=user.age_category.value if hasattr(user.age_category, 'value') else user.age_category,
>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8
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
<<<<<<< HEAD
=======
        app_language=user.app_language,
>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8
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

<<<<<<< HEAD
=======
    # Auto-calculate age category if age is being updated
    if "age" in update_data:
        from app.models.models import AgeCategoryEnum
        update_data["age_category"] = AgeCategoryEnum.teen if update_data["age"] < 18 else AgeCategoryEnum.adult

>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8
    user = await user_service.update_profile(db, user.id, update_data)
    rep = await user_service.get_reputation_percent(user)
    return UserResponse(
        id=user.id,
        tg_id=user.tg_id,
        nickname=user.nickname,
        age=user.age,
<<<<<<< HEAD
=======
        age_category=user.age_category.value if hasattr(user.age_category, 'value') else user.age_category,
>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8
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
<<<<<<< HEAD
=======
        app_language=user.app_language,
>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8
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
