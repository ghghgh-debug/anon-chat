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
<<<<<<< HEAD
from app.core.config import get_settings
=======
from app.services.user import user_service
from app.core.config import get_settings
from app.models.models import Referral, ReferralClaim
from sqlalchemy import select
>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8

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
<<<<<<< HEAD
        # TODO: Track referral via API
        await message.answer(f"👋 Добро пожаловать! Вы пришли по реферальной ссылке: {ref_code}")
=======
        async with async_session() as db:
            referral = (await db.execute(select(Referral).where(Referral.code == ref_code))).scalar_one_or_none()
            if referral:
                # Keep the attribution until onboarding creates the user.  A unique
                # tg_id makes repeat /start calls idempotent.
                claim = (await db.execute(
                    select(ReferralClaim).where(ReferralClaim.tg_id == message.from_user.id)
                )).scalar_one_or_none()
                if not claim:
                    db.add(ReferralClaim(tg_id=message.from_user.id, referral_id=referral.id))
                    await db.commit()
                await message.answer("👋 Добро пожаловать! Реферальная ссылка сохранена.")
>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8

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


<<<<<<< HEAD
=======
@router.message(Command("help"))
async def cmd_help(message: Message):
    """Show help message with available commands."""
    help_text = (
        "📚 **Справка по командам**\n\n"
        "/start — Открыть приложение\n"
        "/help — Показать эту справку\n"
        "/stats — Ваша статистика\n"
        "/profile — Ваш профиль\n"
        "/premium — Информация о Premium\n"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🚀 Открыть приложение",
            web_app=WebAppInfo(url=settings.WEBAPP_URL),
        )],
    ])
    
    await message.answer(help_text, reply_markup=keyboard, parse_mode="Markdown")


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Show user statistics."""
    try:
        async with async_session() as db:
            user = await user_service.get_user_by_tg_id(db, message.from_user.id)
            
            if not user:
                await message.answer("❌ Сначала откройте приложение и пройдите регистрацию.")
                return
            
            if user.is_banned:
                await message.answer("🚫 Ваш аккаунт заблокирован.")
                return
            
            rep = await user_service.get_reputation_percent(user)
            
            stats_text = (
                f"📊 **Ваша статистика**\n\n"
                f"👤 Никнейм: {user.nickname}\n"
                f"🎂 Возраст: {user.age} ({user.age_category.value})\n"
                f"👍 Лайки: {user.likes}\n"
                f"👎 Дизлайки: {user.dislikes}\n"
                f"📈 Репутация: {rep}%\n"
                f"⏱ Время в чатах: {user.total_chat_seconds // 60} мин\n"
                f"{'👑 Premium' if user.is_premium else '💎 Стандарт'}"
            )
            
            await message.answer(stats_text, parse_mode="Markdown")
            
    except Exception as e:
        logger.error(f"Error in /stats: {e}")
        await message.answer("❌ Произошла ошибка при загрузке статистики.")


@router.message(Command("profile"))
async def cmd_profile(message: Message):
    """Show user profile with quick actions."""
    try:
        async with async_session() as db:
            user = await user_service.get_user_by_tg_id(db, message.from_user.id)
            
            if not user:
                await message.answer("❌ Сначала откройте приложение и пройдите регистрацию.")
                return
            
            if user.is_banned:
                await message.answer("🚫 Ваш аккаунт заблокирован.")
                return
            
            profile_text = (
                f"👤 **Профиль: {user.nickname}**\n\n"
                f"🎂 Возраст: {user.age}\n"
                f"🎭 Пол: {user.gender.value}\n"
                f"📊 Репутация: {await user_service.get_reputation_percent(user)}%\n"
                f"{'👑 Premium активен' if user.is_premium else '💎 Без Premium'}\n"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🚀 Открыть приложение",
                    web_app=WebAppInfo(url=settings.WEBAPP_URL),
                )],
            ])
            
            await message.answer(profile_text, reply_markup=keyboard, parse_mode="Markdown")
            
    except Exception as e:
        logger.error(f"Error in /profile: {e}")
        await message.answer("❌ Произошла ошибка при загрузке профиля.")


@router.message(Command("premium"))
async def cmd_premium(message: Message):
    """Show Premium information and pricing."""
    premium_text = (
        "👑 **Premium подписка**\n\n"
        "✨ Преимущества:\n"
        "• 🔓 Фильтр по полу (мужской/женский)\n"
        "• 🌟 VIP-комнаты\n"
        "• 🎭 Эксклюзивные эмодзи-бейджи\n"
        "• ⚡ Приоритет в поиске\n\n"
        "💰 Цены (Telegram Stars):\n"
        "• 99 ⭐ — Неделя\n"
        "• 299 ⭐ — Месяц\n"
        "• 25 ⭐ — Убрать дизлайк\n\n"
        "Откройте приложение для покупки!"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🚀 Открыть приложение",
            web_app=WebAppInfo(url=settings.WEBAPP_URL),
        )],
    ])
    
    await message.answer(premium_text, reply_markup=keyboard, parse_mode="Markdown")


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Admin-only command to show admin panel link."""
    if message.from_user.id not in settings.ADMIN_IDS:
        await message.answer("🚫 Эта команда только для администраторов.")
        return
    
    admin_text = (
        "🛡️ **Панель администратора**\n\n"
        "Доступные функции:\n"
        "• 📊 Статистика платформы\n"
        "• 🚨 Жалобы и модерация\n"
        "• 👥 Управление пользователями\n"
        "• 🔗 Реферальные коды\n"
        "• 📜 Логи действий\n\n"
        "Откройте приложение для доступа к админке."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🚀 Открыть админку",
            web_app=WebAppInfo(url=settings.WEBAPP_URL),
        )],
    ])
    
    await message.answer(admin_text, reply_markup=keyboard, parse_mode="Markdown")


>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8
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
<<<<<<< HEAD
    return dp
=======
    dp.startup.register(on_startup)
    return dp

async def on_startup(dispatcher: Dispatcher):
    """Bot startup handler."""
    print(f"🤖 Bot started successfully: @{(await bot.get_me()).username}")
>>>>>>> f49f89ea64883b54d8f9615cc8813e9d72dabfd8
