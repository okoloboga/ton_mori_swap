from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from fluentogram import TranslatorRunner
import aiohttp
import json
from config import get_config, MemeCoinConfig, MiniAppConfig  # Добавлен импорт MiniAppConfig

from states.swap_form import SwapForm
from keyboards.keyboards import bridge_confirm
from utils.rhino import get_bridge_quote, commit_quote
from utils.jupiter import get_token_pairs
from utils.wallet_validator import is_valid_solana_address
from utils.db import log_transaction, set_quote_id
import logging

logger = logging.getLogger(__name__)

bridge_router = Router()

@bridge_router.callback_query(F.data == "bridge")
async def bridge_start(callback: CallbackQuery, state: FSMContext, i18n: TranslatorRunner):
    await callback.message.answer(i18n.enter.amount.message())
    await state.set_state(SwapForm.bridge_amount)
    await callback.answer()

@bridge_router.message(StateFilter(SwapForm.bridge_amount))
async def process_amount(message: Message, state: FSMContext, i18n: TranslatorRunner):
    try:
        usd_amount = float(message.text)
        if usd_amount <= 0:
            await message.answer(i18n.invalid.amount.message())
            return
        await state.update_data(usd_amount=usd_amount)
        await message.answer(i18n.enter.solana.wallet.message())
        await state.set_state(SwapForm.solana_wallet)
    except ValueError:
        await message.answer(i18n.invalid.amount.message())

@bridge_router.message(StateFilter(SwapForm.solana_wallet))
async def process_solana_wallet(message: Message, state: FSMContext, i18n: TranslatorRunner):
    solana_wallet = message.text
    if not is_valid_solana_address(solana_wallet):
        await message.answer(i18n.invalid.solana.wallet.message())
        return

    state_data = await state.get_data()
    usd_amount = state_data["usd_amount"]

    try:
        # Получаем курс USDT/USD с CoinGecko
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=usd") as resp:
                if resp.status != 200:
                    await message.answer(i18n.bridge.failed.message())
                    return
                usdt_price = (await resp.json())["tether"]["usd"]
        amount_usdt = usd_amount / usdt_price
        amount_usdc = int(amount_usdt * 10**6)  # USDC для Jupiter

        # Получаем курс $MORI
        meme_coin = get_config(MemeCoinConfig, "meme_coin").contract_address
        jupiter_quote = await get_token_pairs(meme_coin, amount_usdc)
        coin_count = int(jupiter_quote["outAmount"]) / 10**9  # Предполагаем decimals=9 для $MORI

        # Сохраняем данные
        await state.update_data(
            solana_wallet=solana_wallet,
            amount_usdt=amount_usdt,
            coin_count=coin_count
        )

        # Открываем Mini App
        mini_app_config = get_config(MiniAppConfig, "mini_app")  # Изменено с get_config(None, "mini_app").url
        mini_app_url = mini_app_config.url
        await message.answer(
            i18n.confirm.bridge.message(
                amount=amount_usdt,
                solana_wallet=solana_wallet,
                coin_count=coin_count,
                meme_coin="MORI"
            ),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=i18n.connect.wallet.button(),
                    web_app=WebAppInfo(
                        url=f"{mini_app_url}?amount={amount_usdt}&coin_count={coin_count}&solana_wallet={solana_wallet}&user_id={message.from_user.id}"
                    )
                )],
                [InlineKeyboardButton(text=i18n.cancel.button(), callback_data="cancel")]
            ])
        )
        await state.set_state(SwapForm.bridge_confirm)
    except Exception as e:
        logger.error(f"Failed to process bridge: {e}")
        await message.answer(i18n.bridge.failed.message())
        await state.clear()

@bridge_router.message(F.web_app_data, StateFilter(SwapForm.bridge_confirm))
async def process_web_app_data(message: Message, state: FSMContext, i18n: TranslatorRunner):
    try:
        data = message.web_app_data.data
        web_data = json.loads(data)
        ton_wallet = web_data['ton_wallet']
        user_id = web_data['user_id']
        state_data = await state.get_data()
        solana_wallet = state_data["solana_wallet"]
        amount_usdt = state_data["amount_usdt"]
        coin_count = state_data["coin_count"]

        # Создаем /bridge/quote
        quote = await get_bridge_quote(amount_usdt, ton_wallet, solana_wallet)
        quote_id = quote['quoteId']

        # Логируем транзакцию
        await log_transaction(
            user_id=message.from_user.id,
            solana_wallet=solana_wallet,
            amount_in=str(amount_usdt),
            commission_amount="0",
            operation_type="bridge",
            status="pending",
            tx_id=quote_id
        )

        # Сохраняем quoteId в Redis
        await set_quote_id(user_id, quote_id)

        # Выполняем /bridge/commit
        await commit_quote(quote_id)

        await message.answer(i18n.wait.bridge.message())
    except Exception as e:
        logger.error(f"Failed to process web app data: {e}")
        await message.answer(i18n.bridge.failed.message())
        await state.clear()
