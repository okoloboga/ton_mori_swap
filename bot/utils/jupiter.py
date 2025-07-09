import aiohttp
import logging
from config import get_config, MemeCoinConfig
from utils.wallet_validator import is_valid_solana_address

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class JupiterAPI:
    def __init__(self):
        self.base_url = "https://quote-api.jup.ag/v6"
        self.session = None
        self.usdc_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC на Solana

    async def start_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
            logger.debug("Initialized aiohttp session for Jupiter API")

    async def close_session(self):
        if self.session:
            await self.session.close()
            self.session = None
            logger.debug("Closed aiohttp session for Jupiter API")

    async def get_token_pairs(self, output_mint: str, amount: int) -> dict:
        await self.start_session()
        if not is_valid_solana_address(output_mint):
            logger.error(f"Invalid output mint address: {output_mint}")
            raise ValueError("Invalid meme coin address")

        url = f"{self.base_url}/quote"
        params = {
            "inputMint": self.usdc_address,
            "outputMint": output_mint,
            "amount": amount,  # Сумма в lamports USDC
            "slippageBps": 50
        }
        logger.debug(f"Sending quote request to {url} with params: {params}")
        try:
            async with self.session.get(url, params=params) as response:
                logger.debug(f"Quote request status: {response.status}")
                response_text = await response.text()
                logger.debug(f"Quote response text: {response_text}")
                if response.status != 200:
                    logger.error(f"Failed to get quote: status={response.status}, response={response_text}")
                    raise Exception(f"Failed to get quote: {response.status}")
                data = await response.json()
                logger.debug(f"Quote response data: {data}")
                if not data.get("outAmount"):
                    logger.error(f"Invalid quote response: missing outAmount in {data}")
                    raise Exception("Invalid quote response: missing outAmount")
                logger.info(f"Successfully received quote for output_mint {output_mint}")
                return data
        except Exception as e:
            logger.error(f"Error getting token pairs for output_mint {output_mint}: {e}")
            raise

    async def initiate_swap(self, amount: float, meme_coin: str, solana_wallet: str, commission: float, fee_wallet: str) -> str:
        await self.start_session()
        if not is_valid_solana_address(meme_coin):
            logger.error(f"Invalid meme coin address: {meme_coin}")
            raise ValueError("Invalid meme coin address")
        if not is_valid_solana_address(solana_wallet):
            logger.error(f"Invalid Solana wallet: {solana_wallet}")
            raise ValueError("Invalid Solana wallet")
        if not is_valid_solana_address(fee_wallet):
            logger.error(f"Invalid fee wallet: {fee_wallet}")
            raise ValueError("Invalid fee wallet")
        if amount < 5:
            logger.error(f"Swap amount too low: {amount} USDC, minimum is 5 USDC")
            raise ValueError("Minimum swap amount is 5 USDC")

        amount_lamports = int(amount * 1_000_000)
        commission_lamports = int(commission * 1_000_000)
        logger.debug(f"Calculated swap: amount={amount} USDC ({amount_lamports} lamports), commission={commission} USDC ({commission_lamports} lamports)")

        url = f"{self.base_url}/quote"
        params = {
            "inputMint": self.usdc_address,
            "outputMint": meme_coin,
            "amount": amount_lamports - commission_lamports,
            "slippageBps": 50
        }
        logger.debug(f"Sending swap quote request to {url} with params: {params}")
        try:
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"Failed to get swap quote: status={response.status}, response={await response.text()}")
                    raise Exception(f"Failed to get swap quote: {response.status}")
                quote = await response.json()
                logger.debug(f"Swap quote response data: {quote}")
        except Exception as e:
            logger.error(f"Error getting swap quote for amount {amount} and meme_coin {meme_coin}: {e}")
            raise

        url = f"{self.base_url}/swap"
        payload = {
            "quoteResponse": quote,
            "userPublicKey": solana_wallet,
            "feeAccount": fee_wallet,
            "feeBps": int(commission * 10000 / amount)
        }
        logger.debug(f"Sending swap request to {url} with payload: {payload}")
        try:
            async with self.session.post(url, json=payload) as response:
                if response.status != 200:
                    logger.error(f"Failed to initiate swap: status={response.status}, response={await response.text()}")
                    raise Exception(f"Failed to initiate swap: {response.status}")
                data = await response.json()
                tx_hash = data.get("swapTransaction")
                if not tx_hash:
                    logger.error(f"Invalid swap response: {data}")
                    raise Exception("No transaction hash received")
                logger.info(f"Swap initiated: tx_hash={tx_hash}, amount={amount}, commission={commission}, fee_wallet={fee_wallet}")
                return tx_hash
        except Exception as e:
            logger.error(f"Error initiating swap for amount {amount} and meme_coin {meme_coin}: {e}")
            raise

jupiter_api = JupiterAPI()

async def get_token_pairs(meme_coin: str, amount: int = 1_000_000) -> dict:
    return await jupiter_api.get_token_pairs(meme_coin, amount)

async def initiate_swap(amount: float, meme_coin: str, solana_wallet: str, commission: float, fee_wallet: str) -> str:
    return await jupiter_api.initiate_swap(amount, meme_coin, solana_wallet, commission, fee_wallet)
