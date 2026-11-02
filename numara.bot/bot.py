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

MAIN_MENU = types.ReplyKeyboardMarkup(
    keyboard=[
        [
            types.KeyboardButton(text="💰 Bakiye"),
            types.KeyboardButton(text="👤 Profilim"),
        ],
        [
            types.KeyboardButton(text="📞 Destek"),
            types.KeyboardButton(text="ℹ️ Yardım"),
        ],
    ],
    resize_keyboard=True,
    input_field_placeholder="Bir seçenek seçin...",
)


@dp.message(Command("start"))
async def start_cmd(message: types.Message) -> None:
    await message.answer(
        "Merhaba! Bot çalışıyor.\n"
        "Aşağıdaki menüden bir seçenek seçebilirsin.",
        reply_markup=MAIN_MENU,
    )


@dp.message(Command("help"))
@dp.message(lambda message: message.text == "ℹ️ Yardım")
async def help_cmd(message: types.Message) -> None:
    await message.answer(
        "Kullanılabilir seçenekler:\n"
        "💰 Bakiye - Bakiye özelliği henüz bağlanmadı.\n"
        "👤 Profilim - Profil özelliği henüz bağlanmadı.\n"
        "📞 Destek - Destek özelliği henüz bağlanmadı.\n"
        "/start - Ana menüyü açar"
    )


@dp.message(lambda message: message.text == "💰 Bakiye")
async def balance_cmd(message: types.Message) -> None:
    await message.answer("Bakiye görüntüleme henüz etkinleştirilmedi.")


@dp.message(lambda message: message.text == "👤 Profilim")
async def profile_cmd(message: types.Message) -> None:
    username = f"@{message.from_user.username}" if message.from_user.username else "Belirtilmemiş"
    await message.answer(
        f"Telegram ID: {message.from_user.id}\n"
        f"Kullanıcı adı: {username}"
    )


@dp.message(lambda message: message.text == "📞 Destek")
async def support_cmd(message: types.Message) -> None:
    await message.answer("Destek özelliği henüz yapılandırılmadı. Lütfen daha sonra tekrar deneyin.")


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
