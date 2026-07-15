#!/usr/bin/env python3
"""
Standalone bot runner for testing Telegram bot commands.
Run this separately from the API server.
"""

import asyncio
from app.bot.handlers import get_dispatcher, bot

async def main():
    dp = get_dispatcher()
    print("🤖 Starting Telegram bot polling...")
    print("Available commands: /start, /help, /stats, /profile, /premium, /admin")
    print("Press Ctrl+C to stop")
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped")

if __name__ == "__main__":
    asyncio.run(main())
