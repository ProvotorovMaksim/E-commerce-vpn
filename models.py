from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table, Text
from datetime import datetime

class Base(DeclarativeBase):
    pass

# Связующая таблица Many-to-Many
client_device_association = Table(
    "client_devices",
    Base.metadata,
    Column("client_id", Integer, ForeignKey("clients.client_id"), primary_key=True),
    Column("device_id", Integer, ForeignKey("devices.id"), primary_key=True)
)

class Client(Base):
    __tablename__ = "clients"
    client_id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    # Убираем device_ids, используем relationship
    devices: Mapped[list["Device"]] = relationship(secondary=client_device_association, back_populates="owners")

class Device(Base):
    __tablename__ = "devices"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    config_text: Mapped[str] = mapped_column(Text, nullable=True) # Может быть пустым до генерации
    country_code: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="pending") # pending / active
    owners: Mapped[list["Client"]] = relationship(secondary=client_device_association, back_populates="devices")
