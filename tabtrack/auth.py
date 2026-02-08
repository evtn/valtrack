import hashlib
from datetime import datetime

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import select

from tabtrack import database
from tabtrack.config import MASTER_KEY
from tabtrack.schemas import APIKeySchema, Wildcard

security = HTTPBearer(auto_error=False)


class AccessScopes(BaseModel):
    write: bool = False
    read: bool = False
    history: bool = False
    admin: bool = False

    @staticmethod
    def master():
        return AccessScopes(
            write=True,
            read=True,
            history=True,
            admin=True,
        )


class APIKey(BaseModel):
    key_id: str
    devices: set[str] | Wildcard = Field(default_factory=set)
    sections: set[str] | Wildcard = Field(default_factory=set)
    access: AccessScopes = Field(default_factory=AccessScopes)
    created_at: datetime

    @staticmethod
    def master():
        return APIKey(
            key_id="$master",
            sections="*",
            devices="*",
            created_at=0,
            access=AccessScopes.master(),
        )

    @staticmethod
    def onetime_read(
        device: str,
        section: str,
    ):
        return APIKey(
            key_id=f"$onetime-{id(object())}",
            devices=[device],
            section=[section],
            access=AccessScopes(read=True),
            created_at=datetime.now(),
        )

    def can_access_base(self, device: str, section: str):
        return self.can_access_device(device) and self.can_access_section(section)

    def can_read(self, device: str, section: str):
        return self.access.read and self.can_access_base(device, section)

    def can_write(self, device: str, section: str):
        return self.access.write and self.can_access_base(device, section)

    def can_read_history(self, device: str, section: str):
        return self.access.history and self.can_access_base(device, section)

    def can_access_device(self, device: str):
        if self.devices == "*":
            return True

        return device in self.devices

    def can_access_section(self, section: str):
        if self.sections == "*":
            return True

        return section in self.sections

    def get_device_filter(self) -> set[str] | None:
        """Get allowed devices, or None if all allowed."""
        if self.devices == "*":
            return None

        return self.devices

    def get_section_filter(self) -> set[str] | None:
        """Get allowed sections, or None if all allowed."""
        if self.sections == "*":
            return None

        return self.sections

    def one_device(self, device: str):
        new_devices: set[str] = set()

        if self.can_access_device(device):
            new_devices.add(device)

        new = self.model_copy()
        new.devices = new_devices

        return new

    def one_section(self, section: str):
        new_sections: set[str] = set()

        if self.can_access_section(section):
            new_sections.add(section)

        new = self.model_copy()
        new.sections = new_sections

        return new

    @staticmethod
    def from_db(db_model: APIKeySchema):
        key = APIKey(
            key_id=db_model.key_id,
            devices=db_model.device_set,
            sections=db_model.section_set,
            access=AccessScopes(
                write=db_model.can_write,
                read=db_model.can_read,
                history=db_model.can_read_history,
            ),
            created_at=db_model.created_at,
        )

        return key


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
) -> APIKey:
    """Get scopes from API key"""
    if not credentials:
        raise HTTPException(status_code=401, detail="API key missing")

    api_key = credentials.credentials

    if api_key == MASTER_KEY:
        return APIKey.master()

    key_hash = hash_api_key(api_key)

    if not database.async_session_maker:
        raise HTTPException(status_code=500, detail="Database not initialized")

    async with database.async_session_maker() as session:
        result = await session.execute(
            select(APIKeySchema).where(APIKeySchema.key_hash == key_hash)
        )
        scopes = result.scalar_one_or_none()

    if not scopes:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return APIKey.from_db(scopes)


async def verify_admin_key(api_key: APIKey = Depends(verify_api_key)) -> APIKey:
    if not api_key.access.admin:
        raise HTTPException(403, detail="Invalid key: no 'admin' access")

    return api_key
