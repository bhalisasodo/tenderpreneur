import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Organisation(Base):
    __tablename__ = "organisations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    type = Column(String(20), nullable=False)  # "contractor" | "supplier"
    legal_name = Column(String(255), nullable=False)
    trading_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    phone = Column(String(50), nullable=True)
    region = Column(String(100), nullable=False, default="Gauteng")
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    users = relationship("User", back_populates="organisation", cascade="all, delete-orphan", lazy="selectin")
    supplier_profile = relationship("SupplierProfile", back_populates="organisation", uselist=False, cascade="all, delete-orphan", lazy="selectin")
    boqs = relationship("BoQ", back_populates="contractor_organisation", cascade="all, delete-orphan", lazy="selectin")


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organisation_id = Column(String(36), ForeignKey("organisations.id"), nullable=False, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="admin")  # "admin", "estimator", "sales"
    password_hash = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    organisation = relationship("Organisation", back_populates="users", lazy="selectin")


class SupplierProfile(Base):
    __tablename__ = "supplier_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organisation_id = Column(String(36), ForeignKey("organisations.id"), nullable=False, unique=True, index=True)
    categories = Column(JSON, nullable=False, default=list)  # list[str] e.g. ["building-materials"]
    service_regions = Column(JSON, nullable=False, default=list)  # list[str] e.g. ["KwaZulu-Natal"]
    compliance_flags = Column(JSON, nullable=False, default=dict)  # dict e.g. {"bbee_level": "1"}
    preferred_contact_method = Column(String(20), nullable=False, default="whatsapp")  # "whatsapp"|"email"|"sms"
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    organisation = relationship("Organisation", back_populates="supplier_profile", lazy="selectin")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    owner_organisation_id = Column(String(36), ForeignKey("organisations.id"), nullable=False, index=True)
    storage_key = Column(String(512), nullable=False)
    original_filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    checksum = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class BoQ(Base):
    __tablename__ = "boqs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    contractor_organisation_id = Column(String(36), ForeignKey("organisations.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    tender_reference = Column(String(100), nullable=True)
    tender_deadline = Column(DateTime(timezone=True), nullable=True)
    region = Column(String(100), nullable=False, default="KwaZulu-Natal")
    source_document_id = Column(String(36), ForeignKey("documents.id"), nullable=True)
    status = Column(String(50), nullable=False, default="draft")  # draft | parsed | in_sourcing | priced | completed
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    contractor_organisation = relationship("Organisation", back_populates="boqs", lazy="selectin")
    source_document = relationship("Document", lazy="selectin")
    line_items = relationship("LineItem", back_populates="boq", cascade="all, delete-orphan", lazy="selectin")


class LineItem(Base):
    __tablename__ = "line_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    boq_id = Column(String(36), ForeignKey("boqs.id"), nullable=False, index=True)
    source_row_reference = Column(String(50), nullable=True)
    description = Column(Text, nullable=False)
    unit = Column(String(20), nullable=False, default="no")  # "m2", "m3", "kg", "no", "sum", "hr"
    quantity = Column(Float, nullable=False, default=1.0)
    category = Column(String(100), nullable=False, default="general-building")
    benchmark_min_minor = Column(Integer, nullable=True)  # in cents
    benchmark_max_minor = Column(Integer, nullable=True)  # in cents
    benchmark_source = Column(String(100), nullable=True)
    benchmark_currency = Column(String(10), nullable=False, default="ZAR")
    final_price_minor = Column(Integer, nullable=True)  # in cents
    pricing_status = Column(String(50), nullable=False, default="unsourced")  # unsourced | awaiting_quotes | quoted | selected | manually_priced
    parsing_confidence = Column(Float, nullable=True)  # 0.0 to 1.0
    review_status = Column(String(50), nullable=False, default="accepted")  # accepted | needs_review | excluded
    exclusion_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    boq = relationship("BoQ", back_populates="line_items", lazy="selectin")
    quote_requests = relationship("QuoteRequest", back_populates="line_item", cascade="all, delete-orphan", lazy="selectin")


class QuoteRequest(Base):
    __tablename__ = "quote_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    line_item_id = Column(String(36), ForeignKey("line_items.id"), nullable=False, index=True)
    requested_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    response_deadline = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), nullable=False, default="open")  # open | closed | cancelled
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    line_item = relationship("LineItem", back_populates="quote_requests", lazy="selectin")
    requested_by_user = relationship("User", lazy="selectin")
    suppliers = relationship("QuoteRequestSupplier", back_populates="quote_request", cascade="all, delete-orphan", lazy="selectin")
    quotes = relationship("Quote", back_populates="quote_request", cascade="all, delete-orphan", lazy="selectin")


class QuoteRequestSupplier(Base):
    __tablename__ = "quote_request_suppliers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    quote_request_id = Column(String(36), ForeignKey("quote_requests.id"), nullable=False, index=True)
    supplier_organisation_id = Column(String(36), ForeignKey("organisations.id"), nullable=False, index=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    viewed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=False, default="sent")  # sent | viewed | submitted | declined

    quote_request = relationship("QuoteRequest", back_populates="suppliers", lazy="selectin")
    supplier_organisation = relationship("Organisation", lazy="selectin")


class Quote(Base):
    __tablename__ = "quotes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    quote_request_id = Column(String(36), ForeignKey("quote_requests.id"), nullable=False, index=True)
    supplier_organisation_id = Column(String(36), ForeignKey("organisations.id"), nullable=False, index=True)
    unit_price_minor = Column(Integer, nullable=False)  # in cents
    total_price_minor = Column(Integer, nullable=False)  # in cents
    currency = Column(String(10), nullable=False, default="ZAR")
    lead_time_days = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    is_selected = Column(Boolean, nullable=False, default=False)
    submitted_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    quote_request = relationship("QuoteRequest", back_populates="quotes", lazy="selectin")
    supplier_organisation = relationship("Organisation", lazy="selectin")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organisation_id = Column(String(36), ForeignKey("organisations.id"), nullable=False, index=True)
    actor_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    entity_type = Column(String(50), nullable=False, index=True)  # boq | line_item | quote_request | quote | export
    entity_id = Column(String(36), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)  # boq.created | line_item.price_overridden | quote.selected ...
    before_json = Column(JSON, nullable=True)
    after_json = Column(JSON, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
