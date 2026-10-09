"""Create the current BoQPro MVP schema.

Revision ID: 0001_initial_schema
Revises:
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organisations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("legal_name", sa.String(255), nullable=False),
        sa.Column("trading_name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("region", sa.String(100), nullable=False, server_default="Gauteng"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_organisations_email", "organisations", ["email"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="admin"),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_organisation_id", "users", ["organisation_id"])

    op.create_table(
        "supplier_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False, unique=True),
        sa.Column("categories", sa.JSON(), nullable=False),
        sa.Column("service_regions", sa.JSON(), nullable=False),
        sa.Column("compliance_flags", sa.JSON(), nullable=False),
        sa.Column("preferred_contact_method", sa.String(20), nullable=False, server_default="whatsapp"),
        sa.Column("approval_status", sa.String(30), nullable=False, server_default="approved"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_supplier_profiles_organisation_id", "supplier_profiles", ["organisation_id"], unique=True)

    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_documents_owner_organisation_id", "documents", ["owner_organisation_id"])

    op.create_table(
        "boqs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("contractor_organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("tender_reference", sa.String(100), nullable=True),
        sa.Column("tender_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("region", sa.String(100), nullable=False, server_default="KwaZulu-Natal"),
        sa.Column("source_document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_boqs_contractor_organisation_id", "boqs", ["contractor_organisation_id"])

    op.create_table(
        "line_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("boq_id", sa.String(36), sa.ForeignKey("boqs.id"), nullable=False),
        sa.Column("source_row_reference", sa.String(50), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False, server_default="no"),
        sa.Column("quantity", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("category", sa.String(100), nullable=False, server_default="general-building"),
        sa.Column("benchmark_min_minor", sa.Integer(), nullable=True),
        sa.Column("benchmark_max_minor", sa.Integer(), nullable=True),
        sa.Column("benchmark_source", sa.String(100), nullable=True),
        sa.Column("benchmark_currency", sa.String(10), nullable=False, server_default="ZAR"),
        sa.Column("final_price_minor", sa.Integer(), nullable=True),
        sa.Column("pricing_status", sa.String(50), nullable=False, server_default="unsourced"),
        sa.Column("parsing_confidence", sa.Float(), nullable=True),
        sa.Column("review_status", sa.String(50), nullable=False, server_default="accepted"),
        sa.Column("exclusion_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_line_items_boq_id", "line_items", ["boq_id"])

    op.create_table(
        "quote_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("line_item_id", sa.String(36), sa.ForeignKey("line_items.id"), nullable=False),
        sa.Column("requested_by_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("response_deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_quote_requests_line_item_id", "quote_requests", ["line_item_id"])

    op.create_table(
        "quote_request_suppliers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("quote_request_id", sa.String(36), sa.ForeignKey("quote_requests.id"), nullable=False),
        sa.Column("supplier_organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="sent"),
    )
    op.create_index("ix_quote_request_suppliers_quote_request_id", "quote_request_suppliers", ["quote_request_id"])
    op.create_index("ix_quote_request_suppliers_supplier_organisation_id", "quote_request_suppliers", ["supplier_organisation_id"])

    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("quote_request_id", sa.String(36), sa.ForeignKey("quote_requests.id"), nullable=False),
        sa.Column("supplier_organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("recipient", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_notification_deliveries_quote_request_id", "notification_deliveries", ["quote_request_id"])
    op.create_index("ix_notification_deliveries_supplier_organisation_id", "notification_deliveries", ["supplier_organisation_id"])

    op.create_table(
        "quotes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("quote_request_id", sa.String(36), sa.ForeignKey("quote_requests.id"), nullable=False),
        sa.Column("supplier_organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("unit_price_minor", sa.Integer(), nullable=False),
        sa.Column("total_price_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="ZAR"),
        sa.Column("lead_time_days", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_selected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_quotes_quote_request_id", "quotes", ["quote_request_id"])
    op.create_index("ix_quotes_supplier_organisation_id", "quotes", ["supplier_organisation_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("actor_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("before_json", sa.JSON(), nullable=True),
        sa.Column("after_json", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_organisation_id", "audit_events", ["organisation_id"])
    op.create_index("ix_audit_events_entity_type", "audit_events", ["entity_type"])
    op.create_index("ix_audit_events_entity_id", "audit_events", ["entity_id"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("quotes")
    op.drop_table("notification_deliveries")
    op.drop_table("quote_request_suppliers")
    op.drop_table("quote_requests")
    op.drop_table("line_items")
    op.drop_table("boqs")
    op.drop_table("documents")
    op.drop_table("supplier_profiles")
    op.drop_table("users")
    op.drop_table("organisations")
