from contextlib import nullcontext
import asyncpg
import redis.asyncio as redis
import logging
from config import get_config, DbConfig

logger = logging.getLogger(__name__)

async def db_start():
    try:
        config = get_config(DbConfig, "db")
        pool = await asyncpg.create_pool(
            user=config.user,
            password=config.password.get_secret_value(),
            database=config.database,
            host=config.host,
            port=config.port
        )
        async with pool.acquire() as conn:
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
                    solana_tx_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        logger.info("Database initialized successfully")
        return pool
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
        solana_tx_hash: str,
        tx_id: str = 'none'):
    pool = await db_start()
    if not pool:
        logger.error("No database pool available")
        raise Exception("Database not initialized")
    try:
        async with pool.acquire() as conn:
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
    finally:
        await pool.close()

async def get_pending_bridges():
    pool = await db_start()
    if not pool:
        logger.error("No database pool available")
        return []
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT id, user_id, solana_wallet, tx_id FROM transactions WHERE status = 'pending' AND operation_type = 'bridge'")
        logger.debug(f"Fetched {len(rows)} pending bridges")
        return [{"id": row["id"], "user_id": row["user_id"], "solana_wallet": row["solana_wallet"], "tx_id": row["tx_id"]} for row in rows]
    except Exception as e:
        logger.error(f"Failed to fetch pending bridges: {e}")
        return []

async def update_status(transaction_id: int, status: str, amount_out: str = None, solana_tx_hash: str = None):
    pool = await db_start()
    if not pool:
        logger.error("No database pool available")
        raise Exception("Database not initialized")
    try:
        async with pool.acquire() as conn:
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
    finally:
        await pool.close()

async def set_quote_id(user_id: int, quote_id: str):
    r = redis.Redis(host='redis', port=6379, db=0)
    try:
        await r.set(f"quote:{user_id}", quote_id)
        logger.info(f"Saved quote_id {quote_id} for user {user_id}")
    finally:
        await r.close()

async def get_quote_id(user_id: int) -> str:
    r = redis.Redis(host='redis', port=6379, db=0)
    try:
        quote_id = await r.get(f"quote:{user_id}")
        return quote_id.decode() if quote_id else None
    finally:
        await r.close()
