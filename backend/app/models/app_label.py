from app.database import Base
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column


class AppLabel(Base):
    __tablename__ = "app_labels"

    port: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[str] = mapped_column(String, nullable=False)
