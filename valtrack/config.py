import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@timescaledb:5432/tabtrack"
)

_master_key = os.environ.get("MASTER_KEY")
assert _master_key, "MASTER_KEY environment variable must be set"

MASTER_KEY: str = _master_key
