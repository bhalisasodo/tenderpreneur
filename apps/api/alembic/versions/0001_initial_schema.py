"""initial_schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-03 21:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Organisations
    op.create_table(
        'organisations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('contact_name', sa.String(255), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('region', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 2. Users
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organisation_id', sa.String(36), sa.ForeignKey('organisations.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 3. Documents
    op.create_table(
        'documents',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('owner_organisation_id', sa.String(36), sa.ForeignKey('organisations.id'), nullable=False),
        sa.Column('storage_key', sa.String(500), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('checksum', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 4. BoQs
    op.create_table(
        'boqs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('contractor_organisation_id', sa.String(36), sa.ForeignKey('organisations.id'), nullable=False),
        sa.Column('source_document_id', sa.String(36), sa.ForeignKey('documents.id'), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('tender_reference', sa.String(100), nullable=True),
        sa.Column('region', sa.String(100), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 5. Line Items
    op.create_table(
        'line_items',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('boq_id', sa.String(36), sa.ForeignKey('boqs.id'), nullable=False),
        sa.Column('source_row_reference', sa.String(50), nullable=True),
        sa.Column('section_name', sa.String(255), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('unit', sa.String(50), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('benchmark_min_minor', sa.Integer(), nullable=True),
        sa.Column('benchmark_max_minor', sa.Integer(), nullable=True),
        sa.Column('benchmark_source', sa.String(255), nullable=True),
        sa.Column('benchmark_currency', sa.String(10), nullable=False, server_default='ZAR'),
        sa.Column('selected_quote_id', sa.String(36), nullable=True),
        sa.Column('final_price_minor', sa.Integer(), nullable=True),
        sa.Column('pricing_status', sa.String(50), nullable=False, server_default='unsourced'),
        sa.Column('price_override_reason', sa.Text(), nullable=True),
        sa.Column('parsing_confidence', sa.Float(), nullable=True),
        sa.Column('review_status', sa.String(50), nullable=False, server_default='accepted'),
        sa.Column('exclusion_reason', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 6. Supplier Trades
    op.create_table(
        'supplier_trades',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('supplier_organisation_id', sa.String(36), sa.ForeignKey('organisations.id'), nullable=False),
        sa.Column('trade_category', sa.String(100), nullable=False),
        sa.Column('region', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 7. Quote Requests
    op.create_table(
        'quote_requests',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('boq_id', sa.String(36), sa.ForeignKey('boqs.id'), nullable=False),
        sa.Column('contractor_organisation_id', sa.String(36), sa.ForeignKey('organisations.id'), nullable=False),
        sa.Column('line_item_id', sa.String(36), sa.ForeignKey('line_items.id'), nullable=True),
        sa.Column('supplier_organisation_id', sa.String(36), sa.ForeignKey('organisations.id'), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('response_deadline', sa.DateTime(timezone=True), nullable=True),
        sa.Column('broadcast_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 8. Quotes
    op.create_table(
        'quotes',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('quote_request_id', sa.String(36), sa.ForeignKey('quote_requests.id'), nullable=False),
        sa.Column('supplier_organisation_id', sa.String(36), sa.ForeignKey('organisations.id'), nullable=False),
        sa.Column('quote_reference', sa.String(100), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('lead_time_days', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 9. Quote Items
    op.create_table(
        'quote_items',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('quote_id', sa.String(36), sa.ForeignKey('quotes.id'), nullable=False),
        sa.Column('line_item_id', sa.String(36), sa.ForeignKey('line_items.id'), nullable=False),
        sa.Column('unit_price_minor', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(10), nullable=False, server_default='ZAR'),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 10. Audit Events
    op.create_table(
        'audit_events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organisation_id', sa.String(36), nullable=False),
        sa.Column('actor_user_id', sa.String(36), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', sa.String(36), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('before_json', sa.JSON(), nullable=True),
        sa.Column('after_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('audit_events')
    op.drop_table('quote_items')
    op.drop_table('quotes')
    op.drop_table('quote_requests')
    op.drop_table('supplier_trades')
    op.drop_table('line_items')
    op.drop_table('boqs')
    op.drop_table('documents')
    op.drop_table('users')
    op.drop_table('organisations')
