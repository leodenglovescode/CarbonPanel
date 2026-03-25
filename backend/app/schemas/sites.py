from datetime import datetime
from typing import Literal

from pydantic import BaseModel

SiteType = Literal["nginx", "python", "wordpress", "nodejs"]
ServiceManager = Literal["systemd", "pm2"]
SiteAction = Literal["start", "stop", "restart"]


class SiteCreate(BaseModel):
    name: str
    type: SiteType
    service_name: str
    service_manager: ServiceManager
    config_file_path: str | None = None
    log_paths: list[str] = []
    description: str | None = None


class SiteUpdate(BaseModel):
    name: str | None = None
    type: SiteType | None = None
    service_name: str | None = None
    service_manager: ServiceManager | None = None
    config_file_path: str | None = None
    log_paths: list[str] | None = None
    description: str | None = None


class SiteStatus(BaseModel):
    status: str           # active | inactive | failed | unknown
    uptime: str | None = None
    pid: int | None = None


class SiteResponse(BaseModel):
    id: str
    name: str
    type: str
    service_name: str
    service_manager: str
    config_file_path: str | None
    log_paths: list[str]
    description: str | None
    created_at: datetime
    updated_at: datetime
    status: SiteStatus | None = None

    model_config = {"from_attributes": True}


class SiteActionRequest(BaseModel):
    action: SiteAction


class SiteActionResponse(BaseModel):
    success: bool
    output: str = ""


class ConfigReadResponse(BaseModel):
    content: str
    path: str


class ConfigWriteRequest(BaseModel):
    content: str
