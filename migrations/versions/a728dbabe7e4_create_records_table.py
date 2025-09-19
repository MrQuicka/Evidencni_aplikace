"""Initial migration - marking existing database state

Revision ID: a728dbabe7e4
Revises: 
Create Date: 2025-09-19 12:47:43.727476

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a728dbabe7e4'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """
    Databáze už existuje, tato migrace jen označuje výchozí stav.
    Tabulky users, projects a log_entry už jsou vytvořeny.
    """
    pass


def downgrade():
    """
    Downgrade by teoreticky smazal všechny tabulky.
    POZOR: Použití downgrade smaže všechna data!
    """
    # Mazání v opačném pořadí kvůli foreign key constraints
    op.drop_table('log_entry')
    op.drop_table('projects') 
    op.drop_table('users')
