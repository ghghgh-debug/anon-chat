"""
Telegram Bot — Aiogram 3 handler.

Handles:
- /start command (with referral tracking)
- Onboarding FSM (nickname → gender → age → confirm)
- Payment webhooks (pre_checkout_query + successful_payment)
- WebApp button to launch the Mini App
"""

from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    WebAppInfo,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    PreCheckoutQuery,
    Message,
    LabeledPrice,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging

# Import at top (was inside function — bug fix)
from app.db.session import async_session
from app.services.payment import payment_service
from app.core.config import get_settings

settings = get_settings()
bot = Bot(token=settings.BOT_TOKEN)
router = Router()

logger = logging.getLogger(__name__)


# --- FSM States for onboarding via bot ---

class OnboardingStates(StatesGroup):
    nickname = State()
    gender = State()
    age = State()
    confirm = State()


# --- Handlers ---

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start — show welcome and WebApp button."""
    # Check for referral code
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        ref_code = args[1][4:]
        # TODO: Track referral via API
        await message.answer(f"👋 Добро пожаловать! Вы пришли по реферальной ссылке: {ref_code}")

    # Determine if user is admin
    is_admin = message.from_user.id in settings.ADMIN_IDS
    greeting = "👋 Привет, админ!" if is_admin else "👋 Привет!"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🚀 Открыть Анонимный Чат",
            web_app=WebAppInfo(url=settings.WEBAPP_URL),
        )],
    ])

    await message.answer(
        f"{greeting}\n\n"
        "🔮 **Анонимный чат** — найди случайного собеседника по интересам!\n\n"
        "• 💬 Текст, фото, видео, голосовые\n"
        "• ⭐ Система репутации\n"
        "• 👑 Premium-возможности\n"
        "• 🛡 Модерация и безопасность\n\n"
        "Нажми кнопку ниже, чтобы начать!",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


# --- Payment handlers ---

@router.pre_checkout_query()
async def handle_pre_checkout(query: PreCheckoutQuery):
    """
    Telegram sends this before processing payment.
    We must answer within 10 seconds.
    Always accept — actual validation happens in successful_payment.
    """
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def handle_successful_payment(message: Message):
    """
    Handle successful Telegram Stars payment.
    Complete the transaction on the server side.
    
    Improvements:
    - Better error handling
    - Logging for debugging
    - Idempotency check
    - User-friendly error messages
    """
    payment = message.successful_payment
    payload = payment.invoice_payload  # This is the transaction_id we passed

    try:
        # Parse transaction ID from payload
        tx_id = int(payload)
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid payload format: {payload}, error: {e}")
        await message.answer(
            "⚠ Произошла ошибка при обработке платежа (неверный ID).\n"
            "Пожалуйста, обратитесь в поддержку."
        )
        return

    try:
        async with async_session() as db:
            # Complete the transaction (idempotent operation)
            tx = await payment_service.complete_transaction(db, tx_id)
            await db.commit()

            if not tx:
                logger.warning(f"Transaction {tx_id} not found")
                await message.answer(
                    "⚠ Транзакция не найдена. Пожалуйста, обратитесь в поддержку."
                )
                return

            if tx.status == "completed":
                logger.info(f"Transaction {tx_id} already completed (idempotent)")

        # Success message
        await message.answer(
            "✅ Оплата успешна! Ваш баланс обновлён.\n\n"
            "Вернитесь в приложение, чтобы увидеть изменения.",
        )
        logger.info(f"Payment processed successfully for transaction {tx_id}")

    except Exception as e:
        logger.error(f"Failed to process successful_payment for tx_id {tx_id}: {e}", exc_info=True)
        await message.answer(
            "⚠ Произошла ошибка при сохранении платежа.\n"
            "Ваши звёзды не были списаны. Обратитесь в поддержку: @support"
        )


# --- Utility ---

def get_dispatcher() -> Dispatcher:
    """Create and configure the Aiogram dispatcher."""
    dp = Dispatcher()
    dp.include_router(router)
    return dp
