from datetime import datetime, date

from sqlalchemy import (
    Column, Integer, String, Text, Numeric, Boolean, Date,
    DateTime, ForeignKey, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class ApiToken(Base):
    __tablename__ = "api_tokens"

    id = Column(Integer, primary_key=True)
    provider = Column(String(50), nullable=False)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text)
    token_type = Column(String(20), default="Bearer")
    expires_at = Column(DateTime(timezone=True))
    realm_id = Column(String(50))
    extra_data = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True)
    qb_id = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(255))
    email = Column(String(255))
    balance = Column(Numeric(12, 2))
    is_active = Column(Boolean, default=True)
    raw_data = Column(JSONB)
    synced_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    revenues = relationship("Revenue", back_populates="customer")


class ProductService(Base):
    __tablename__ = "products_services"

    id = Column(Integer, primary_key=True)
    qb_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(String(50))
    unit_price = Column(Numeric(12, 2))
    cost = Column(Numeric(12, 2))
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    raw_data = Column(JSONB)
    synced_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    revenues = relationship("Revenue", back_populates="product_service")
    expenses = relationship("Expense", back_populates="product_service")


class Revenue(Base):
    __tablename__ = "revenue"

    id = Column(Integer, primary_key=True)
    qb_id = Column(String(50), unique=True, nullable=False)
    qb_type = Column(String(50))
    customer_id = Column(Integer, ForeignKey("customers.id"))
    product_service_id = Column(Integer, ForeignKey("products_services.id"))
    txn_date = Column(Date, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    quantity = Column(Numeric(10, 2), default=1)
    description = Column(Text)
    raw_data = Column(JSONB)
    synced_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="revenues")
    product_service = relationship("ProductService", back_populates="revenues")


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True)
    qb_id = Column(String(50), unique=True, nullable=False)
    qb_type = Column(String(50))
    vendor_name = Column(String(255))
    account_name = Column(String(255))
    product_service_id = Column(Integer, ForeignKey("products_services.id"))
    txn_date = Column(Date, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    description = Column(Text)
    raw_data = Column(JSONB)
    synced_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    product_service = relationship("ProductService", back_populates="expenses")


class Liability(Base):
    __tablename__ = "liabilities"

    id = Column(Integer, primary_key=True)
    qb_account_id = Column(String(50), nullable=False)
    account_name = Column(String(255))
    account_type = Column(String(50))
    balance = Column(Numeric(12, 2))
    balance_date = Column(Date)
    raw_data = Column(JSONB)
    synced_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("qb_account_id", "balance_date"),
    )


class AnalysisSnapshot(Base):
    __tablename__ = "analysis_snapshots"

    id = Column(Integer, primary_key=True)
    snapshot_date = Column(Date, unique=True, nullable=False)
    total_revenue = Column(Numeric(12, 2))
    total_expenses = Column(Numeric(12, 2))
    net_profit = Column(Numeric(12, 2))
    total_liabilities = Column(Numeric(12, 2))
    product_breakdown = Column(JSONB)
    insights = Column(JSONB)
    forecast = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class OperationalData(Base):
    __tablename__ = "operational_data"

    id = Column(Integer, primary_key=True)
    source = Column(String(50), nullable=False)
    data_type = Column(String(100))
    reference_date = Column(Date)
    amount = Column(Numeric(12, 2))
    quantity = Column(Numeric(10, 2))
    metadata = Column(JSONB)
    synced_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True)
    session_id = Column(UUID(as_uuid=True), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    function_call = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
