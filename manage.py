from flask_script import Manager
from app import app, db

manager = Manager(app)
# Přidáme příkazy pro migraci
from flask_migrate import MigrateCommand
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()
