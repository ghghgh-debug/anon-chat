"""
Chat service — handles message persistence, chat lifecycle, and media.
"""

import os
import uuid
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from sqlalchemy import select, update, or_, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Chat, Message, User, MessageTypeEnum
from app.services.centrifugo import centrifugo_service
from app.core.config import get_settings


class ChatService:
    def __init__(self):
        self.settings = get_settings()

    async def create_chat(
        self, db: AsyncSession, user_a_id: int, user_b_id: int, language: str = "ru"
    ) -> Chat:
        """Create a new chat record in the database."""
        chat = Chat(
            user_a_id=user_a_id,
            user_b_id=user_b_id,
            language=language,
            started_at=datetime.now(timezone.utc),
        )
        db.add(chat)
        await db.flush()
        return chat

    async def end_chat(
        self,
        db: AsyncSession,
        chat_id: int,
        reason: str = "manual",
    ) -> Optional[Chat]:
        """
        End an active chat.
        Reasons: manual, report, timeout.
        Also calculates and adds chat duration to both users' total_chat_seconds.
        """
        result = await db.execute(select(Chat).where(Chat.id == chat_id))
        chat = result.scalar_one_or_none()
        if not chat:
            return None

        now = datetime.now(timezone.utc)
        chat.ended_at = now
        chat.ended_reason = reason

        # Calculate duration and update both users' stats
        if chat.started_at:
            started = chat.started_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            duration_seconds = int((now - started).total_seconds())
            if duration_seconds > 0:
                await db.execute(
                    update(User)
                    .where(User.id.in_([chat.user_a_id, chat.user_b_id]))
                    .values(total_chat_seconds=User.total_chat_seconds + duration_seconds)
                )

        await db.flush()
        return chat

    async def send_message(
        self,
        db: AsyncSession,
        chat_id: int,
        sender_id: int,
        msg_type: MessageTypeEnum,
        content: str,
        channel: str,
    ) -> Message:
        """
        Save a message to the database AND publish it to Centrifugo in real-time.
        This dual approach ensures persistence + instant delivery.
        """
        message = Message(
            chat_id=chat_id,
            sender_id=sender_id,
            type=msg_type,
            content_url_or_text=content,
        )
        db.add(message)
        await db.flush()

        # Publish to Centrifugo for real-time delivery
        await centrifugo_service.publish(
            channel,
            {
                "event": "message",
                "id": message.id,
                "chat_id": chat_id,
                "sender_id": sender_id,
                "type": msg_type.value,
                "content": content,
                "sent_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        return message

    async def send_typing_indicator(
        self, sender_id: int, channel: str
    ) -> None:
        """Send a 'typing...' indicator to the chat partner via Centrifugo."""
        await centrifugo_service.publish(
            channel,
            {
                "event": "typing",
                "sender_id": sender_id,
            },
        )

    async def get_chat_messages(
        self,
        db: AsyncSession,
        chat_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Message]:
        """Get messages for a chat, ordered by time, with pagination."""
        result = await db.execute(
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.id.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_user_chats(
        self, db: AsyncSession, user_id: int
    ) -> List[Chat]:
        """Get all chats for a user (archive)."""
        result = await db.execute(
            select(Chat)
            .where(or_(Chat.user_a_id == user_id, Chat.user_b_id == user_id))
            .order_by(Chat.started_at.desc())
        )
        return list(result.scalars().all())

    async def get_active_chat(
        self, db: AsyncSession, user_id: int
    ) -> Optional[Chat]:
        """Get a user's currently active (not ended) chat."""
        result = await db.execute(
            select(Chat)
            .where(
                and_(
                    or_(Chat.user_a_id == user_id, Chat.user_b_id == user_id),
                    Chat.ended_at.is_(None),
                )
            )
            .order_by(Chat.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def cleanup_expired_archives(self, db: AsyncSession) -> int:
        """Delete chats older than ARCHIVE_TTL_DAYS. Returns count of deleted records."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.settings.ARCHIVE_TTL_DAYS)
        result = await db.execute(
            select(Chat).where(
                and_(
                    Chat.ended_at.isnot(None),
                    Chat.ended_at < cutoff,
                )
            )
        )
        chats = result.scalars().all()
        count = 0
        for chat in chats:
            # Delete associated messages first
            await db.execute(
                select(Message).where(Message.chat_id == chat.id)
            )
            await db.delete(chat)
            count += 1
        await db.flush()
        return count

    async def save_media(self, file_data: bytes, filename: str, content_type: str) -> str:
        """
        Save an uploaded media file to local storage.
        Returns a URL path to access the file.
        In production, replace this with S3 upload + signed URL generation.
        """
        upload_dir = self.settings.MEDIA_UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)

        ext = os.path.splitext(filename)[1] or ".bin"
        unique_name = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(upload_dir, unique_name)

        with open(file_path, "wb") as f:
            f.write(file_data)

        return f"/media/{unique_name}"


chat_service = ChatService()
