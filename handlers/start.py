from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest
from fluentogram import TranslatorRunner

from keyboards.keyboards import start_menu

start_router = Router()

@start_router.message(CommandStart())
async def start_command(
        message: Message, 
        i18n: TranslatorRunner
):
    try:
        await message.answer(i18n.start.message(), 
                             reply_markup=start_menu(i18n))
    except TelegramBadRequest:
        await message.answer(i18n.start.message())  # Fallback to new message

