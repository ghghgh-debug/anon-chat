"""
Payment API routes — Telegram Stars invoices and transaction history.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.session import get_db
from app.services.user import user_service
from app.services.payment import payment_service
from app.core.config import get_settings

router = APIRouter(prefix="/payments", tags=["payments"])
settings = get_settings()


class CreateInvoiceRequest(BaseModel):
    type: str  # premium_week / premium_month / remove_dislike


from app.bot.handlers import bot
from aiogram.types import LabeledPrice

@router.post("/create-invoice")
async def create_invoice(
    data: CreateInvoiceRequest,
    tg_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a payment invoice for Telegram Stars.
    Returns invoice url that the frontend uses to call
    Telegram.WebApp.openInvoice().
    """
    user = await user_service.get_user_by_tg_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate type
    invoice_params = payment_service.get_invoice_params(data.type)
    if not invoice_params:
        raise HTTPException(status_code=400, detail="Invalid invoice type")

    # Remove dislike check
    if data.type == "remove_dislike" and user.dislikes <= 0:
        raise HTTPException(status_code=400, detail="No dislikes to remove")

    # Create pending transaction
    tx = await payment_service.create_transaction(
        db,
        user_id=user.id,
        tx_type=data.type,
        stars_amount=invoice_params["prices"][0]["amount"],
    )

    # Generate Telegram Invoice Link
    prices = [LabeledPrice(label=p["label"], amount=p["amount"]) for p in invoice_params["prices"]]
    try:
        invoice_url = await bot.create_invoice_link(
            title=invoice_params["title"],
            description=invoice_params["description"],
            payload=str(tx.id),  # Use transaction ID as payload!
            provider_token="",  # Empty for Telegram Stars
            currency="XTR",
            prices=prices,
        )
    except Exception as e:
        # If bot fails to create invoice (e.g., bad token)
        raise HTTPException(status_code=500, detail=f"Failed to create invoice link: {str(e)}")

    return {
        "transaction_id": tx.id,
        "invoice_url": invoice_url,
    }


@router.get("/history")
async def transaction_history(
    tg_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's transaction history."""
    user = await user_service.get_user_by_tg_id(db, tg_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    transactions = await payment_service.get_user_transactions(db, user.id)
    return {
        "transactions": [
            {
                "id": tx.id,
                "type": tx.type,
                "stars_amount": tx.stars_amount,
                "status": tx.status,
                "created_at": tx.created_at.isoformat() if tx.created_at else None,
            }
            for tx in transactions
        ]
    }


@router.get("/prices")
async def get_prices(
    tg_user: dict = Depends(get_current_user),
):
    """Get current pricing for all purchasable items."""
    return {
        "prices": [
            {
                "type": "premium_week",
                "stars": settings.PREMIUM_WEEK_PRICE,
                "label": "Premium — 1 неделя",
            },
            {
                "type": "premium_month",
                "stars": settings.PREMIUM_MONTH_PRICE,
                "label": "Premium — 1 месяц",
            },
            {
                "type": "remove_dislike",
                "stars": settings.REMOVE_DISLIKE_PRICE,
                "label": "Снять 1 дизлайк",
            },
        ]
    }
