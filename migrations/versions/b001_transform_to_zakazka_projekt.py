"""transform_to_zakazka_projekt_hierarchy

Revision ID: b001
Revises: a728dbabe7e4
Create Date: 2026-02-03

Description:
    Transforms the flat User → Project → LogEntry structure into
    hierarchical User → Zakázka → Projekt → LogEntry structure.

    Migration strategy:
    1. Rename 'projects' table to 'zakazky'
    2. Add new columns to zakazky (color, is_active, created_at)
    3. Create new 'projekty' table
    4. For each zakázka, create a default projekt
    5. Update log_entry.project_id to point to new projekty
    6. Update task_templates.project_id to point to new projekty
    7. Update invoice_settings.project_id → zakazka_id
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'b001'
down_revision = 'a728dbabe7e4'
branch_labels = None
depends_on = None


def upgrade():
    # Get connection for data migration
    connection = op.get_bind()

    # Step 0: Drop all foreign key constraints that reference 'projects' table
    # We need to do this before renaming the table
    op.drop_constraint('log_entry_ibfk_1', 'log_entry', type_='foreignkey')
    op.drop_constraint('task_templates_ibfk_1', 'task_templates', type_='foreignkey')
    op.drop_constraint('invoice_settings_ibfk_1', 'invoice_settings', type_='foreignkey')
    op.drop_constraint('invoice_history_ibfk_2', 'invoice_history', type_='foreignkey')

    # Step 1: Rename 'projects' table to 'zakazky'
    op.rename_table('projects', 'zakazky')

    # Step 2: Add new columns to zakazky
    op.add_column('zakazky', sa.Column('color', sa.String(7), nullable=True, server_default='#0d6efd'))
    op.add_column('zakazky', sa.Column('is_active', sa.Boolean(), nullable=True, server_default='1'))
    op.add_column('zakazky', sa.Column('created_at', sa.DateTime(), nullable=True))

    # Set created_at to current timestamp for existing records
    connection.execute(sa.text("UPDATE zakazky SET created_at = NOW() WHERE created_at IS NULL"))

    # Step 3: Create new 'projekty' table
    op.create_table('projekty',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(120), nullable=False),
        sa.Column('zakazka_id', sa.Integer(), nullable=False),
        sa.Column('color', sa.String(7), nullable=True, server_default='#28a745'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['zakazka_id'], ['zakazky.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Step 4: For each zakázka, create a default projekt
    # Get all zakazky
    zakazky = connection.execute(sa.text("SELECT id, name FROM zakazky")).fetchall()

    for zakazka_id, zakazka_name in zakazky:
        # Create default projekt for this zakázka
        connection.execute(
            sa.text("INSERT INTO projekty (name, zakazka_id, color, is_active, created_at) "
                   "VALUES (:name, :zakazka_id, '#28a745', 1, NOW())"),
            {
                'name': f"{zakazka_name} - Všeobecné práce",
                'zakazka_id': zakazka_id
            }
        )

    # Step 5: Create mapping between old project_id and new projekt_id
    # For each old project (now zakázka), find its corresponding default projekt
    old_to_new_mapping = {}
    zakazky = connection.execute(sa.text("SELECT id FROM zakazky")).fetchall()

    for (zakazka_id,) in zakazky:
        # Find the default projekt for this zakázka
        result = connection.execute(
            sa.text("SELECT id FROM projekty WHERE zakazka_id = :zakazka_id LIMIT 1"),
            {'zakazka_id': zakazka_id}
        ).fetchone()
        if result:
            projekt_id = result[0]
            old_to_new_mapping[zakazka_id] = projekt_id

    # Step 6: Update log_entry.project_id to point to new projekty
    for old_id, new_id in old_to_new_mapping.items():
        connection.execute(
            sa.text("UPDATE log_entry SET project_id = :new_id WHERE project_id = :old_id"),
            {'new_id': new_id, 'old_id': old_id}
        )

    # Step 7: Update task_templates.project_id to point to new projekty
    for old_id, new_id in old_to_new_mapping.items():
        connection.execute(
            sa.text("UPDATE task_templates SET project_id = :new_id WHERE project_id = :old_id"),
            {'new_id': new_id, 'old_id': old_id}
        )

    # Step 8: Update invoice_settings: rename project_id to zakazka_id
    # Rename the column (FK was already dropped in Step 0)
    op.alter_column('invoice_settings', 'project_id',
                   new_column_name='zakazka_id',
                   existing_type=sa.Integer(),
                   nullable=False)

    # Re-add foreign key constraint pointing to zakazky
    op.create_foreign_key('invoice_settings_zakazka_fk', 'invoice_settings', 'zakazky',
                         ['zakazka_id'], ['id'])

    # Step 9: Update invoice_history: keep project_id but it now references projekty
    # Create new foreign key pointing to projekty (FK was already dropped in Step 0)
    op.create_foreign_key('invoice_history_projekt_fk', 'invoice_history', 'projekty',
                         ['project_id'], ['id'])

    # Step 10: Create new foreign keys for log_entry and task_templates pointing to projekty
    # (FKs were already dropped in Step 0)
    op.create_foreign_key('log_entry_projekt_fk', 'log_entry', 'projekty',
                         ['project_id'], ['id'])
    op.create_foreign_key('task_templates_projekt_fk', 'task_templates', 'projekty',
                         ['project_id'], ['id'])


def downgrade():
    """Rollback migration"""
    connection = op.get_bind()

    # This is destructive - we'll lose the hierarchical structure
    # but we can restore the original state

    # Step 1: Update log_entry and task_templates to point back to zakazky
    # Get all projekty and their zakazky
    projekty = connection.execute(
        sa.text("SELECT id, zakazka_id FROM projekty")
    ).fetchall()

    projekt_to_zakazka = {projekt_id: zakazka_id for projekt_id, zakazka_id in projekty}

    # Update log_entry
    for projekt_id, zakazka_id in projekt_to_zakazka.items():
        connection.execute(
            sa.text("UPDATE log_entry SET project_id = :zakazka_id WHERE project_id = :projekt_id"),
            {'zakazka_id': zakazka_id, 'projekt_id': projekt_id}
        )

    # Update task_templates
    for projekt_id, zakazka_id in projekt_to_zakazka.items():
        connection.execute(
            sa.text("UPDATE task_templates SET project_id = :zakazka_id WHERE project_id = :projekt_id"),
            {'zakazka_id': zakazka_id, 'projekt_id': projekt_id}
        )

    # Step 2: Drop foreign keys
    op.drop_constraint('log_entry_projekt_fk', 'log_entry', type_='foreignkey')
    op.drop_constraint('task_templates_projekt_fk', 'task_templates', type_='foreignkey')
    op.drop_constraint('invoice_history_projekt_fk', 'invoice_history', type_='foreignkey')
    op.drop_constraint('invoice_settings_zakazka_fk', 'invoice_settings', type_='foreignkey')

    # Step 3: Rename zakazka_id back to project_id in invoice_settings
    op.alter_column('invoice_settings', 'zakazka_id',
                   new_column_name='project_id',
                   existing_type=sa.Integer(),
                   nullable=False)

    # Step 4: Drop projekty table
    op.drop_table('projekty')

    # Step 5: Remove new columns from zakazky
    op.drop_column('zakazky', 'created_at')
    op.drop_column('zakazky', 'is_active')
    op.drop_column('zakazky', 'color')

    # Step 6: Rename zakazky back to projects
    op.rename_table('zakazky', 'projects')

    # Step 7: Re-create original foreign keys
    op.create_foreign_key('log_entry_ibfk_1', 'log_entry', 'projects',
                         ['project_id'], ['id'])
    op.create_foreign_key('task_templates_ibfk_1', 'task_templates', 'projects',
                         ['project_id'], ['id'])
    op.create_foreign_key('invoice_settings_ibfk_1', 'invoice_settings', 'projects',
                         ['project_id'], ['id'])
    op.create_foreign_key('invoice_history_ibfk_2', 'invoice_history', 'projects',
                         ['project_id'], ['id'])
