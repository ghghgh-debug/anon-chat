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
    FSInputFile,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging
import os

# Import at top (was inside function — bug fix)
from app.db.session import async_session
from app.services.payment import payment_service
from app.services.user import user_service
from app.core.config import get_settings
from app.models.models import Referral, ReferralClaim
from sqlalchemy import select

settings = get_settings()
token = settings.BOT_TOKEN
if not token or ":" not in token:
    token = "12345678:AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQq"
bot = Bot(token=token)
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
    # Determine user language from profile settings
    lang = "ru"  # Default fallback
    if message.from_user and message.from_user.language_code:
        user_lang = message.from_user.language_code.lower()
        if user_lang.startswith("uz"):
            lang = "uz"
        elif user_lang.startswith("en"):
            lang = "en"

    # Check for referral code
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        ref_code = args[1][4:]
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

                # Send referral saved message in the user's language
                if lang == "uz":
                    ref_msg = "👋 Xush kelibsiz! Taklif havolasi saqlandi."
                elif lang == "en":
                    ref_msg = "👋 Welcome! Referral link saved."
                else:
                    ref_msg = "👋 Добро пожаловать! Реферальная ссылка сохранена."

                try:
                    await message.answer(ref_msg)
                except Exception as e:
                    logger.error(f"Error answering referral saved message: {e}")

    # Determine if user is admin
    is_admin = message.from_user.id in settings.ADMIN_IDS

    # 1. First send the welcome GIF
    try:
        gif_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "doc_2026-07-15_23-03-17.mp4")
        if os.path.exists(gif_path):
            await message.answer_animation(
                animation=FSInputFile(gif_path),
                caption="Masco Bot 🚀"
            )
        else:
            logger.warning(f"Welcome GIF not found at path: {gif_path}")
    except Exception as e:
        logger.error(f"Error sending welcome GIF: {e}", exc_info=True)

    # 2. Prepare localized welcome message and keyboard
    if lang == "uz":
        greeting = "👋 Salom, admin!" if is_admin else "👋 Salom!"
        greeting_text = (
            f"{greeting} **Masco Bot**-ga xush kelibsiz!\n\n"
            "🔮 **Masco Bot** — qiziqishlaringiz bo'yicha tasodifiy suhbatdosh toping!\n"
            "• 💬 Matn, rasm, video, ovozli xabarlar\n"
            "• ⭐ Obro' (reputatsiya) tizimi\n"
            "• 👑 Premium imkoniyatlar\n"
            "• 🛡 Moderatsiya va xavfsizlik\n\n"
            "Boshlash uchun pastdagi tugmani bosing!"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🚀 Ochish",
                web_app=WebAppInfo(url=settings.WEBAPP_URL),
            )],
        ])
    elif lang == "en":
        greeting = "👋 Hello, admin!" if is_admin else "👋 Hello!"
        greeting_text = (
            f"{greeting} Welcome to **Masco Bot**!\n\n"
            "🔮 **Masco Bot** — find a random chat partner by interests!\n"
            "• 💬 Text, photo, video, voice notes\n"
            "• ⭐ Reputation system\n"
            "• 👑 Premium features\n"
            "• 🛡 Moderation & safety\n\n"
            "Click the button below to start!"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🚀 Open",
                web_app=WebAppInfo(url=settings.WEBAPP_URL),
            )],
        ])
    else:  # Default to Russian
        greeting = "👋 Привет, админ!" if is_admin else "👋 Привет!"
        greeting_text = (
            f"{greeting} Добро пожаловать в **Masco Bot**!\n\n"
            "🔮 **Masco Bot** — найди случайного собеседника по интересам!\n"
            "• 💬 Текст, фото, видео, голосовые\n"
            "• ⭐ Система репутации\n"
            "• 👑 Premium-возможности\n"
            "• 🛡 Модерация и безопасность\n\n"
            "Нажми кнопку ниже, чтобы начать!"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🚀 Открыть",
                web_app=WebAppInfo(url=settings.WEBAPP_URL),
            )],
        ])

    await message.answer(
        greeting_text,
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Show help message with available commands."""
    help_text = (
        "📚 **Справка по командам / Help / Yordam**\n\n"
        "🇷🇺 **RU:**\n"
        "/start — Открыть Masco Bot\n"
        "/help — Показать эту справку\n"
        "/stats — Ваша статистика\n"
        "/profile — Ваш профиль\n"
        "/premium — Информация о Premium\n\n"
        "🇺🇸 **EN:**\n"
        "/start — Open Masco Bot\n"
        "/help — Show this help info\n"
        "/stats — Your stats\n"
        "/profile — Your profile\n"
        "/premium — Premium info\n\n"
        "🇺🇿 **UZ:**\n"
        "/start — Masco Bot-ni ochish\n"
        "/help — Ushbu ma'lumotni ko'rsatish\n"
        "/stats — Sizning statistikangiz\n"
        "/profile — Sizning profilingiz\n"
        "/premium — Premium ma'lumotlar"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🚀 Открыть / Open / Ochish",
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
                await message.answer(
                    "❌ Сначала откройте приложение и пройдите регистрацию.\n"
                    "❌ First open the app and register.\n"
                    "❌ Birinchi ilovani ochib ro'yxatdan o'ting."
                )
                return
            
            if user.is_banned:
                await message.answer(
                    "🚫 Ваш аккаунт заблокирован.\n"
                    "🚫 Your account is banned.\n"
                    "🚫 Sizning hisobingiz bloklangan."
                )
                return
            
            rep = await user_service.get_reputation_percent(user)
            
            stats_text = (
                f"📊 **Ваша статистика / Your Stats / Sizning statistikangiz**\n\n"
                f"👤 {user.nickname}\n"
                f"🎂 {user.age} ({user.age_category.value})\n"
                f"👍 {user.likes} | 👎 {user.dislikes}\n"
                f"📈 {rep}%\n"
                f"⏱ {user.total_chat_seconds // 60} min\n"
                f"{'👑 Premium' if user.is_premium else '💎 Standard'}"
            )
            
            await message.answer(stats_text, parse_mode="Markdown")
            
    except Exception as e:
        logger.error(f"Error in /stats: {e}")
        await message.answer("❌ Произошла ошибка. / Error occurred. / Xatolik yuz berdi.")


@router.message(Command("profile"))
async def cmd_profile(message: Message):
    """Show user profile with quick actions."""
    try:
        async with async_session() as db:
            user = await user_service.get_user_by_tg_id(db, message.from_user.id)
            
            if not user:
                await message.answer(
                    "❌ Сначала откройте приложение и пройдите регистрацию.\n"
                    "❌ First open the app and register.\n"
                    "❌ Birinchi ilovani ochib ro'yxatdan o'ting."
                )
                return
            
            if user.is_banned:
                await message.answer(
                    "🚫 Ваш аккауйн заблокирован.\n"
                    "🚫 Your account is banned.\n"
                    "🚫 Sizning hisobingiz bloklangan."
                )
                return
            
            profile_text = (
                f"👤 **Профиль / Profile / Profil: {user.nickname}**\n\n"
                f"🎂 {user.age}\n"
                f"🎭 {user.gender.value}\n"
                f"📊 {await user_service.get_reputation_percent(user)}%\n"
                f"{'👑 Premium active' if user.is_premium else '💎 Standard'}\n"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🚀 Открыть / Open / Ochish",
                    web_app=WebAppInfo(url=settings.WEBAPP_URL),
                )],
            ])
            
            await message.answer(profile_text, reply_markup=keyboard, parse_mode="Markdown")
            
    except Exception as e:
        logger.error(f"Error in /profile: {e}")
        await message.answer("❌ Произошла ошибка. / Error occurred. / Xatolik yuz berdi.")


@router.message(Command("premium"))
async def cmd_premium(message: Message):
    """Show Premium information and pricing."""
    premium_text = (
        "👑 **Premium подписка / Premium Subscription / Premium obuna**\n\n"
        "🇷🇺 **RU:**\n"
        "✨ Преимущества:\n"
        "• 🔓 Фильтр по полу (мужской/женский)\n"
        "• 🌟 VIP-комнаты\n"
        "• 🎭 Эксклюзивные эмодзи-бейджи\n"
        "• ⚡ Приоритет в поиске\n\n"
        "💰 Цены (Telegram Stars):\n"
        "• 99 ⭐ — Неделя\n"
        "• 299 ⭐ — Месяц\n"
        "• 25 ⭐ — Убрать дизлайк\n\n"
        "🇺🇸 **EN:**\n"
        "✨ Benefits:\n"
        "• 🔓 Gender filter (male/female)\n"
        "• 🌟 VIP rooms\n"
        "• 🎭 Exclusive emoji badges\n"
        "• ⚡ Search priority\n\n"
        "💰 Prices (Telegram Stars):\n"
        "• 99 ⭐ — Week\n"
        "• 299 ⭐ — Month\n"
        "• 25 ⭐ — Remove dislike\n\n"
        "🇺🇿 **UZ:**\n"
        "✨ Afzalliklari:\n"
        "• 🔓 Jins bo'yicha filtr (erkak/ayol)\n"
        "• 🌟 VIP xonalar\n"
        "• 🎭 Eksklyuziv emoji-nishonlar\n"
        "• ⚡ Qidiruvdagi ustuvorlik\n\n"
        "💰 Narxlar (Telegram Stars):\n"
        "• 99 ⭐ — Hafta\n"
        "• 299 ⭐ — Oy\n"
        "• 25 ⭐ — Dizlikeni olib tashlash\n\n"
        "Откройте приложение для покупки! / Open the app to purchase! / Sotib olish uchun ilovani oching!"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🚀 Открыть / Open / Ochish",
            web_app=WebAppInfo(url=settings.WEBAPP_URL),
        )],
    ])
    
    await message.answer(premium_text, reply_markup=keyboard, parse_mode="Markdown")


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Admin-only command to show admin panel link."""
    if message.from_user.id not in settings.ADMIN_IDS:
        await message.answer("🚫 Эта команда только для администраторов. / This is an admin command.")
        return
    
    admin_text = (
        "🛡️ **Панель администратора / Admin Panel**\n\n"
        "Откройте приложение для доступа к панели. / Open the app for root admin panel access."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🚀 Открыть админку / Open Admin",
            web_app=WebAppInfo(url=settings.WEBAPP_URL),
        )],
    ])
    
    await message.answer(admin_text, reply_markup=keyboard, parse_mode="Markdown")


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
    dp.startup.register(on_startup)
    return dp

async def on_startup(dispatcher: Dispatcher):
    """Bot startup handler."""
    print(f"🤖 Bot started successfully: @{(await bot.get_me()).username}")
