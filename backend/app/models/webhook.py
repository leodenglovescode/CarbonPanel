import uuid

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.types import EncryptedString


class Webhook(Base):
    __tablename__ = "webhooks"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    label: Mapped[str] = mapped_column(String, nullable=False, default="")
    url: Mapped[str] = mapped_column(String, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Notification channels evolved from the original webhook table. Keeping
    # the table avoids disrupting existing installations and API clients.
    kind: Mapped[str] = mapped_column(String, nullable=False, default="webhook")
    topic: Mapped[str | None] = mapped_column(String, nullable=True)
    token: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    smtp_host: Mapped[str | None] = mapped_column(String, nullable=True)
    smtp_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    smtp_security: Mapped[str | None] = mapped_column(String, nullable=True)
    smtp_username: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    smtp_password: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    email_from: Mapped[str | None] = mapped_column(String, nullable=True)
    email_to: Mapped[str | None] = mapped_column(String, nullable=True)
    # Comma-separated event names: alert.cpu, alert.ram, alert.disk
    events: Mapped[str] = mapped_column(
        String, nullable=False, default="alert.cpu,alert.ram,alert.disk"
    )
