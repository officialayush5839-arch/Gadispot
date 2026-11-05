"""SQLAlchemy declarative models for double-entry ledger."""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import AccountTypeEnum, EntrySideEnum, JournalStatusEnum


class LedgerAccount(Base):
    __tablename__ = "ledger_accounts"

    account_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    account_name: Mapped[str] = mapped_column(String(128), nullable=False)
    account_type: Mapped[AccountTypeEnum] = mapped_column(
        ENUM(AccountTypeEnum, name="account_type_enum", create_type=False),
        nullable=False,
    )
    normal_balance: Mapped[str] = mapped_column(String(8), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    lines: Mapped[list["JournalLine"]] = relationship("JournalLine", back_populates="account")

    __table_args__ = (
        CheckConstraint(
            "normal_balance IN ('DEBIT', 'CREDIT')",
            name="chk_ledger_accounts_normal_balance",
        ),
    )


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    journal_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, server_default=func.current_date(), nullable=False)
    transaction_reference: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    transaction_type: Mapped[str] = mapped_column(String(32), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    posting_status: Mapped[JournalStatusEnum] = mapped_column(
        ENUM(JournalStatusEnum, name="journal_status_enum", create_type=False),
        default=JournalStatusEnum.DRAFT,
        nullable=False,
    )
    reversal_of_journal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    lines: Mapped[list["JournalLine"]] = relationship(
        "JournalLine", back_populates="journal", cascade="all, delete-orphan"
    )
    reversal_of: Mapped[Optional["JournalEntry"]] = relationship("JournalEntry", remote_side=[id], backref="reversals")


class JournalLine(Base):
    __tablename__ = "journal_lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    journal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    account_code: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("ledger_accounts.account_code"),
        nullable=False,
        index=True,
    )
    entry_side: Mapped[EntrySideEnum] = mapped_column(
        ENUM(EntrySideEnum, name="entry_side_enum", create_type=False),
        nullable=False,
    )
    amount_in_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    journal: Mapped["JournalEntry"] = relationship("JournalEntry", back_populates="lines")
    account: Mapped["LedgerAccount"] = relationship("LedgerAccount", back_populates="lines")

    __table_args__ = (
        UniqueConstraint("journal_id", "line_number", name="uq_journal_line"),
        CheckConstraint("amount_in_paise > 0", name="chk_amount_in_paise_positive"),
    )
