"""create stock_movements

Revision ID: a3c1d7e92b40
Revises: 1df934ef4a72
Create Date: 2026-11-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3c1d7e92b40'
down_revision: Union[str, Sequence[str], None] = '1df934ef4a72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('stock_movements',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('product_id', sa.Integer(), nullable=False),
    sa.Column('type', sa.String(length=20), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('reason', sa.String(length=255), nullable=True),
    sa.Column('reference_id', sa.Integer(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('quantity <> 0', name='check_stock_movement_quantity_not_zero'),
    sa.CheckConstraint("type IN ('INITIAL', 'PURCHASE', 'SALE', 'RETURN', 'LOSS', 'ADJUSTMENT')", name='check_stock_movement_type'),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_stock_movements_product_id_products'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_stock_movements'))
    )
    op.create_index(op.f('ix_stock_movements_product_id'), 'stock_movements', ['product_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_stock_movements_product_id'), table_name='stock_movements')
    op.drop_table('stock_movements')
