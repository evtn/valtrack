from typing import Literal

from pydantic import BaseModel

from .auth import APIKey


class PushRequest(BaseModel):
    device: str
    section: str
    value: float
    forcepush: bool = False


type APIKeyPermission = Literal["read", "write", "history", "admin"]


class APIKeyCreate(BaseModel):
    devices: list[str] = ["*"]  # Default to all devices
    sections: list[str] = ["*"]  # Default to all sections
    permissions: set[APIKeyPermission]
    key_id: str | None = None


class APIKeyResponse(BaseModel):
    api_key: str
    data: APIKey
