"""
Chat API routes — search, messaging, archive, ratings, reports.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
<<<<<<< HEAD
from pydantic import BaseModel, Field
=======
from pydantic import BaseModel, Field, model_validator
>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.session import get_db
from app.services.user import user_service
from app.services.chat import chat_service
from app.services.matching import matching_service
from app.services.moderation import moderation_service
from app.models.models import MessageTypeEnum, ReportCategoryEnum
from app.core.config import get_settings

router = APIRouter(prefix="/chat", tags=["chat"])
settings = get_settings()

<<<<<<< HEAD
=======
GAME_QUESTIONS = {
    "pd": {
        "ru": ["Правда или действие: выбери одно и задай вопрос собеседнику.", "Правда или действие: какой твой самый смешной страх?"],
        "en": ["Truth or dare: choose one and ask your partner.", "Truth or dare: what is your funniest fear?"],
        "uz": ["Haqiqat yoki jur'at: birini tanlang va suhbatdoshingizdan so'rang.", "Haqiqat yoki jur'at: eng kulgili qo'rquvingiz nima?"],
    },
    "never": {
        "ru": ["Я никогда не… не писал(а) первым(ой) человеку, который нравился.", "Я никогда не… не влюблялся(ась) с первого взгляда."],
        "en": ["Never have I ever… texted first someone I liked.", "Never have I ever… fallen in love at first sight."],
        "uz": ["Men hech qachon… yoqqan odamga birinchi bo'lib yozmaganman.", "Men hech qachon… bir qarashda sevib qolmaganman."],
    },
    "wouldyou": {
        "ru": ["Что выберешь: читать мысли или становиться невидимым?", "Что выберешь: путешествие в прошлое или в будущее?"],
        "en": ["Would you rather read minds or become invisible?", "Would you rather travel to the past or the future?"],
        "uz": ["Qaysini tanlaysiz: fikrlarni o'qishmi yoki ko'rinmas bo'lishmi?", "Qaysini tanlaysiz: o'tmishga yoki kelajakka sayohatmi?"],
    },
}

def _game_question(content: str, language: str) -> Optional[dict]:
    """Return a localized random game prompt for /pd, /never or /wouldyou."""
    import random
    command = content.strip().lower().split(maxsplit=1)[0].lstrip("/")
    aliases = {"пд": "pd", "правда": "pd", "яникогда": "never", "никогда": "never", "выбор": "wouldyou"}
    game = aliases.get(command, command)
    if game not in GAME_QUESTIONS:
        return None
    return {"game": game, "content": random.choice(GAME_QUESTIONS[game][language])}

>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8

# --- Schemas ---

class SearchRequest(BaseModel):
    find_gender: str = Field(default="any", pattern="^(male|female|any)$")
<<<<<<< HEAD
=======
    age_category: str = Field(default="any", pattern="^(teen|adult|any)$")
>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8
    age_from: int = Field(default=14, ge=14, le=99)
    age_to: int = Field(default=99, ge=14, le=99)
    topics: List[str] = Field(default_factory=list)
    vip_only: bool = False
<<<<<<< HEAD
=======
    chat_language: str = Field(default="ru", pattern="^(ru|en|uz)$")

    @model_validator(mode="after")
    def validate_age_range(self):
        if self.age_from > self.age_to:
            raise ValueError("age_from must not be greater than age_to")
        return self
>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8

class SendMessageRequest(BaseModel):
    chat_id: int
    type: str = Field(default="text", pattern="^(text|photo|video|voice)$")
    content: str

class RateRequest(BaseModel):
    chat_id: int
    to_user_id: int
    value: str = Field(..., pattern="^(like|dislike)$")

class ReportRequest(BaseModel):
    chat_id: int
    reported_id: int
    category: str = Field(..., pattern="^(spam|insult|nsfw|scam|other)$")

class TypingRequest(BaseModel):
    channel: str


# --- Routes ---

@router.post("/search")
async def search_partner(
    data: SearchRequest,
    tg_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Search for a chat partner.
    Returns match info if found immediately, or waiting room info if queued.
    """
    user = await user_service.get_user_by_tg_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="Complete onboarding first")
    if user.is_banned:
        raise HTTPException(status_code=403, detail="Account banned")

