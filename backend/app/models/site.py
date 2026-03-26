import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )  # nginx|python|wordpress|nodejs
    service_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )  # systemd unit or pm2 app name
    service_manager: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )  # systemd|pm2
    config_file_path: Mapped[str | None] = mapped_column(String, nullable=True)
    log_paths: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )  # JSON array string
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )
