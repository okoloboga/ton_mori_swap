import asyncpg
import redis.asyncio as redis
import logging
from config import get_config, DbConfig
from pytonconnect.storage import IStorage

logger = logging.getLogger(__name__)

# Глобальный пул соединений
_pool = None

class TcStorage(IStorage):
    def __init__(self, chat_id: int):
        self.chat_id = chat_id

    def _get_key(self, key: str):
        return f"tc:{self.chat_id}:{key}"

    async def set_item(self, key: str, value: str):
        try:
            r = redis.Redis(host='redis', port=6379, db=0)
            try:
                await r.set(self._get_key(key), value)
                logger.debug(f"Set item {key} for chat {self.chat_id}")
            finally:
                await r.close()
        except Exception as e:
            logger.error(f"Failed to set item {key} for chat {self.chat_id}: {e}")
            raise

    async def get_item(self, key: str, default_value: str = None):
        try:
            r = redis.Redis(host='redis', port=6379, db=0)
            try:
                value = await r.get(self._get_key(key))
                return value.decode() if value else default_value
            finally:
                await r.close()
        except Exception as e:
            logger.error(f"Failed to get item {key} for chat {self.chat_id}: {e}")
            raise

    async def remove_item(self, key: str):
        try:
            r = redis.Redis(host='redis', port=6379, db=0)
            try:
                await r.delete(self._get_key(key))
                logger.debug(f"Removed item {key} for chat {self.chat_id}")
            finally:
                await r.close()
        except Exception as e:
            logger.error(f"Failed to remove item {key} for chat {self.chat_id}: {e}")
            raise

async def get_wallet_by_user_id(user_id: int):
    try:
        storage = TcStorage(user_id)
        address = await storage.get_item("wallet_address")
        if address:
            return {"address": address}
        return None
    except Exception as e:
        logger.error(f"Failed to get wallet for user {user_id}: {e}")
        return None

async def get_config_by_user_id(user_id: int):
    try:
        r = redis.Redis(host='redis', port=6379, db=0)
        try:
            jetton_wallet = await r.get(f"config:{user_id}:jetton_wallet")
            bridge_wallet = await r.get(f"config:{user_id}:bridge_wallet")
            if jetton_wallet and bridge_wallet:
                return {
                    "jetton_wallet": jetton_wallet.decode(),
                    "bridge_wallet": bridge_wallet.decode()
                }
            return None
        finally:
            await r.close()
    except Exception as e:
        logger.error(f"Failed to get config for user {user_id}: {e}")
        return None

async def db_start():
    global _pool
    try:
        config = get_config(DbConfig, "db")
        _pool = await asyncpg.create_pool(
            user=config.user,
            password=config.password.get_secret_value(),
            database=config.database,
            host=config.host,
            port=config.port
        )
        async with _pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    solana_wallet TEXT NOT NULL,
                    amount_in TEXT NOT NULL,
                    commission_amount TEXT NOT NULL,
                    operation_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    tx_id TEXT,
                    solana_tx_hash TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_transactions_status_op ON transactions (status, operation_type);
                CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions (user_id);
            ''')
        logger.info("Database initialized successfully")
        return _pool
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return None

async def log_transaction(
        user_id: int, 
        solana_wallet: str, 
        amount_in: str, 
        commission_amount: str, 
        operation_type: str, 
        status: str, 
        solana_tx_hash: str = 'none',
        tx_id: str = 'none'):
    if not _pool:
        logger.error("No database pool available")
        raise Exception("Database not initialized")
    try:
        async with _pool.acquire() as conn:
            await conn.execute(
                '''
                INSERT INTO transactions (user_id, solana_wallet, amount_in, commission_amount, operation_type, status, tx_id, solana_tx_hash)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ''',
                user_id, solana_wallet, amount_in, commission_amount, operation_type, status, tx_id, solana_tx_hash
            )
        logger.info(f"Logged transaction for user {user_id}, operation {operation_type}, status {status}, tx_id {tx_id}")
    except Exception as e:
        logger.error(f"Failed to log transaction: {e}")
        raise

async def get_pending_bridges():
    if not _pool:
        logger.error("No database pool available")
        return []
    try:
        async with _pool.acquire() as conn:
            rows = await conn.fetch("SELECT id, user_id, solana_wallet, tx_id, created_at FROM transactions WHERE status = 'pending' AND operation_type = 'bridge'")
        logger.debug(f"Fetched {len(rows)} pending bridges")
        return [{"id": row["id"], "user_id": row["user_id"], "solana_wallet": row["solana_wallet"], "tx_id": row["tx_id"], "created_at": row["created_at"]} for row in rows]
    except Exception as e:
        logger.error(f"Failed to fetch pending bridges: {e}")
        return []

async def update_status(
        transaction_id: int, 
        status: str, 
        amount_out: str = None, 
        solana_tx_hash: str = None
):
    if not _pool:
        logger.error("No database pool available")
        raise Exception("Database not initialized")
    try:
        async with _pool.acquire() as conn:
            await conn.execute(
                '''
                UPDATE transactions SET status = $1, amount_out = $2, solana_tx_hash = $3
                WHERE id = $4
                ''',
                status, amount_out, solana_tx_hash, transaction_id
            )
        logger.info(f"Updated transaction {transaction_id} to status {status}")
    except Exception as e:
        logger.error(f"Failed to update transaction {transaction_id}: {e}")
        raise

async def set_quote_id(
        user_id: int, 
        quote_id: str
):
    try:
        r = redis.Redis(host='redis', port=6379, db=0)
        try:
            await r.set(f"quote:{user_id}", quote_id)
            logger.info(f"Saved quote_id {quote_id} for user {user_id}")
        finally:
            await r.close()
    except Exception as e:
        logger.error(f"Failed to set quote_id for user {user_id}: {e}")
        raise

async def get_quote_id(user_id: int) -> str:
    try:
        r = redis.Redis(host='redis', port=6379, db=0)
        try:
            quote_id = await r.get(f"quote:{user_id}")
            return quote_id.decode() if quote_id else None
        finally:
            await r.close()
    except Exception as e:
        logger.error(f"Failed to get quote_id for user {user_id}: {e}")
        raise
