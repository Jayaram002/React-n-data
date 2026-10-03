"""add dpdp consent framework

Revision ID: c015e874b219
Revises: f9846adf42ca
Create Date: 2026-10-03 14:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c015e874b219'
down_revision: Union[str, None] = 'f9846adf42ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. consent_documents
    op.create_table(
        'consent_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('purpose_code', sa.String(length=64), nullable=False),
        sa.Column('version', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('body_markdown', sa.Text(), nullable=False),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_consent_documents_id'), 'consent_documents', ['id'], unique=False)
    op.create_index(op.f('ix_consent_documents_purpose_code'), 'consent_documents', ['purpose_code'], unique=False)
    op.create_index(op.f('ix_consent_documents_active'), 'consent_documents', ['active'], unique=False)
    op.create_index('ix_consent_docs_purpose_version', 'consent_documents', ['purpose_code', 'version'], unique=True)

    # 2. consent_records
    op.create_table(
        'consent_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('upload_id', sa.Integer(), nullable=True),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('purpose_code', sa.String(length=64), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('document_sha256', sa.String(length=64), nullable=False),
        sa.Column('action', sa.String(length=20), nullable=False, server_default='granted'),
        sa.Column('ip', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['consent_documents.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['upload_id'], ['uploads.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_consent_records_id'), 'consent_records', ['id'], unique=False)
    op.create_index(op.f('ix_consent_records_user_id'), 'consent_records', ['user_id'], unique=False)
    op.create_index(op.f('ix_consent_records_upload_id'), 'consent_records', ['upload_id'], unique=False)
    op.create_index(op.f('ix_consent_records_order_id'), 'consent_records', ['order_id'], unique=False)
    op.create_index(op.f('ix_consent_records_purpose_code'), 'consent_records', ['purpose_code'], unique=False)
    op.create_index('ix_consent_records_user_purpose_date', 'consent_records', ['user_id', 'purpose_code', 'created_at'], unique=False)
    op.create_index('ix_consent_records_upload_purpose', 'consent_records', ['upload_id', 'purpose_code'], unique=False)

    # 3. takedown_requests
    op.create_table(
        'takedown_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('upload_id', sa.Integer(), nullable=False),
        sa.Column('claimant_name', sa.String(length=255), nullable=False),
        sa.Column('claimant_email', sa.String(length=255), nullable=False),
        sa.Column('reason', sa.String(length=100), nullable=False),
        sa.Column('details', sa.Text(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'INVESTIGATING', 'ACTIONED', 'DISMISSED', name='takedownstatus'), nullable=False, server_default='PENDING'),
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['upload_id'], ['uploads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_takedown_requests_id'), 'takedown_requests', ['id'], unique=False)
    op.create_index(op.f('ix_takedown_requests_upload_id'), 'takedown_requests', ['upload_id'], unique=False)

    # 4. deletion_requests
    op.create_table(
        'deletion_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='deletionrequeststatus'), nullable=False, server_default='PENDING'),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_deletion_requests_id'), 'deletion_requests', ['id'], unique=False)
    op.create_index(op.f('ix_deletion_requests_user_id'), 'deletion_requests', ['user_id'], unique=False)

    # 5. users columns
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('terms_accepted_version', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('privacy_accepted_version', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('is_adult_confirmed', sa.Boolean(), nullable=False, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))

    # 6. uploads columns
    with op.batch_alter_table('uploads') as batch_op:
        batch_op.add_column(sa.Column('personal_data_status', sa.String(length=50), nullable=False, server_default='none'))
        batch_op.add_column(sa.Column('lawful_basis', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('lawful_basis_note', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('evidence_storage_key', sa.String(length=255), nullable=True))

    # 7. licenses columns
    with op.batch_alter_table('licenses') as batch_op:
        batch_op.add_column(sa.Column('buyer_agreement_document_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('buyer_agreement_sha256', sa.String(length=64), nullable=True))
        batch_op.create_foreign_key('fk_licenses_buyer_doc', 'consent_documents', ['buyer_agreement_document_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    with op.batch_alter_table('licenses') as batch_op:
        batch_op.drop_constraint('fk_licenses_buyer_doc', type_='foreignkey')
        batch_op.drop_column('buyer_agreement_sha256')
        batch_op.drop_column('buyer_agreement_document_id')

    with op.batch_alter_table('uploads') as batch_op:
        batch_op.drop_column('evidence_storage_key')
        batch_op.drop_column('lawful_basis_note')
        batch_op.drop_column('lawful_basis')
        batch_op.drop_column('personal_data_status')

    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('deleted_at')
        batch_op.drop_column('is_adult_confirmed')
        batch_op.drop_column('privacy_accepted_version')
        batch_op.drop_column('terms_accepted_version')

    op.drop_table('deletion_requests')
    op.drop_table('takedown_requests')
    op.drop_table('consent_records')
    op.drop_table('consent_documents')
