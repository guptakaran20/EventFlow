import hashlib
import logging
import secrets
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import APIKey

logger = logging.getLogger(__name__)

API_KEY_PREFIX = "efk_"


def generate_api_key() -> str:
    """Generate a new high-entropy raw API key (shown to the user once)."""
    return f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"


def hash_api_key(raw_key: str) -> str:
    """Hash a raw API key for storage/lookup.

    API keys are high-entropy random tokens rather than user-chosen
    passwords, so a fast cryptographic hash (SHA-256) is sufficient here and
    avoids the latency cost of a deliberately slow password hash.
    """
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


class APIKeyService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def verify(self, raw_key: str) -> bool:
        """Check a raw API key against hashed, active keys in the database.

        Returns False (rather than raising) on lookup failure so callers can
        treat DB-backed and bootstrap key checks uniformly; connectivity
        failures are logged, not swallowed.
        """
        db_key = await self.get_by_raw_key(raw_key)
        if db_key is None:
            return False

        db_key.last_used_at = datetime.now(UTC)
        await self._db.commit()
        return True

    async def get_by_raw_key(self, raw_key: str) -> APIKey | None:
        """Get an API key by its raw string."""
        try:
            key_hash = hash_api_key(raw_key)
            result = await self._db.execute(
                select(APIKey).where(APIKey.key_hash == key_hash, APIKey.is_active.is_(True))
            )
            return result.scalar_one_or_none()
        except Exception:
            logger.warning("API key DB lookup failed", exc_info=True)
            return None

    async def get_or_create_bootstrap_api_key(self, raw_key: str) -> APIKey:
        """Get or create an API key specifically for a bootstrap key.

        This ensures workflows created using the bootstrap key have a valid owner_api_key_id.
        """
        api_key = await self.get_by_raw_key(raw_key)
        if api_key is not None:
            return api_key

        key_hash = hash_api_key(raw_key)
        api_key = APIKey(name="bootstrap-key", key_hash=key_hash, is_active=True)
        self._db.add(api_key)
        await self._db.commit()
        await self._db.refresh(api_key)
        return api_key

    async def create(self, name: str) -> tuple[APIKey, str]:
        """Create a new API key record. Returns the record and the raw key."""
        raw_key = generate_api_key()
        api_key = APIKey(name=name, key_hash=hash_api_key(raw_key), is_active=True)
        self._db.add(api_key)
        await self._db.commit()
        await self._db.refresh(api_key)
        return api_key, raw_key
