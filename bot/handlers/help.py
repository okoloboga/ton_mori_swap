from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest
from fluentogram import TranslatorRunner

help_router = Router()

@help_router.message(Command("help"))
async def help_command(
        message: Message, 
        i18n: TranslatorRunner
):
    try:
        await message.answer(i18n.help.message())
    except TelegramBadRequest:
        pass
