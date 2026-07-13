"""Create a new hashed API key record.

Usage:
    python scripts/create_api_key.py "my key name"

Prints the raw key once. Only the SHA-256 hash is stored in the database.
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import get_session_factory  # noqa: E402
from app.services.api_key_service import APIKeyService  # noqa: E402


async def main(name: str) -> None:
    session_factory = get_session_factory()
    async with session_factory() as db:
        api_key, raw_key = await APIKeyService(db).create(name)

    print(f"Created API key '{api_key.name}' (id={api_key.id})")
    print(f"Raw key (shown once, store it now): {raw_key}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a new EventFlow API key")
    parser.add_argument("name", help="Human-readable name for the key")
    args = parser.parse_args()
    asyncio.run(main(args.name))