<<<<<<< HEAD
=======
    # One active conversation per account prevents duplicate matching rooms.
    if await chat_service.get_active_chat(db, user.id):
        raise HTTPException(status_code=409, detail="Finish your current chat before starting a new search")

>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8
    # Premium check for gender filter
    if data.find_gender != "any" and not user.is_premium:
        raise HTTPException(
            status_code=403,
            detail="Gender filter requires Premium subscription"
        )

    # VIP check
    if data.vip_only and not user.is_premium:
        raise HTTPException(status_code=403, detail="VIP rooms require Premium")

    # Get blacklist
    blacklist = await moderation_service.get_blacklist(user.id)

    room_key, token, matched = await matching_service.find_or_create_room(
        user_id=user.id,
        nickname=user.nickname,
        gender=user.gender.value if hasattr(user.gender, 'value') else user.gender,
        age=user.age,
<<<<<<< HEAD
        find_gender=data.find_gender,
        age_from=data.age_from,
        age_to=data.age_to,
        topics=data.topics,
=======
        age_category=user.age_category.value if hasattr(user.age_category, 'value') else user.age_category,
        find_gender=data.find_gender,
        find_age_category=data.age_category,
        age_from=data.age_from,
        age_to=data.age_to,
        topics=data.topics,
        chat_language=data.chat_language,
>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8
        is_premium=user.is_premium,
        vip_only=data.vip_only,
        blacklist=blacklist,
    )

    if matched:
        # Get room data for partner info
        room = await matching_service.get_room(room_key)
        partner_data = None
        channel = f"chat:{room_key.replace('room:', '')}"

        if room and room.get("partners"):
            for p in room["partners"]:
                if p["id"] != user.id:
                    partner_user = await user_service.get_user_by_id(db, p["id"])
                    if partner_user:
                        rep = await user_service.get_reputation_percent(partner_user)
                        partner_data = {
                            "id": partner_user.id,
                            "nickname": partner_user.nickname,
                            "age": partner_user.age,
                            "gender": partner_user.gender.value if hasattr(partner_user.gender, 'value') else partner_user.gender,
                            "is_premium": partner_user.is_premium,
                            "chosen_emoji": partner_user.chosen_emoji,
                            "likes": partner_user.likes,
                            "dislikes": partner_user.dislikes,
                            "reputation_percent": rep,
                        }

        # Create a chat record in DB
        partner_id = None
        if room and room.get("partners"):
            for p in room["partners"]:
                if p["id"] != user.id:
                    partner_id = p["id"]
                    break

        chat = None
        if partner_id:
<<<<<<< HEAD
            chat = await chat_service.create_chat(db, user.id, partner_id)
=======
            chat = await chat_service.create_chat(db, user.id, partner_id, data.chat_language)
            await matching_service.set_chat_id(room_key, chat.id)

        # The queue channel is only for the match notification.  A persistent
        # chat uses its database id as the Centrifugo channel for both users.
        from app.services.centrifugo import centrifugo_service
        chat_channel = f"chat:{chat.id}" if chat else channel
        chat_token = centrifugo_service.generate_subscription_token(user.id, chat_channel)
>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8

        return {
            "status": "matched",
            "room_key": room_key,
<<<<<<< HEAD
            "channel": channel,
            "token": token,
=======
            "channel": chat_channel,
            "token": chat_token,
>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8
            "chat_id": chat.id if chat else None,
            "partner": partner_data,
        }
    else:
        return {
            "status": "waiting",
            "room_key": room_key,
            "token": token,
            "channel": f"waiting:{user.id}",
        }


