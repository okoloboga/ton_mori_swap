import aiohttp
import logging
from config import get_config, RhinoConfig

logger = logging.getLogger(__name__)

async def get_bridge_quote(amount: float, ton_wallet: str, solana_wallet: str) -> dict:
    config = get_config(RhinoConfig, "rhino")
    async with aiohttp.ClientSession() as session:
        headers = {"X-API-Key": config.api_key}
        payload = {
            "fromChain": "TON",
            "toChain": "SOLANA",
            "fromToken": "USDT",
            "toToken": "USDC",
            "fromAmount": str(int(amount * 10**6)),
            "fromAddress": ton_wallet,
            "toAddress": solana_wallet,
            "mode": "receive",
            "gasBoost": {"amountNative": "0.001"}
        }
        logger.debug(f"Sending /bridge/quote request with payload: {payload}")
        async with session.post("https://api.rhino.fi/bridge/quote", json=payload, headers=headers) as resp:
            if resp.status != 200:
                logger.error(f"Failed to get bridge quote: status={resp.status}, response={await resp.text()}")
                raise Exception(f"Failed to get bridge quote: {resp.status}")
            data = await resp.json()
            logger.info(f"Received bridge quote: quoteId={data.get('quoteId')}")
            return data

async def commit_quote(quote_id: str):
    config = get_config(RhinoConfig, "rhino")
    async with aiohttp.ClientSession() as session:
        headers = {"X-API-Key": config.api_key}
        payload = {"quoteId": quote_id}
        logger.debug(f"Sending /bridge/commit request with payload: {payload}")
        async with session.post("https://api.rhino.fi/bridge/commit", json=payload, headers=headers) as resp:
            if resp.status != 200:
                logger.error(f"Failed to commit quote: status={resp.status}, response={await resp.text()}")
                raise Exception(f"Failed to commit quote: {resp.status}")
            logger.info(f"Committed quote: {quote_id}")

async def check_bridge_status(quote_id: str) -> dict:
    config = get_config(RhinoConfig, "rhino")
    async with aiohttp.ClientSession() as session:
        headers = {"X-API-Key": config.api_key}
        logger.debug(f"Checking status for quote_id: {quote_id}")
        async with session.get(f"https://api.rhino.fi/bridge/status/{quote_id}", headers=headers) as resp:
            if resp.status != 200:
                logger.error(f"Failed to check status: status={resp.status}, response={await resp.text()}")
                return {"status": "pending", "amount_out": None, "solana_tx_hash": None}
            data = await resp.json()
            logger.info(f"Bridge status for {quote_id}: {data.get('status')}")
            return {
                "status": data.get("status", "PENDING").lower(),
                "amount_out": data.get("amount"),
                "solana_tx_hash": data.get("withdrawTxHash")
            }
