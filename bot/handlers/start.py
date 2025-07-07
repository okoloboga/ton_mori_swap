from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from fluentogram import TranslatorRunner

from states.swap_form import SwapForm
from keyboards.keyboards import start_menu

start_router = Router()

@start_router.message(CommandStart())
async def start_command(message: Message, i18n: TranslatorRunner):
    try:
        await message.answer(i18n.start.message(), reply_markup=start_menu(i18n))
    except TelegramBadRequest:
        await message.answer(i18n.start.message())  # Fallback to new message

@start_router.callback_query(F.data == "connect_wallet")
async def connect_wallet_callback(query: CallbackQuery, i18n: TranslatorRunner, state: FSMContext):
    try:
        await state.set_state(SwapForm.solana_wallet)
        await query.message.edit_text(i18n.enter.solana.wallet.message())
    except TelegramBadRequest:
        await query.answer()

@start_router.callback_query(F.data == "help")
async def help_callback(query: CallbackQuery, i18n: TranslatorRunner):
    try:
        await query.message.edit_text(i18n.help.message())
    except TelegramBadRequest:
        await query.answer()
