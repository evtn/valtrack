import os

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@timescaledb:5432/tabtrack")
MASTER_KEY = os.environ.get("MASTER_KEY")

if not MASTER_KEY:
    raise ValueError("MASTER_KEY environment variable must be set")
