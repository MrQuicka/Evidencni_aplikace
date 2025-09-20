from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'  # Explicitní název tabulky
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    # Vztah na projekty, které tento uživatel vlastní
    projects = db.relationship('Project', backref='owner', lazy=True)

class Project(db.Model):
    __tablename__ = 'projects'  # Explicitní název tabulky
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    # Přidáme sloupec user_id, který odkazuje na vlastníka projektu (User)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

class LogEntry(db.Model):
    __tablename__ = 'log_entry'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    pause_start = db.Column(db.DateTime, nullable=True)
    pause_end = db.Column(db.DateTime, nullable=True)
    note = db.Column(db.Text, nullable=True)

    project = db.relationship('Project', backref=db.backref('logs', lazy=True))
    user = db.relationship('User', backref=db.backref('logs', lazy=True))

class Record(db.Model):
    __tablename__ = "records"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    def __repr__(self) -> str:
        return f"<Record id={self.id} title={self.title!r}>"

class TaskTemplate(db.Model):
    __tablename__ = 'task_templates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # Název šablony
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    duration_minutes = db.Column(db.Integer, default=60)  # Výchozí délka
    note = db.Column(db.Text, nullable=True)
    color = db.Column(db.String(7), default='#0d6efd')  # Barva pro kalendář

    project = db.relationship('Project', backref='templates')
    user = db.relationship('User', backref='templates')