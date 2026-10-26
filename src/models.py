"""SQLAlchemy schema for the local, synthetic procurement prototype."""
from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Float, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Supplier(Base):
    __tablename__ = 'suppliers'
    name: Mapped[str] = mapped_column(String, primary_key=True)
    lead_time_days: Mapped[int | None] = mapped_column(Integer)
    contact_email: Mapped[str | None] = mapped_column(String)
    __table_args__ = (CheckConstraint('lead_time_days IS NULL OR lead_time_days >= 1'),)


class Product(Base):
    __tablename__ = 'products'
    sku: Mapped[str] = mapped_column(String, primary_key=True)
    product_name: Mapped[str] = mapped_column(String, nullable=False)
    supplier: Mapped[str] = mapped_column(String, nullable=False)
    on_hand: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    on_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    reserved_qty: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False)
    safety_stock: Mapped[int] = mapped_column(Integer, nullable=False)
    pack_size: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost_vnd: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, server_default='Unclassified')
    unit_of_measure: Mapped[str] = mapped_column(String(20), nullable=False, server_default='unit')
    origin: Mapped[str] = mapped_column(String(120), nullable=False, server_default='')
    quality_notes: Mapped[str] = mapped_column(String(500), nullable=False, server_default='')
    __table_args__ = tuple(CheckConstraint(f'{field} >= {minimum}') for field, minimum in (
        ('on_hand', 0), ('on_order', 0), ('reserved_qty', 0), ('lead_time_days', 1),
        ('safety_stock', 0), ('pack_size', 1), ('unit_cost_vnd', 0))) + (
        CheckConstraint("unit_of_measure IN ('unit','piece','kg','carton','roll')"),
        CheckConstraint('length(category) BETWEEN 1 AND 100'),
        CheckConstraint('length(origin) <= 120'), CheckConstraint('length(quality_notes) <= 500'),
    )


class Inventory(Base):
    __tablename__ = 'inventory'
    sku: Mapped[str] = mapped_column(ForeignKey('products.sku'), primary_key=True)
    on_hand: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    on_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    reserved_qty: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    updated_at: Mapped[str] = mapped_column(String, nullable=False)
    __table_args__ = tuple(CheckConstraint(f'{field} >= 0') for field in ('on_hand', 'on_order', 'reserved_qty'))


class Sale(Base):
    __tablename__ = 'sales'
    sale_date: Mapped[str] = mapped_column(String, primary_key=True)
    sku: Mapped[str] = mapped_column(ForeignKey('products.sku'), primary_key=True)
    units: Mapped[int] = mapped_column(Integer, nullable=False)
    __table_args__ = (CheckConstraint('units >= 0'), Index('ix_sales_sku_date', 'sku', 'sale_date'))


class Proposal(Base):
    __tablename__ = 'proposals'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(ForeignKey('products.sku'), nullable=False)
    avg_daily_demand: Mapped[float] = mapped_column(Float, nullable=False)
    inventory_position: Mapped[int] = mapped_column(Integer, nullable=False)
    reorder_point: Mapped[int] = mapped_column(Integer, nullable=False)
    target_stock: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost_vnd: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    supplier: Mapped[str] = mapped_column(String, nullable=False, server_default='')
    category: Mapped[str] = mapped_column(String, nullable=False, server_default='Unclassified')
    unit_of_measure: Mapped[str] = mapped_column(String, nullable=False, server_default='unit')
    snapshot_json: Mapped[str | None] = mapped_column(Text)
    max_quantity: Mapped[int | None] = mapped_column(Integer)
    max_value_vnd: Mapped[int | None] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, server_default='DRAFT')
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    decided_at: Mapped[str | None] = mapped_column(String)
    decided_by: Mapped[str | None] = mapped_column(String)
    comment: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (CheckConstraint('quantity > 0'),
                      CheckConstraint("status IN ('DRAFT','APPROVED','REJECTED')"),
                      Index('ix_proposals_sku_status', 'sku', 'status'))


class ApprovalHistory(Base):
    __tablename__ = 'approval_history'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    proposal_id: Mapped[int] = mapped_column(ForeignKey('proposals.id'), nullable=False)
    decision: Mapped[str] = mapped_column(String, nullable=False)
    actor: Mapped[str] = mapped_column(String, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    before_json: Mapped[str | None] = mapped_column(Text)
    after_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, nullable=False)


class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    proposal_id: Mapped[int | None] = mapped_column(ForeignKey('proposals.id'))
    action: Mapped[str] = mapped_column(String, nullable=False)
    actor: Mapped[str] = mapped_column(String, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    before_json: Mapped[str | None] = mapped_column(Text)
    after_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, nullable=False)


class InventorySnapshot(Base):
    __tablename__ = 'inventory_snapshots'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_date: Mapped[str] = mapped_column(String, nullable=False)
    sku: Mapped[str] = mapped_column(ForeignKey('products.sku'), nullable=False)
    on_hand: Mapped[int] = mapped_column(Integer, nullable=False)
    on_order: Mapped[int] = mapped_column(Integer, nullable=False)
    reserved_qty: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    source: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    __table_args__ = (UniqueConstraint('snapshot_date', 'sku', 'source'),)


class ExceptionRecord(Base):
    __tablename__ = 'exceptions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    proposal_id: Mapped[int | None] = mapped_column(ForeignKey('proposals.id'))
    sku: Mapped[str | None] = mapped_column(ForeignKey('products.sku'))
    exception_type: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False, server_default='WARNING')
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, server_default='OPEN')
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    resolved_at: Mapped[str | None] = mapped_column(String)
