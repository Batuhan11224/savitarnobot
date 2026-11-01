import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Keep secrets out of source control.
# Set BOT_TOKEN in Railway Variables before starting the service.
BOT_TOKEN = os.getenv("BOT_TOKEN")

dp = Dispatcher()


@dp.message(Command("start"))
async def start_cmd(message: types.Message) -> None:
    await message.answer(
        "Merhaba! Bot çalışıyor.\n"
        "Komutlar için /help yazabilirsin."
    )


@dp.message(Command("help"))
async def help_cmd(message: types.Message) -> None:
    await message.answer(
        "Kullanılabilir komutlar:\n"
        "/start - Botu başlatır\n"
        "/help - Yardım mesajını gösterir"
    )


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN bulunamadı. Railway Variables bölümüne BOT_TOKEN ekleyin."
        )

    bot = Bot(token=BOT_TOKEN)
    try:
        logger.info("Bot başlatılıyor...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
