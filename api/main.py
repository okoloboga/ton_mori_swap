from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis
import logging

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://moriswap.space", "http://localhost:8080"],
    allow_methods=["*"],
    allow_headers=["*"]
)
logger = logging.getLogger(__name__)

@app.get("/get-quote-id")
async def get_quote_id(userId: str):
    r = redis.Redis(host='redis', port=6379, db=0)
    try:
        quote_id = await r.get(f"quote:{userId}")
        logger.info(f"Retrieved quote_id {quote_id} for user {userId}")
        return {"quoteId": quote_id.decode() if quote_id else None}
    finally:
        await r.close()
