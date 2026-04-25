from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "affiliates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
    )
    op.create_table(
        "offers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
    )
    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(50), nullable=False),
        sa.Column("country", sa.String(2), nullable=False),
        sa.Column("offer_id", sa.Integer(), sa.ForeignKey("offers.id"), nullable=False),
        sa.Column("affiliate_id", sa.Integer(), sa.ForeignKey("affiliates.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    # Seed data базові записи для тестування
    op.bulk_insert(
        sa.table("affiliates", sa.column("id", sa.Integer()), sa.column("name", sa.String())),
        [{"id": 1, "name": "Affiliate One"}, {"id": 2, "name": "Affiliate Two"}],
    )
    op.bulk_insert(
        sa.table("offers", sa.column("id", sa.Integer()), sa.column("name", sa.String())),
        [{"id": 1, "name": "Offer Alpha"}, {"id": 2, "name": "Offer Beta"}],
    )


def downgrade() -> None:
    op.drop_table("leads")
    op.drop_table("offers")
    op.drop_table("affiliates")