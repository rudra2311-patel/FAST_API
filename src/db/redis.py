import redis.asyncio as aioredis
from src.config import Config

# Token expiry in Redis (1 hour)
JTI_EXPIRY = 3600  

# Redis connection client for token blocklist
token_blocklist = aioredis.StrictRedis(
    host=Config.REDIS_HOST,
    port=Config.REDIS_PORT,
    db=0,
)

# Shared Redis client for general use (weather alerts, caching, etc.)
redis_client = aioredis.StrictRedis(
    host=Config.REDIS_HOST,
    port=Config.REDIS_PORT,
    db=1,  # Use different DB to separate concerns
    decode_responses=True  # Automatically decode responses to strings
)

# Add token to blocklist when user logs out
async def add_jti_to_blocklist(jti: str) -> None:
    await token_blocklist.set(
        name=jti,
        value="revoked",
        ex=JTI_EXPIRY  # expire automatically after 1 hour
    )

# Check if token has already been revoked
async def is_jti_blacklisted(jti: str) -> bool:
    jti_value = await token_blocklist.get(name=jti)
    return jti_value is not None
