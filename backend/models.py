"""
SQLAlchemy ORM models for Pacfully Cost Intelligence.
Every meaningful action (estimate created/updated, quotation generated, etc.)
is written to the audit_events table so nothing is lost.
"""

import json
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, Text, Boolean,
    DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship

from database import Base


# ── User ─────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id           = Column(Integer, primary_key=True, index=True)
    full_name    = Column(String(200), nullable=False)
    email        = Column(String(200), unique=True, index=True, nullable=False)
    hashed_password = Column(String(500), nullable=False)
    role         = Column(String(30), default="Estimator")  # Administrator | Estimator | Viewer
    is_active    = Column(Boolean, default=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
    last_login   = Column(DateTime, nullable=True)


# ── Helpers ──────────────────────────────────────────────────
def now():
    return datetime.utcnow()


# ── Customer ─────────────────────────────────────────────────
class Customer(Base):
    __tablename__ = "customers"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(200), nullable=False)
    contact     = Column(String(100))
    email       = Column(String(200))
    phone       = Column(String(50))
    address     = Column(Text)
    city        = Column(String(100))
    state       = Column(String(100))
    gst_number  = Column(String(50))
    created_at  = Column(DateTime, default=now)
    updated_at  = Column(DateTime, default=now, onupdate=now)
    is_active   = Column(Boolean, default=True)

    estimates   = relationship("Estimate", back_populates="customer", lazy="dynamic")


# ── Master configuration ─────────────────────────────────────
class MasterConfiguration(Base):
    __tablename__ = "master_configuration"

    id         = Column(Integer, primary_key=True)
    rates      = Column(JSON, nullable=False, default=dict)
    updated_at = Column(DateTime, default=now, onupdate=now)


class FormulaConfiguration(Base):
    __tablename__ = "formula_configuration"

    id         = Column(Integer, primary_key=True)
    formulas   = Column(JSON, nullable=False, default=dict)
    updated_at = Column(DateTime, default=now, onupdate=now)


class SystemSettings(Base):
    __tablename__ = "system_settings"

    id         = Column(Integer, primary_key=True)
    settings   = Column(JSON, nullable=False, default=dict)
    updated_at = Column(DateTime, default=now, onupdate=now)


# ── Estimate ─────────────────────────────────────────────────
class Estimate(Base):
    __tablename__ = "estimates"

    id              = Column(Integer, primary_key=True, index=True)
    estimate_number = Column(String(50), unique=True, index=True)  # EST-00124
    customer_id     = Column(Integer, ForeignKey("customers.id"), nullable=True)
    customer_name   = Column(String(200))          # denormalized for quick display
    job_name        = Column(String(300))
    status          = Column(String(30), default="Draft")  # Draft | Quoted | Finalized
    created_by      = Column(String(100), default="System")
    created_at      = Column(DateTime, default=now)
    updated_at      = Column(DateTime, default=now, onupdate=now)
    finalized_at    = Column(DateTime, nullable=True)

    # ── Input snapshot (JSON) ─────────────────────────────────
    input_snapshot  = Column(JSON)   # full EstimateInput dict stored at finalization

    # ── Summary values (denormalized for dashboard/list queries) ──
    order_quantity          = Column(Integer, default=0)
    total_manufacturing_cost = Column(Float, default=0.0)
    cost_per_box            = Column(Float, default=0.0)
    margin_percent          = Column(Float, default=20.0)
    selling_price_per_box   = Column(Float, default=0.0)
    order_value             = Column(Float, default=0.0)

    # ── Relationships ─────────────────────────────────────────
    customer    = relationship("Customer", back_populates="estimates")
    cost_lines  = relationship("CostLine", back_populates="estimate", cascade="all, delete-orphan")
    quotations  = relationship("Quotation", back_populates="estimate", cascade="all, delete-orphan")
    events      = relationship("AuditEvent", back_populates="estimate", cascade="all, delete-orphan")


# ── CostLine ─────────────────────────────────────────────────
class CostLine(Base):
    __tablename__ = "cost_lines"

    id              = Column(Integer, primary_key=True, index=True)
    estimate_id     = Column(Integer, ForeignKey("estimates.id"))
    module          = Column(String(60))          # Kappa | Wrapper | Printing …
    total_cost      = Column(Float, default=0.0)
    cost_per_box    = Column(Float, default=0.0)
    weightage_pct   = Column(Float, default=0.0)
    trace           = Column(JSON)                # list of {label, value} dicts
    status          = Column(String(30), default="OK")  # OK | CONFIGURATION REQUIRED

    estimate = relationship("Estimate", back_populates="cost_lines")


# ── Quotation ────────────────────────────────────────────────
class Quotation(Base):
    __tablename__ = "quotations"

    id              = Column(Integer, primary_key=True, index=True)
    quotation_number = Column(String(60), unique=True, index=True)  # QUO-2026-09-L14
    estimate_id     = Column(Integer, ForeignKey("estimates.id"))
    doc_type        = Column(String(30), default="Quotation")  # Quotation | Proforma Invoice
    customer_name   = Column(String(200))
    customer_address = Column(Text)
    job_name        = Column(String(300))
    order_quantity  = Column(Integer, default=0)
    unit_price      = Column(Float, default=0.0)  # selling price per box
    subtotal        = Column(Float, default=0.0)
    gst_percent     = Column(Float, default=18.0)
    gst_amount      = Column(Float, default=0.0)
    grand_total     = Column(Float, default=0.0)
    validity_days   = Column(Integer, default=15)
    notes           = Column(Text, default="1. Prices are valid for 15 days.\n2. This is a budgetary quotation.\n3. Final pricing may vary based on final artwork and specifications.")
    pdf_path        = Column(String(500), nullable=True)   # path to generated PDF
    created_at      = Column(DateTime, default=now)
    status          = Column(String(30), default="Draft")  # Draft | Sent | Accepted

    estimate = relationship("Estimate", back_populates="quotations")


# ── AuditEvent ───────────────────────────────────────────────
class AuditEvent(Base):
    __tablename__ = "audit_events"

    id          = Column(Integer, primary_key=True, index=True)
    estimate_id = Column(Integer, ForeignKey("estimates.id"), nullable=True)
    user        = Column(String(100), default="System")
    action      = Column(String(200))      # "Estimate Created", "Rate Override", "Quotation Generated" …
    entity_type = Column(String(60))       # estimate | quotation | customer | config
    entity_id   = Column(String(100))      # EST-00124 / QUO-… etc
    detail      = Column(Text)             # human-readable change description
    old_value   = Column(Text, nullable=True)
    new_value   = Column(Text, nullable=True)
    timestamp   = Column(DateTime, default=now)

    estimate = relationship("Estimate", back_populates="events")
