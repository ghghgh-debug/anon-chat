"""
Admin API routes — reports, statistics, referrals, user management.
All endpoints require admin authentication (checked server-side).
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_admin_user
from app.db.session import get_db
from app.services.user import user_service
from app.services.moderation import moderation_service
from app.services.chat import chat_service
from app.models.models import User, Chat, Report, Transaction, Referral, AdminLog
from app.core.config import get_settings

router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()


# --- Schemas ---

class ResolveReportRequest(BaseModel):
    action: str  # ban / warn / dismiss

class CreateReferralRequest(BaseModel):
    code: Optional[str] = None  # auto-generate if not provided


# --- Admin action logging ---

async def log_admin_action(db: AsyncSession, admin_id: int, action: str, target_id: int = None):
    """Log every admin action for accountability."""
    log = AdminLog(
        admin_id=admin_id,
        action=action,
        target_id=target_id,
    )
    db.add(log)
    await db.flush()


# --- Routes ---

@router.get("/stats")
async def admin_stats(
    tg_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive admin dashboard statistics."""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)

    # Total users
    total_users = await db.execute(select(func.count(User.id)))
    total_users = total_users.scalar() or 0

    # Users registered today
    today_users = await db.execute(
        select(func.count(User.id)).where(User.created_at >= day_ago)
    )
    today_users = today_users.scalar() or 0

    # Users registered this week
    week_users = await db.execute(
        select(func.count(User.id)).where(User.created_at >= week_ago)
    )
    week_users = week_users.scalar() or 0

    # Premium users
    premium_users = await db.execute(
        select(func.count(User.id)).where(User.is_premium == True)
    )
    premium_users = premium_users.scalar() or 0

    # Total chats ever
    total_chats = await db.execute(select(func.count(Chat.id)))
    total_chats = total_chats.scalar() or 0

    # Active chats right now
    active_chats = await db.execute(
        select(func.count(Chat.id)).where(Chat.ended_at.is_(None))
    )
    active_chats = active_chats.scalar() or 0

    # Open reports
    open_reports = await moderation_service.get_report_count(db)

    # Revenue (total stars from completed transactions)
    revenue = await db.execute(
        select(func.sum(Transaction.stars_amount)).where(
            Transaction.status == "completed"
        )
    )
    revenue = revenue.scalar() or 0

    # Online users
    from app.services.matching import matching_service
    online_count = await matching_service.get_online_count()

    # Banned users
    banned_users = await db.execute(
        select(func.count(User.id)).where(User.is_banned == True)
    )
    banned_users = banned_users.scalar() or 0

    return {
        "users": {
            "total": total_users,
            "today": today_users,
            "this_week": week_users,
            "premium": premium_users,
            "banned": banned_users,
            "online_now": online_count,
        },
        "chats": {
            "total": total_chats,
            "active_now": active_chats,
        },
        "reports": {
            "open": open_reports,
        },
        "revenue": {
            "total_stars": revenue,
        },
    }


@router.get("/reports")
async def get_reports(
    limit: int = 50,
    offset: int = 0,
    tg_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get open reports with chat transcript and user info."""
    reports = await moderation_service.get_open_reports(db, limit, offset)
    result = []
    for r in reports:
        # Get reporter and reported user info
        reporter = await user_service.get_user_by_id(db, r.reporter_id)
        reported = await user_service.get_user_by_id(db, r.reported_id)

        # Get chat messages (transcript for review)
        messages = []
        if r.chat_id:
            msgs = await chat_service.get_chat_messages(db, r.chat_id, limit=100)
            messages = [
                {
                    "sender_id": m.sender_id,
                    "type": m.type.value,
                    "content": m.content_url_or_text,
                    "sent_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in msgs
            ]

        result.append({
            "id": r.id,
            "category": r.category.value if hasattr(r.category, 'value') else r.category,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "reporter": {
                "id": reporter.id if reporter else None,
                "nickname": reporter.nickname if reporter else "Unknown",
                "tg_id": reporter.tg_id if reporter else None,
            },
            "reported": {
                "id": reported.id if reported else None,
                "nickname": reported.nickname if reported else "Unknown",
                "tg_id": reported.tg_id if reported else None,
                "is_banned": reported.is_banned if reported else False,
                "total_reports": reported.dislikes if reported else 0,
            },
            "chat_transcript": messages,
        })

    return {"reports": result, "total": len(result)}


@router.post("/reports/{report_id}/resolve")
async def resolve_report(
    report_id: int,
    data: ResolveReportRequest,
    tg_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Resolve a report: ban, warn, or dismiss."""
    admin = await user_service.get_user_by_tg_id(db, tg_user["id"])
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    report = await moderation_service.resolve_report(db, report_id, admin.id, data.action)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    await log_admin_action(db, admin.id, f"resolve_report_{data.action}", report_id)

    return {"status": "resolved", "action": data.action}


@router.post("/users/{user_id}/ban")
async def ban_user(
    user_id: int,
    tg_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Ban a user."""
    admin = await user_service.get_user_by_tg_id(db, tg_user["id"])
    await user_service.ban_user(db, user_id)
    await log_admin_action(db, admin.id, "ban_user", user_id)

    # Force disconnect from Centrifugo
    user = await user_service.get_user_by_id(db, user_id)
    if user:
        from app.services.centrifugo import centrifugo_service
        await centrifugo_service.disconnect_user(user.tg_id)

    return {"status": "banned"}


@router.post("/users/{user_id}/unban")
async def unban_user(
    user_id: int,
    tg_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Unban a user."""
    admin = await user_service.get_user_by_tg_id(db, tg_user["id"])
    await user_service.unban_user(db, user_id)
    await log_admin_action(db, admin.id, "unban_user", user_id)
    return {"status": "unbanned"}


# --- Referrals ---

@router.post("/referrals")
async def create_referral(
    data: CreateReferralRequest,
    tg_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a referral link (admin only)."""
    admin = await user_service.get_user_by_tg_id(db, tg_user["id"])
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    code = data.code or uuid.uuid4().hex[:8]

    referral = Referral(
        code=code,
        created_by_admin_id=admin.id,
    )
    db.add(referral)
    await db.flush()

    await log_admin_action(db, admin.id, "create_referral", referral.id)

    return {
        "id": referral.id,
        "code": referral.code,
        "link": f"https://t.me/YourBotName?start=ref_{code}",
    }


@router.get("/referrals")
async def get_referrals(
    tg_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all referral links with usage stats."""
    result = await db.execute(
        select(Referral).order_by(Referral.created_at.desc())
    )
    referrals = result.scalars().all()
    return {
        "referrals": [
            {
                "id": r.id,
                "code": r.code,
                "uses_count": r.uses_count,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "link": f"https://t.me/YourBotName?start=ref_{r.code}",
            }
            for r in referrals
        ]
    }


@router.get("/logs")
async def get_admin_logs(
    limit: int = 100,
    tg_user: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get admin action logs."""
    result = await db.execute(
        select(AdminLog).order_by(AdminLog.created_at.desc()).limit(limit)
    )
    logs = result.scalars().all()
    return {
        "logs": [
            {
                "id": l.id,
                "admin_id": l.admin_id,
                "action": l.action,
                "target_id": l.target_id,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ]
    }
