from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'  # Explicitní název tabulky
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    # Vztah na zakázky, které tento uživatel vlastní
    zakazky = db.relationship('Zakazka', backref='owner', lazy=True)
    # Zpětná kompatibilita - alias pro zakazky
    projects = db.relationship('Zakazka', backref='user_compat', lazy=True, viewonly=True)

class Zakazka(db.Model):
    """Zakázka = logické seskupení projektů pro jednoho uživatele"""
    __tablename__ = 'zakazky'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    color = db.Column(db.String(7), default='#0d6efd')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Vztahy
    projekty = db.relationship('Projekt', backref='zakazka', lazy=True,
                               cascade='all, delete-orphan')

class Projekt(db.Model):
    """Projekt = konkrétní pracovní úkol pod zakázkou"""
    __tablename__ = 'projekty'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    zakazka_id = db.Column(db.Integer, db.ForeignKey('zakazky.id', ondelete='CASCADE'), nullable=False)
    color = db.Column(db.String(7), default='#28a745')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Vztahy
    logs = db.relationship('LogEntry', backref='projekt', lazy=True)
    templates = db.relationship('TaskTemplate', backref='projekt', lazy=True)

# Alias pro zpětnou kompatibilitu
Project = Zakazka

class LogEntry(db.Model):
    __tablename__ = 'log_entry'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projekty.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    pause_start = db.Column(db.DateTime, nullable=True)
    pause_end = db.Column(db.DateTime, nullable=True)
    note = db.Column(db.Text, nullable=True)

    # Zpětná kompatibilita - project is actually projekt now
    project = db.relationship('Projekt', backref=db.backref('logs_compat', lazy=True), foreign_keys=[project_id])
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
    project_id = db.Column(db.Integer, db.ForeignKey('projekty.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    duration_minutes = db.Column(db.Integer, default=60)  # Výchozí délka
    note = db.Column(db.Text, nullable=True)
    color = db.Column(db.String(7), default='#0d6efd')  # Barva pro kalendář

    # project is now projekt
    project = db.relationship('Projekt', backref='templates_compat', foreign_keys=[project_id])
    user = db.relationship('User', backref='templates')