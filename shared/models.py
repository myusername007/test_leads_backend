from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Affiliate(Base):
    __tablename__ = "affiliates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    leads: Mapped[list["Lead"]] = relationship(back_populates="affiliate")


class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    leads: Mapped[list["Lead"]] = relationship(back_populates="offer")


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False) 
    offer_id: Mapped[int] = mapped_column(ForeignKey("offers.id"), nullable=False)
    affiliate_id: Mapped[int] = mapped_column(ForeignKey("affiliates.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    offer: Mapped["Offer"] = relationship(back_populates="leads")
    affiliate: Mapped["Affiliate"] = relationship(back_populates="leads")