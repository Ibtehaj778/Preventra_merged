"""
Motor (async MongoDB) client factory.

A single AsyncIOMotorClient is created on first call to get_client() and
reused for the application lifetime. Routers obtain the database handle
via get_db() and issue async queries directly.
"""

from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from core.config import settings

_client: Optional[AsyncIOMotorClient] = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongodb_uri)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return get_client()[settings.mongodb_db_name]

def get_shared_identity_db() -> AsyncIOMotorDatabase:
    return get_client()[settings.shared_identity_db_name]

async def ping() -> None:
    await get_client().admin.command("ping")


def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None
