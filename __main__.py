import asyncio
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest
from aiogram_tonconnect.middleware import AiogramTonConnectMiddleware
from fluentogram import TranslatorHub
from pytonconnect import TonConnect
from datetime import datetime, timedelta
from backoff import on_exception, expo

from utils.i18n import create_translator_hub
from utils.middleware import TranslatorRunnerMiddleware
from utils.db import db_start, get_pending_bridges, update_status
from utils.rhino import check_bridge_status
from utils.jupiter import jupiter_api
from handlers import start_router, bridge_router, swap_router
from keyboards.keyboards import bridge_completed
from config import get_config, BotConfig, TonConnect


load_dotenv(".env")

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@on_exception(expo, Exception, max_tries=5)
async def check_bridge_status_with_backoff(tx_id):
    return await check_bridge_status(tx_id)

async def poll_pending_bridges(bot: Bot, translator_hub: TranslatorHub):
    while True:
        try:
            pending_bridges = await get_pending_bridges()
            for tx in pending_bridges:
                if tx["created_at"] < datetime.now() - timedelta(hours=1):
                    await update_status(transaction_id=tx["id"], status="failed_bridge")
                    i18n = translator_hub.get_translator_by_locale("ru")
                    try:
                        await bot.send_message(
                            chat_id=tx["user_id"],
                            text=i18n.bridge.failed.message()
                        )
                    except TelegramBadRequest as e:
                        logger.warning(f"Failed to send bridge failed message to {tx['user_id']}: {e}")
                    continue
                status_info = await check_bridge_status_with_backoff(tx["tx_id"])
                if status_info["status"] == "executed":
                    await update_status(
                        transaction_id=tx["id"],
                        status="bridge_completed",
                        amount_out=status_info["amount_out"],
                        solana_tx_hash=status_info["solana_tx_hash"]
                    )
                    i18n = translator_hub.get_translator_by_locale("ru")
                    try:
                        await bot.send_message(
                            chat_id=tx["user_id"],
                            text=i18n.bridge.completed.message(
                                amount_out=float(status_info["amount_out"]) / 10**6 if status_info["amount_out"] else "0",
                                solana_wallet=tx["solana_wallet"]
                            ),
                            reply_markup=bridge_completed(i18n)
                        )
                    except TelegramBadRequest as e:
                        logger.warning(f"Failed to send bridge completed message to {tx['user_id']}: {e}")
                elif status_info["status"] in ["failed", "stuck"]:
                    await update_status(transaction_id=tx["id"], status="failed_bridge")
                    i18n = translator_hub.get_translator_by_locale("ru")
                    try:
                        await bot.send_message(
                            chat_id=tx["user_id"],
                            text=i18n.bridge.failed.message()
                        )
                    except TelegramBadRequest as e:
                        logger.warning(f"Failed to send bridge failed message to {tx['user_id']}: {e}")
        except Exception as e:
            logger.error(f"Polling error: {e}")
        await asyncio.sleep(30)

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s'
    )
    logger.info('Starting Bot')

    bot_config = get_config(BotConfig, "bot")
    tonconnect_config = get_config(TonConnect, "tonconnect")
    pool = await db_start()
    if not pool:
        logger.error("Failed to connect to the database. Exiting.")
        return

    bot = Bot(token=bot_config.token.get_secret_value(),
              default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(pool=pool)
    
    translator_hub = create_translator_hub()
    dp.update.middleware(TranslatorRunnerMiddleware())
    dp.update.middleware(AiogramTonConnectMiddleware(tonconnect=TonConnect(manifest_url=tonconnect_config.manifest)))
    dp.include_routers(start_router, bridge_router, swap_router)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook deleted, ready for polling.")
    except TelegramBadRequest as e:
        logger.error(f"Failed to delete webhook: {e}")

    asyncio.create_task(poll_pending_bridges(bot, translator_hub))

    try:
        await dp.start_polling(bot, _translator_hub=translator_hub)
    finally:
        await jupiter_api.close_session()
        logger.info("Closed API sessions")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
