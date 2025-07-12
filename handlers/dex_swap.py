from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from fluentogram import TranslatorRunner

from states.swap_form import BridgeForm
from keyboards.keyboards import swap_confirm
from utils.jupiter import get_token_pairs, initiate_swap
from utils.db import log_transaction
from config import get_config, MemeCoinConfig

swap_router = Router()

@swap_router.callback_query(F.data == "swap_all")
async def swap_all(
        query: CallbackQuery, 
        state: FSMContext, 
        i18n: TranslatorRunner
):
    try:
        data = await state.get_data()
        solana_wallet = data["solana_wallet"]
        amount_out = data.get("amount_out", 0)
        await state.update_data(swap_amount=amount_out)
        meme_coin = get_config(MemeCoinConfig, "meme_coin").contract_address
        token_pairs = await get_token_pairs(meme_coin, int(amount_out * 10**6))
        coin_count = int(token_pairs["outAmount"]) / 10**9
        commission = amount_out * 0.02 if amount_out <= 100 else amount_out * 0.01
        await state.update_data(meme_coin=meme_coin, coin_count=coin_count)
        await query.message.edit_text(
            i18n.confirm.swap.message(
                amount=amount_out,
                commission=commission,
                meme_coin=meme_coin,
                solana_wallet=solana_wallet,
                coin_count=coin_count
            ),
            reply_markup=swap_confirm(i18n)
        )
        await state.set_state(BridgeForm.swap_confirm)
    except TelegramBadRequest:
        await query.answer()

@swap_router.callback_query(F.data == "swap_custom")
async def swap_custom(
        query: CallbackQuery, 
        state: FSMContext, 
        i18n: TranslatorRunner
):
    try:
        await state.set_state(BridgeForm.amount)
        await query.message.edit_text(i18n.enter.swap.amount.message())
    except TelegramBadRequest:
        await query.answer()

@swap_router.message(StateFilter(BridgeForm.amount))
async def process_swap_amount(
        message: Message, 
        state: FSMContext, 
        i18n: TranslatorRunner
):
    try:
        amount = float(message.text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        try:
            await message.answer(i18n.invalid.amount.message())
        except TelegramBadRequest:
            pass
        return
    data = await state.get_data()
    solana_wallet = data["solana_wallet"]
    meme_coin = get_config(MemeCoinConfig, "meme_coin").contract_address
    token_pairs = await get_token_pairs(meme_coin, int(amount * 10**6))
    coin_count = int(token_pairs["outAmount"]) / 10**9
    commission = amount * 0.02 if amount <= 100 else amount * 0.01
    await state.update_data(swap_amount=amount, meme_coin=meme_coin, coin_count=coin_count)
    try:
        await message.answer(
            i18n.confirm.swap.message(
                amount=amount,
                commission=commission,
                meme_coin=meme_coin,
                solana_wallet=solana_wallet,
                coin_count=coin_count
            ),
            reply_markup=swap_confirm(i18n)
        )
        await state.set_state(BridgeForm.bridge_confirm)
    except TelegramBadRequest:
        pass

@swap_router.callback_query(
        StateFilter(BridgeForm.bridge_confirm), 
        F.data == "confirm_swap")
async def confirm_swap(
        query: CallbackQuery, 
        state: FSMContext, 
        i18n: TranslatorRunner
):
    try:
        data = await state.get_data()
        user_id = query.from_user.id
        solana_wallet = data["solana_wallet"]
        swap_amount = data["swap_amount"]
        meme_coin = data["meme_coin"]
        coin_count = data["coin_count"]
        commission = swap_amount * 0.02 if swap_amount <= 100 else swap_amount * 0.01
        swap_amount_after_commission = swap_amount - commission
        fee_wallet = get_config(MemeCoinConfig, "meme_coin").fee_wallet
        tx_hash = await initiate_swap(
            amount=swap_amount_after_commission,
            meme_coin=meme_coin,
            solana_wallet=solana_wallet,
            commission=commission,
            fee_wallet=fee_wallet
        )
        await log_transaction(
            user_id=user_id,
            solana_wallet=solana_wallet,
            amount_in=str(swap_amount),
            commission_amount=str(commission),
            operation_type="swap",
            status="swap_completed",
            solana_tx_hash=tx_hash
        )
        await query.message.edit_text(
            i18n.swap.completed.message(coin_count=coin_count, meme_coin="MORI")
        )
        await state.clear()
    except TelegramBadRequest:
        await query.answer()

@swap_router.callback_query(
        StateFilter(BridgeForm.bridge_confirm), 
        F.data == "cancel")
async def cancel_swap(
        query: CallbackQuery, 
        state: FSMContext, 
        i18n: TranslatorRunner
):
    try:
        await query.message.edit_text(i18n.swap.canceled.message())
        await state.clear()
    except TelegramBadRequest:
        await query.answer()

@swap_router.callback_query(F.data == "later")
async def later_swap(
        query: CallbackQuery, 
        state: FSMContext, 
        i18n: TranslatorRunner
):
    try:
        await query.message.edit_text(i18n.swap.later.message())
        await state.clear()
    except TelegramBadRequest:
        await query.answer()
