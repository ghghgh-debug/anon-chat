"""
Payment service — Telegram Stars integration.

Handles invoice creation, webhook processing, and transaction recording.
All payments are processed server-side only (never trust client).
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Transaction, User
from app.services.user import user_service
from app.core.config import get_settings


class PaymentService:
    def __init__(self):
        self.settings = get_settings()

    async def create_transaction(
        self,
        db: AsyncSession,
        user_id: int,
        tx_type: str,
        stars_amount: int,
    ) -> Transaction:
        """Create a pending transaction record."""
        tx = Transaction(
            user_id=user_id,
            type=tx_type,
            stars_amount=stars_amount,
            status="pending",
        )
        db.add(tx)
        await db.flush()
        return tx

    async def complete_transaction(
        self,
        db: AsyncSession,
        tx_id: int,
    ) -> Optional[Transaction]:
        """
        Mark a transaction as completed and apply its effects.
        This is called from the Telegram webhook handler after payment confirmation.
        Idempotent: if already completed, does nothing.
        """
        result = await db.execute(select(Transaction).where(Transaction.id == tx_id))
        tx = result.scalar_one_or_none()
        if not tx or tx.status == "completed":
            return tx  # Idempotent

        tx.status = "completed"

        # Apply effects based on transaction type
        if tx.type == "premium_week":
            await user_service.activate_premium(db, tx.user_id, duration_days=7)
        elif tx.type == "premium_month":
            await user_service.activate_premium(db, tx.user_id, duration_days=30)
        elif tx.type == "remove_dislike":
            await user_service.remove_dislike(db, tx.user_id)

        await db.flush()
        return tx

    async def fail_transaction(
        self, db: AsyncSession, tx_id: int
    ) -> Optional[Transaction]:
        """Mark a transaction as failed."""
        result = await db.execute(select(Transaction).where(Transaction.id == tx_id))
        tx = result.scalar_one_or_none()
        if not tx:
            return None
        tx.status = "failed"
        await db.flush()
        return tx

    async def get_user_transactions(
        self,
        db: AsyncSession,
        user_id: int,
        limit: int = 50,
    ) -> list[Transaction]:
        """Get transaction history for a user."""
        result = await db.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    def get_invoice_params(self, tx_type: str) -> dict:
        """
        Get Telegram sendInvoice parameters for a given transaction type.
        Uses XTR (Telegram Stars) currency.
        """
        invoices = {
            "premium_week": {
                "title": "⭐ Premium — 1 неделя",
                "description": "VIP-комнаты, расширенные фильтры, эмодзи-бейджи и приоритет в поиске на 7 дней.",
                "payload": "premium_week",
                "currency": "XTR",
                "prices": [{"label": "Premium 7 дней", "amount": self.settings.PREMIUM_WEEK_PRICE}],
            },
            "premium_month": {
                "title": "⭐ Premium — 1 месяц",
                "description": "VIP-комнаты, расширенные фильтры, эмодзи-бейджи и приоритет в поиске на 30 дней.",
                "payload": "premium_month",
                "currency": "XTR",
                "prices": [{"label": "Premium 30 дней", "amount": self.settings.PREMIUM_MONTH_PRICE}],
            },
            "remove_dislike": {
                "title": "❌ Снять дизлайк",
                "description": "Убрать один дизлайк с вашего профиля.",
                "payload": "remove_dislike",
                "currency": "XTR",
                "prices": [{"label": "Снять 1 дизлайк", "amount": self.settings.REMOVE_DISLIKE_PRICE}],
            },
        }
        return invoices.get(tx_type)


payment_service = PaymentService()
