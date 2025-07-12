from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram_tonconnect import ATCManager
from pytonconnect.exceptions import UserRejectsError
from utils.db import (get_wallet_by_user_id, log_transaction, update_status, 
                     get_pending_bridges, get_config_by_user_id)
from utils.ton import encode_jetton_transfer
from utils.rhino import create_bridge
from states.swap_form import BridgeForm
from keyboards.keyboards import bridge_completed
from fluentogram import TranslatorHub
import time
import asyncio

bridge_router = Router()

@bridge_router.callback_query(F.text == 'bridge')
async def bridge_command(
        callback: CallbackQuery, 
        state: FSMContext, 
        atc_manager: ATCManager, 
        translator_hub: TranslatorHub
):
    i18n = translator_hub.get_translator_by_locale("ru")
    user_id = callback.from_user.id
    wallet = await get_wallet_by_user_id(user_id=user_id)
    if not wallet:
        await callback.message.answer(text=i18n.wallet.connect())
        return
    
    await state.set_state(BridgeForm.amount)
    await callback.message.answer(text=i18n.bridge.amount())

@bridge_router.message(BridgeForm.amount)
async def bridge_amount(
        message: Message, 
        state: FSMContext, 
        atc_manager: ATCManager, 
        translator_hub: TranslatorHub
):
    i18n = translator_hub.get_translator_by_locale("ru")
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0:
            await message.answer(text=i18n.bridge.invalid_amount())
            return
    except ValueError:
        await message.answer(text=i18n.bridge.invalid_amount())
        return
    
    user_id = message.from_user.id
    config = await get_config_by_user_id(user_id=user_id)
    if not config:
        await message.answer(text=i18n.config.error())
        return
    
    await state.update_data(amount=amount)
    await state.set_state(BridgeForm.solana_wallet)
    await message.answer(text=i18n.bridge.solana_wallet())

@bridge_router.message(BridgeForm.solana_wallet)
async def bridge_solana_wallet(
        message: Message, 
        state: FSMContext, 
        atc_manager: ATCManager, 
        translator_hub: TranslatorHub
):
    i18n = translator_hub.get_translator_by_locale("ru")
    solana_wallet = message.text
    user_id = message.from_user.id
    
    config = await get_config_by_user_id(user_id=user_id)
    if not config:
        await message.answer(text=i18n.config.error())
        return
    
    wallet = await get_wallet_by_user_id(user_id=user_id)
    if not wallet:
        await message.answer(text=i18n.wallet.connect())
        return
    
    jetton_wallet = config.get("jetton_wallet")
    state_data = await state.get_data()
    amount = state_data.get("amount")
    destination_address = config.get("bridge_wallet")
    response_address = wallet.get("address")

    bridge_response = await create_bridge(
            amount=amount, 
            solana_wallet=solana_wallet, 
            jetton_wallet=jetton_wallet
            )
    if not bridge_response.get("success"):
        await message.answer(text=i18n.bridge.error())
        return
    
    transaction_id = bridge_response.get("transaction_id")
    jetton_amount = bridge_response.get("jetton_amount")
    
    transaction = {
        'valid_until': int(time.time() + 3600),
        'messages': [
            encode_jetton_transfer(
                destination_address=destination_address,
                jetton_amount=jetton_amount,
                response_address=response_address,
                forward_ton_amount=int(0.01 * 10 ** 9),
                comment=f"Bridge {transaction_id}"
            )
        ]
    }
    
    await log_transaction(
        user_id=user_id,
        solana_wallet=solana_wallet,
        amount_in=str(amount),
        commission_amount="0",
        operation_type="bridge",
        status="pending",
        tx_id=transaction_id
    )
    
    await message.answer(text=i18n.bridge.wait())
    try:
        await asyncio.wait_for(atc_manager.send_transaction(
            transaction=transaction
        ), 300)
        await message.answer(text=i18n.bridge.sent())
    except asyncio.TimeoutError:
        await message.answer(text=i18n.bridge.timeout())
        await update_status(transaction_id=transaction_id, status="failed_bridge")
    except UserRejectsError:
        await message.answer(text=i18n.bridge.rejected())
        await update_status(transaction_id=transaction_id, status="failed_bridge")
    except Exception as e:
        await message.answer(text=i18n.bridge.error())
        await update_status(transaction_id=transaction_id, status="failed_bridge")
        print(f"Error: {e}")
    
    await state.clear()

@bridge_router.callback_query(lambda call: call.data == "check_bridge")
async def check_bridge_callback(
        callback: CallbackQuery, 
        atc_manager: ATCManager, 
        translator_hub: TranslatorHub
):
    i18n = translator_hub.get_translator_by_locale("ru")
    user_id = callback.from_user.id
    pending_bridges = await get_pending_bridges(user_id=user_id)
    if not pending_bridges:
        await callback.message.answer(text=i18n.bridge.no_pending())
        return
    
    for bridge in pending_bridges:
        status_info = await atc_manager.check_transaction(bridge["tx_id"])
        if status_info["status"] == "executed":
            await update_status(
                transaction_id=bridge["id"],
                status="bridge_completed",
                amount_out=status_info["amount_out"],
                solana_tx_hash=status_info["solana_tx_hash"]
            )
            await callback.message.answer(
                text=i18n.bridge.completed.message(
                    amount_out=float(status_info["amount_out"]) / 10**6 if status_info["amount_out"] else "0",
                    solana_wallet=bridge["solana_wallet"]
                ),
                reply_markup=bridge_completed(i18n)
            )
        elif status_info["status"] in ["failed", "stuck"]:
            await update_status(transaction_id=bridge["id"], status="failed_bridge")
            await callback.message.answer(text=i18n.bridge.failed.message())
