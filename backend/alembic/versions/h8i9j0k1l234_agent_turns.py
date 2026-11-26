"""Add private admissions-agent request receipts and expiring edit snapshots."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "h8i9j0k1l234"
down_revision = "g7h8i9j0k123"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("agent_turns",
        sa.Column("request_id", sa.Uuid(), primary_key=True),
        sa.Column("conversation_id", sa.Uuid(), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("user_message_id", sa.Uuid()),
        sa.Column("answer_id", sa.Uuid()),
        sa.Column("effect_started", sa.Boolean(), nullable=False),
        sa.Column("snapshot", JSONB()),
        sa.Column("expires_at", sa.DateTime(timezone=True)))
    op.create_index("ix_agent_turns_conversation_id", "agent_turns", ["conversation_id"])
    op.create_index("ix_agent_turns_expires_at", "agent_turns", ["expires_at"])


def downgrade():
    op.drop_table("agent_turns")
