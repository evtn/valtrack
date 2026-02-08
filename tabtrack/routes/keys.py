import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from tabtrack.auth import (
    APIKey,
    hash_api_key,
    verify_admin_key,
    verify_api_key,
)
from tabtrack.database import get_db
from tabtrack.models import APIKeyCreate, APIKeyResponse
from tabtrack.schemas import APIKeySchema, Permissions

keys_router = APIRouter(prefix="/keys")
admin_router = APIRouter(prefix="/admin")


@admin_router.post("/key")
async def create_api_key(
    data: APIKeyCreate,
    session: AsyncSession = Depends(get_db),
    admin_key: APIKey = Depends(verify_admin_key),
) -> APIKeyResponse:
    api_key = secrets.token_hex(20)
    key_hash = hash_api_key(api_key)
    key_id = data.key_id or secrets.token_hex(8)
    created_at = int(datetime.now(timezone.utc).timestamp())

    if key_id.startswith("$"):
        raise HTTPException(400, detail="Invalid key id, cannot start with '$'")

    can_read = "read" in data.permissions
    can_write = "write" in data.permissions
    can_get_history = "history" in data.permissions
    can_manage: bool = "admin" in data.permissions

    if can_manage and admin_key.key_id != "$master":
        raise HTTPException(403, detail="only the root admin can create other admins")

    devices = set(data.devices)

    if "*" in devices:
        devices = {"*"}

    sections = set(data.sections)

    if "*" in sections:
        sections = {"*"}

    api_key_record = APIKeySchema(
        key_id=key_id,
        key_hash=key_hash,
        devices=list(devices),
        sections=list(sections),
        permissions=(Permissions.READ * can_read)
        | (Permissions.WRITE * can_write)
        | (Permissions.HISTORY * can_get_history)
        | (Permissions.ADMIN * can_manage),
        created_at=created_at,
    )

    key_data = APIKey.from_db(api_key_record)

    session.add(api_key_record)

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Key ID already exists")

    return APIKeyResponse(
        api_key=api_key,
        data=key_data,
    )


@keys_router.get("/")
async def get_current_key(
    key: APIKey = Depends(verify_api_key),
) -> APIKey:
    return key


@admin_router.get("/keys")
async def list_api_keys(
    session: AsyncSession = Depends(get_db),
    _: APIKey = Depends(verify_admin_key),
) -> list[APIKey]:
    result = await session.execute(
        select(APIKeySchema).order_by(APIKeySchema.created_at.desc())
    )
    key_schemas = result.scalars().all()

    keys = [APIKey.from_db(key) for key in key_schemas]

    keys.append(APIKey.master())

    return keys


async def key_exists(key_id: str, session: AsyncSession):
    result = await session.execute(
        select(APIKeySchema).where(APIKeySchema.key_id == key_id)
    )

    existing = result.scalar_one_or_none()

    if not existing:
        return None

    return APIKey.from_db(existing)


async def revoke(key_id: str, session: AsyncSession, admin_key: APIKey | None = None):
    existing = await key_exists(key_id, session)

    if not existing:
        raise HTTPException(status_code=404, detail="Key not found")

    if admin_key:
        if existing.access.admin and admin_key.key_id != "master":
            raise HTTPException(
                403,
                detail="only the root admin can revoke other admins",
            )

    await session.execute(delete(APIKeySchema).where(APIKeySchema.key_id == key_id))
    await session.commit()

    return existing


@keys_router.delete("/")
async def revoke_current_key(
    key: APIKey = Depends(verify_api_key),
    session: AsyncSession = Depends(get_db),
) -> APIKey:
    if key.key_id == "$master":
        raise HTTPException(400, detail="Cannot revoke root key")

    return await revoke(key.key_id, session)


@admin_router.delete("/key")
async def revoke_api_key(
    key_id: str,
    admin_key: APIKey = Depends(verify_admin_key),
    session: AsyncSession = Depends(get_db),
) -> APIKey:
    if key_id == "$master":
        raise HTTPException(400, detail="Cannot revoke root key")

    return await revoke(key_id, session, admin_key=admin_key)