<<<<<<< HEAD
=======
@router.get("/room/{room_id}")
async def resolve_matched_room(
    room_id: str,
    tg_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resolve a waiting-room id to the shared persistent chat for the invited user."""
    user = await user_service.get_user_by_tg_id(db, tg_user["id"])
    room = await matching_service.get_room(f"room:{room_id}")
    if not user or not room or room.get("status") != "matched":
        raise HTTPException(status_code=404, detail="Matched room not found")
    if user.id not in [p["id"] for p in room.get("partners", [])]:
        raise HTTPException(status_code=403, detail="You are not in this room")
    chat_id = room.get("chat_id")
    if not chat_id:
        raise HTTPException(status_code=409, detail="Chat is being prepared; retry shortly")
    from app.services.centrifugo import centrifugo_service
    channel = f"chat:{chat_id}"
    return {"chat_id": chat_id, "channel": channel, "token": centrifugo_service.generate_subscription_token(user.id, channel)}


>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8
@router.post("/cancel-search")
async def cancel_search(
    tg_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel an active search."""
    user = await user_service.get_user_by_tg_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    cancelled = await matching_service.cancel_search(user.id)
    return {"cancelled": cancelled}


@router.post("/send")
async def send_message(
    data: SendMessageRequest,
    tg_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message in an active chat.
    Saves to DB for persistence AND publishes to Centrifugo for real-time delivery.
    """
    user = await user_service.get_user_by_tg_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify user is part of this chat
    chat = await chat_service.get_active_chat(db, user.id)
    if not chat or chat.id != data.chat_id:
        raise HTTPException(status_code=403, detail="You are not in this chat")

    msg_type = MessageTypeEnum(data.type)
    # Determine channel name from chat participants
    channel = f"chat:{chat.id}"

    message = await chat_service.send_message(
        db, chat.id, user.id, msg_type, data.content, channel
    )

<<<<<<< HEAD
=======
    game = _game_question(data.content, chat.language)
    if game:
        from app.services.centrifugo import centrifugo_service
        await centrifugo_service.publish(channel, {"event": "game_question", **game})

>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8
    return {
        "id": message.id,
        "chat_id": message.chat_id,
        "type": message.type.value,
        "sent_at": message.created_at.isoformat() if message.created_at else None,
    }


@router.post("/upload-media")
async def upload_media(
    chat_id: int,
    file: UploadFile = File(...),
    tg_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a media file (photo/video/voice) and send it as a message."""
    user = await user_service.get_user_by_tg_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify user is in this chat
    chat = await chat_service.get_active_chat(db, user.id)
    if not chat or chat.id != chat_id:
        raise HTTPException(status_code=403, detail="You are not in this chat")

    # Size check
    contents = await file.read()
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(contents) > max_size:
        raise HTTPException(status_code=413, detail=f"File too large (max {settings.MAX_UPLOAD_SIZE_MB}MB)")

    # NSFW check
    # In production: save to temp, check NSFW, then proceed or reject
    # is_nsfw = await moderation_service.check_media_nsfw(temp_path)
    # if is_nsfw:
    #     raise HTTPException(status_code=400, detail="Content flagged as inappropriate")

    # Save file
    url = await chat_service.save_media(contents, file.filename, file.content_type)

    # Determine message type from content type
    if file.content_type and file.content_type.startswith("image"):
        msg_type = MessageTypeEnum.photo
    elif file.content_type and file.content_type.startswith("video"):
        msg_type = MessageTypeEnum.video
    elif file.content_type and "audio" in file.content_type:
        msg_type = MessageTypeEnum.voice
    else:
        msg_type = MessageTypeEnum.photo  # Default

    channel = f"chat:{chat.id}"
    message = await chat_service.send_message(
        db, chat.id, user.id, msg_type, url, channel
    )

    return {"id": message.id, "url": url, "type": msg_type.value}


@router.post("/typing")
async def typing_indicator(
    data: TypingRequest,
    tg_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a typing indicator to the chat partner."""
    user = await user_service.get_user_by_tg_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
<<<<<<< HEAD
=======
    try:
        chat_id = int(data.channel.removeprefix("chat:"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid chat channel")
    if not await chat_service.get_active_chat(db, user.id) or not await chat_service.get_chat_for_user(db, chat_id, user.id):
        raise HTTPException(status_code=403, detail="You are not in this chat")
>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8
    await chat_service.send_typing_indicator(user.id, data.channel)
    return {"status": "ok"}


@router.post("/end")
async def end_chat(
    chat_id: int,
    tg_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """End a chat (manual)."""
    user = await user_service.get_user_by_tg_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

<<<<<<< HEAD
=======
    active = await chat_service.get_active_chat(db, user.id)
    if not active or active.id != chat_id:
        raise HTTPException(status_code=403, detail="You are not in this chat")
>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8
    chat = await chat_service.end_chat(db, chat_id, reason="manual")
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Notify partner via Centrifugo
    from app.services.centrifugo import centrifugo_service
    channel = f"chat:{chat.id}"
    await centrifugo_service.publish(channel, {
        "event": "chat_ended",
        "reason": "manual",
        "ended_by": user.id,
    })

    return {"status": "ended", "chat_id": chat.id}


@router.post("/rate")
async def rate_chat(
    data: RateRequest,
    tg_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rate a chat partner (like/dislike). Only after chat ends."""
    user = await user_service.get_user_by_tg_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

<<<<<<< HEAD
    await user_service.add_rating(db, data.chat_id, user.id, data.to_user_id, data.value)
=======
    chat = await chat_service.get_chat_for_user(db, data.chat_id, user.id)
    if not chat or chat.ended_at is None:
        raise HTTPException(status_code=403, detail="You can rate only a finished chat you participated in")
    partner_id = chat.user_b_id if chat.user_a_id == user.id else chat.user_a_id
    if data.to_user_id != partner_id:
        raise HTTPException(status_code=400, detail="Rating target must be your chat partner")
    await user_service.add_rating(db, data.chat_id, user.id, partner_id, data.value)
>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8
    return {"status": "rated", "value": data.value}


@router.post("/report")
async def report_user(
    data: ReportRequest,
    tg_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Report a user. This:
    1. Creates a report
    2. Auto-dislikes the reported user
    3. Immediately ends the chat
    4. May trigger auto-ban if threshold reached
    """
    user = await user_service.get_user_by_tg_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

<<<<<<< HEAD
=======
    chat = await chat_service.get_chat_for_user(db, data.chat_id, user.id)
    if not chat:
        raise HTTPException(status_code=403, detail="You are not in this chat")
    partner_id = chat.user_b_id if chat.user_a_id == user.id else chat.user_a_id
    if data.reported_id != partner_id:
        raise HTTPException(status_code=400, detail="Reported user must be your chat partner")

>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8
    category = ReportCategoryEnum(data.category)
    report = await moderation_service.create_report(
        db, data.chat_id, user.id, data.reported_id, category
    )

    # End the chat with reason="report"
    await chat_service.end_chat(db, data.chat_id, reason="report")

    # Notify both users
    from app.services.centrifugo import centrifugo_service
    channel = f"chat:{data.chat_id}"
    await centrifugo_service.publish(channel, {
        "event": "chat_ended",
        "reason": "report",
    })

    return {"status": "reported", "report_id": report.id}


@router.get("/archive")
async def get_archive(
    tg_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get chat archive for the current user."""
    user = await user_service.get_user_by_tg_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    chats = await chat_service.get_user_chats(db, user.id)
    result = []
    for chat in chats:
        partner_id = chat.user_b_id if chat.user_a_id == user.id else chat.user_a_id
        partner = await user_service.get_user_by_id(db, partner_id)
        result.append({
            "chat_id": chat.id,
            "partner": {
                "id": partner.id if partner else None,
                "nickname": partner.nickname if partner else "Deleted",
                "is_premium": partner.is_premium if partner else False,
                "chosen_emoji": partner.chosen_emoji if partner else None,
            },
            "started_at": chat.started_at.isoformat() if chat.started_at else None,
            "ended_at": chat.ended_at.isoformat() if chat.ended_at else None,
            "ended_reason": chat.ended_reason,
            "is_active": chat.ended_at is None,
        })

    return {"archive": result}


@router.get("/messages/{chat_id}")
async def get_messages(
    chat_id: int,
    limit: int = 50,
    offset: int = 0,
    tg_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get messages for a specific chat (for archive viewing)."""
    user = await user_service.get_user_by_tg_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

<<<<<<< HEAD
=======
    if not await chat_service.get_chat_for_user(db, chat_id, user.id):
        raise HTTPException(status_code=403, detail="You are not in this chat")

>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8
    messages = await chat_service.get_chat_messages(db, chat_id, limit, offset)
    return {
        "messages": [
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "type": m.type.value,
                "content": m.content_url_or_text,
                "sent_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ]
    }


@router.get("/online-count")
async def online_count(
    tg_user: dict = Depends(get_current_user),
):
    """Get current online user count."""
    count = await matching_service.get_online_count()
    return {"online": count}


@router.post("/heartbeat")
async def heartbeat(
    tg_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a heartbeat to maintain online status."""
    user = await user_service.get_user_by_tg_id(db, tg_user["id"])
    if user:
        await matching_service.heartbeat(user.id)
    return {"status": "ok"}
