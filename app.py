from flask import Flask, render_template, redirect, url_for, request, flash, Response, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, date
from sqlalchemy import func, text, and_, or_
import json
import os
import csv
import io
import xlsxwriter
from dateutil.relativedelta import relativedelta
from models import db, User, Zakazka, Projekt, LogEntry, TaskTemplate, Project
from models_invoice import (InvoiceSettings, UserSettings, InvoiceHistory,
                            SupplierProfile, Customer, LocalInvoice, LocalInvoiceItem,
                            InvoiceTemplate, InvoiceCounter)
from idoklad_api import IDokladAPI


# Import kalendářového blueprintu
from calendar_bp import bp as calendar_bp
# Import blueprintu pro lokální faktury
from invoice_bp import bp as invoice_bp


def parse_local_time(value):
    """Přijme string ve formátu "YYYY-MM-DDTHH:MM" a vrátí naive datetime."""
    if value:
        return datetime.fromisoformat(value)
    return None


ALL_COLUMNS = [
    ("id", "ID"),
    ("project", "Projekt"),
    ("start_time", "Začátek"),
    ("end_time", "Konec"),
    ("pause_start", "Start pauzy"),
    ("pause_end", "Konec pauzy"),
    ("note", "Poznámka"),
    ("hours", "Odpracované hodiny")
]

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI',
                                                        'mysql+pymysql://dochazka_user:dochazka_pass@db:3306/dochazka')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'supertajnyklic'

# Inicializace databáze a Flask-Login
db.init_app(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Registrace kalendářového Blueprintu
app.register_blueprint(calendar_bp)
# Registrace blueprintu pro lokální faktury
app.register_blueprint(invoice_bp)

# Inicializace Flask-Migrate
from flask_migrate import Migrate
migrate = Migrate(app, db)

# Načítání uživatele pro Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --------------------------------------------------
#                  NOVÉ ROUTY
# --------------------------------------------------

@app.route('/test')
def test():
    return "Test OK", 200

# --------------------------------------------------
#           NOVÉ ROUTY PRO ZAKÁZKY A PROJEKTY
# --------------------------------------------------

@app.route('/zakazky')
@login_required
def zakazky():
    """Seznam zakázek uživatele s projekty"""
    zakazky_list = Zakazka.query.filter_by(user_id=current_user.id)\
        .options(db.joinedload(Zakazka.projekty)).all()
    return render_template('zakazky.html', zakazky=zakazky_list)

@app.route('/zakazky/create', methods=['GET', 'POST'])
@login_required
def create_zakazka():
    """Vytvoření zakázky + výchozího projektu"""
    if request.method == 'POST':
        name = request.form.get('name')
        color = request.form.get('color', '#0d6efd')

        new_zakazka = Zakazka(name=name, user_id=current_user.id, color=color)
        db.session.add(new_zakazka)
        db.session.commit()

        # Vytvoř výchozí projekt
        default_projekt = Projekt(
            name=f"{name} - Všeobecné práce",
            zakazka_id=new_zakazka.id
        )
        db.session.add(default_projekt)
        db.session.commit()

        flash(f'Zakázka "{name}" byla vytvořena.')
        return redirect(url_for('zakazky'))

    return render_template('create_zakazka.html')

@app.route('/zakazky/<int:zakazka_id>/projekty', methods=['GET', 'POST'])
@login_required
def manage_projekty(zakazka_id):
    """Správa projektů pod zakázkou"""
    zakazka = Zakazka.query.get_or_404(zakazka_id)
    if zakazka.user_id != current_user.id:
        flash('Nemáte oprávnění spravovat tuto zakázku.')
        return redirect(url_for('zakazky'))

    if request.method == 'POST':
        name = request.form.get('name')
        color = request.form.get('color', '#28a745')
        projekt = Projekt(name=name, zakazka_id=zakazka_id, color=color)
        db.session.add(projekt)
        db.session.commit()
        flash(f'Projekt "{name}" byl přidán.')

    projekty_list = Projekt.query.filter_by(zakazka_id=zakazka_id).all()
    return render_template('manage_projekty.html',
                          zakazka=zakazka, projekty=projekty_list)

@app.route('/zakazky/delete/<int:zakazka_id>', methods=['POST'])
@login_required
def delete_zakazka(zakazka_id):
    """Smazání/archivace zakázky"""
    zakazka = Zakazka.query.get_or_404(zakazka_id)
    if zakazka.user_id != current_user.id:
        flash('Nemáte oprávnění smazat tuto zakázku.')
        return redirect(url_for('zakazky'))

    # Zkontroluj log entries
    total_logs = db.session.query(func.count(LogEntry.id))\
        .join(Projekt).filter(Projekt.zakazka_id == zakazka_id).scalar()

    if total_logs > 0:
        # Místo smazání zakázku archivujeme
        zakazka.is_active = False
        db.session.commit()
        flash(f'Zakázka byla archivována (má {total_logs} záznamů).')
    else:
        db.session.delete(zakazka)
        db.session.commit()
        flash('Zakázka byla smazána.')

    return redirect(url_for('zakazky'))

@app.route('/zakazky/toggle/<int:zakazka_id>', methods=['POST'])
@login_required
def toggle_zakazka(zakazka_id):
    """Aktivace/deaktivace zakázky"""
    zakazka = Zakazka.query.get_or_404(zakazka_id)
    if zakazka.user_id != current_user.id:
        flash('Nemáte oprávnění upravit tuto zakázku.')
        return redirect(url_for('zakazky'))

    zakazka.is_active = not zakazka.is_active
    db.session.commit()
    status = "aktivována" if zakazka.is_active else "archivována"
    flash(f'Zakázka byla {status}.')
    return redirect(url_for('zakazky'))

@app.route('/zakazky/edit/<int:zakazka_id>', methods=['POST'])
@login_required
def edit_zakazka(zakazka_id):
    """Úprava názvu a barvy zakázky"""
    zakazka = Zakazka.query.get_or_404(zakazka_id)
    if zakazka.user_id != current_user.id:
        flash('Nemáte oprávnění upravit tuto zakázku.')
        return redirect(url_for('zakazky'))

    name = request.form.get('name', '').strip()
    color = request.form.get('color', zakazka.color)

    if not name:
        flash('Název zakázky nemůže být prázdný.')
        return redirect(url_for('zakazky'))

    zakazka.name = name
    zakazka.color = color
    db.session.commit()
    flash(f'Zakázka byla přejmenována na "{name}".')
    return redirect(url_for('zakazky'))

@app.route('/projekty/edit/<int:projekt_id>', methods=['POST'])
@login_required
def edit_projekt(projekt_id):
    """Úprava názvu a barvy projektu"""
    projekt = Projekt.query.get_or_404(projekt_id)
    if projekt.zakazka.user_id != current_user.id:
        flash('Nemáte oprávnění upravit tento projekt.')
        return redirect(url_for('zakazky'))

    name = request.form.get('name', '').strip()
    color = request.form.get('color', projekt.color)

    if not name:
        flash('Název projektu nemůže být prázdný.')
        return redirect(url_for('manage_projekty', zakazka_id=projekt.zakazka_id))

    projekt.name = name
    projekt.color = color
    db.session.commit()
    flash(f'Projekt byl přejmenován na "{name}".')
    return redirect(url_for('manage_projekty', zakazka_id=projekt.zakazka_id))

@app.route('/projekty/delete/<int:projekt_id>', methods=['POST'])
@login_required
def delete_projekt(projekt_id):
    """Smazání projektu"""
    projekt = Projekt.query.get_or_404(projekt_id)
    if projekt.zakazka.user_id != current_user.id:
        flash('Nemáte oprávnění smazat tento projekt.')
        return redirect(url_for('zakazky'))

    # Zjisti počet projektů v zakázce
    projekty_count = Projekt.query.filter_by(zakazka_id=projekt.zakazka_id).count()

    if projekty_count <= 1:
        flash('Nelze smazat poslední projekt v zakázce.')
        return redirect(url_for('manage_projekty', zakazka_id=projekt.zakazka_id))

    if projekt.logs:
        flash(f'Nelze smazat projekt s {len(projekt.logs)} existujícími záznamy.')
        return redirect(url_for('manage_projekty', zakazka_id=projekt.zakazka_id))

    zakazka_id = projekt.zakazka_id
    db.session.delete(projekt)
    db.session.commit()
    flash('Projekt byl smazán.')
    return redirect(url_for('manage_projekty', zakazka_id=zakazka_id))

@app.route('/')
@login_required
def dashboard():
    """Úvodní dashboard s přehledem statistik."""
    today = datetime.now().date()
    
    # Dnešní odpracované hodiny
    today_logs = LogEntry.query.filter(
        LogEntry.user_id == current_user.id,
        func.date(LogEntry.start_time) == today
    ).all()
    
    today_hours = 0
    for log in today_logs:
        if log.start_time and log.end_time:
            minutes = (log.end_time - log.start_time).total_seconds() / 60.0
            if log.pause_start and log.pause_end:
                minutes -= (log.pause_end - log.pause_start).total_seconds() / 60.0
            today_hours += minutes / 60.0
    
    # Tento týden
    week_start = today - timedelta(days=today.weekday())
    week_logs = LogEntry.query.filter(
        LogEntry.user_id == current_user.id,
        func.date(LogEntry.start_time) >= week_start
    ).all()
    
    week_hours = 0
    for log in week_logs:
        if log.start_time and log.end_time:
            minutes = (log.end_time - log.start_time).total_seconds() / 60.0
            if log.pause_start and log.pause_end:
                minutes -= (log.pause_end - log.pause_start).total_seconds() / 60.0
            week_hours += minutes / 60.0
    
    # Tento měsíc
    month_start = today.replace(day=1)
    month_logs = LogEntry.query.filter(
        LogEntry.user_id == current_user.id,
        func.date(LogEntry.start_time) >= month_start
    ).all()
    
    month_hours = 0
    for log in month_logs:
        if log.start_time and log.end_time:
            minutes = (log.end_time - log.start_time).total_seconds() / 60.0
            if log.pause_start and log.pause_end:
                minutes -= (log.pause_end - log.pause_start).total_seconds() / 60.0
            month_hours += minutes / 60.0
    
    # Aktivní zakázky
    active_zakazky = Zakazka.query.filter_by(user_id=current_user.id, is_active=True).count()
    
    # Posledních 5 záznamů
    recent_logs = LogEntry.query.filter_by(user_id=current_user.id)\
                                 .order_by(LogEntry.start_time.desc())\
                                 .limit(5).all()
    
    # Aktuálně běžící aktivita
    active_log = LogEntry.query.filter_by(
        user_id=current_user.id,
        end_time=None
    ).first()
    
    # Top 3 zakázky tento měsíc
    top_zakazky = db.session.query(
        Zakazka.name,
        Zakazka.color,
        func.sum(
            func.timestampdiff(text('MINUTE'), LogEntry.start_time, LogEntry.end_time)
            - func.coalesce(
                func.timestampdiff(text('MINUTE'), LogEntry.pause_start, LogEntry.pause_end), 0
            )
        ) / 60.0
    ).select_from(LogEntry)\
     .join(Projekt, LogEntry.project_id == Projekt.id)\
     .join(Zakazka, Projekt.zakazka_id == Zakazka.id)\
     .filter(
        LogEntry.user_id == current_user.id,
        LogEntry.end_time.isnot(None),
        func.date(LogEntry.start_time) >= month_start
    ).group_by(Zakazka.name, Zakazka.color).order_by(text('3 DESC')).limit(3).all()

    return render_template('dashboard.html',
                          today_hours=round(today_hours, 2),
                          week_hours=round(week_hours, 2),
                          month_hours=round(month_hours, 2),
                          active_zakazky=active_zakazky,
                          recent_logs=recent_logs,
                          active_log=active_log,
                          top_zakazky=top_zakazky)

@app.route('/api/logs')
@login_required
def api_logs():
    """API endpoint pro načítání záznamů s filtrováním a stránkováním."""
    # Parametry z URL
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    search = request.args.get('search', '')
    project_id = request.args.get('project_id', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    # Základní query
    query = LogEntry.query.filter_by(user_id=current_user.id)
    
    # Filtrování podle projektu
    if project_id:
        query = query.filter(LogEntry.project_id == int(project_id))
    
    # Filtrování podle data
    if date_from:
        query = query.filter(LogEntry.start_time >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(LogEntry.start_time <= datetime.fromisoformat(date_to))
    
    # Vyhledávání v poznámkách
    if search:
        query = query.filter(LogEntry.note.contains(search))
    
    # Stránkování
    pagination = query.order_by(LogEntry.start_time.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Formátování dat
    logs_data = []
    for log in pagination.items:
        total_minutes = 0
        if log.start_time and log.end_time:
            total_minutes = (log.end_time - log.start_time).total_seconds() / 60.0
            if log.pause_start and log.pause_end:
                total_minutes -= (log.pause_end - log.pause_start).total_seconds() / 60.0
        
        logs_data.append({
            "id": log.id,
            "project_name": log.project.name if log.project else "",
            "start_time": log.start_time.isoformat() if log.start_time else None,
            "end_time": log.end_time.isoformat() if log.end_time else None,
            "pause_start": log.pause_start.isoformat() if log.pause_start else None,
            "pause_end": log.pause_end.isoformat() if log.pause_end else None,
            "note": log.note,
            "hours": round(total_minutes / 60.0, 2)
        })
    
    return jsonify({
        'logs': logs_data,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
        'per_page': per_page
    })

@app.route('/calendar')
@login_required
def calendar_view():
    templates = TaskTemplate.query.filter_by(user_id=current_user.id).all()
    zakazky = Zakazka.query.filter_by(user_id=current_user.id)\
        .options(db.joinedload(Zakazka.projekty)).all()
    return render_template('calendar.html', templates=templates, zakazky=zakazky)

# --------------------------------------------------
#              PŮVODNÍ ROUTY (upravené)
# --------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))  # Změna: přesměrování na dashboard
        else:
            flash('Neplatné uživatelské jméno nebo heslo')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            flash('Uživatel s tímto jménem již existuje.')
        else:
            new_user = User(username=username, password=generate_password_hash(password))
            db.session.add(new_user)
            db.session.commit()
            flash('Uživatel vytvořen. Nyní se můžeš přihlásit.')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/projects')
@login_required
def projects():
    projects = Project.query.filter_by(user_id=current_user.id).all()
    return render_template('projects.html', projects=projects)

@app.route('/projects/create', methods=['GET', 'POST'])
@login_required
def create_project():
    if request.method == 'POST':
        name = request.form.get('name')
        if name:
            new_project = Project(name=name, user_id=current_user.id)
            db.session.add(new_project)
            db.session.commit()
            return redirect(url_for('projects'))
        else:
            flash('Název projektu je povinný.')
    return render_template('create_project.html')

@app.route('/projects/delete/<int:project_id>', methods=['POST'])
@login_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    if project.user_id != current_user.id:
        flash('Nemáte oprávnění smazat tento projekt.')
        return redirect(url_for('projects'))
    db.session.delete(project)
    db.session.commit()
    return redirect(url_for('projects'))

@app.route('/log', methods=['GET', 'POST'])
@login_required
def log_time():
    # Načti zakázky s projekty pro hierarchický select
    zakazky_list = Zakazka.query.filter_by(user_id=current_user.id, is_active=True)\
        .options(db.joinedload(Zakazka.projekty)).all()

    if request.method == 'POST':
        project_id = request.form.get('project_id')
        action = request.form.get('action')
        note = request.form.get('note')
        parsed_start = parse_local_time(request.form.get('start_time'))
        parsed_end = parse_local_time(request.form.get('end_time'))
        parsed_pause_s = parse_local_time(request.form.get('pause_start_time'))
        parsed_pause_e = parse_local_time(request.form.get('pause_end_time'))

        if not parsed_start and action == 'start':
            parsed_start = datetime.now()

        current_log = LogEntry.query.filter_by(
            user_id=current_user.id,
            project_id=project_id,
            end_time=None
        ).first()

        if action == 'start':
            if not current_log:
                new_log = LogEntry(
                    project_id=project_id,
                    user_id=current_user.id,
                    start_time=parsed_start,
                    note=note
                )
                if parsed_end:
                    new_log.end_time = parsed_end
                db.session.add(new_log)
                db.session.commit()
            else:
                flash('Činnost již probíhá.')
        elif action == 'end':
            if current_log:
                current_log.end_time = parsed_end if parsed_end else datetime.now()
                db.session.commit()
            else:
                flash('Žádná aktivní činnost k ukončení.')
        elif action == 'pause_start':
            if current_log and not current_log.pause_start:
                current_log.pause_start = parsed_pause_s if parsed_pause_s else datetime.now()
                db.session.commit()
            else:
                flash('Nelze spustit pauzu (možná již probíhá).')
        elif action == 'pause_end':
            if current_log and current_log.pause_start and not current_log.pause_end:
                current_log.pause_end = parsed_pause_e if parsed_pause_e else datetime.now()
                db.session.commit()
            else:
                flash('Pauza nebyla spuštěna nebo již ukončena.')
        else:
            flash('Neznámá akce.')
        return redirect(url_for('log_time'))

    return render_template('log_time.html', zakazky=zakazky_list)

@app.route('/logs')
@login_required
def logs():
    """Vylepšená verze s podporou filtrování a stránkování."""
    # Parametry z URL
    page = request.args.get('page', 1, type=int)
    per_page = 50  # Pevný počet záznamů na stránku
    search = request.args.get('search', '')
    project_id = request.args.get('project_id', '')
    zakazka_id = request.args.get('zakazka_id', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    status = request.args.get('status', '')  # running, completed, all
    quick_filter = request.args.get('quick', '')  # today, yesterday, week, month

    # Základní query
    query = LogEntry.query.filter_by(user_id=current_user.id)

    # Rychlé filtry
    today = date.today()
    if quick_filter == 'today':
        date_from = today.isoformat()
        date_to = today.isoformat()
    elif quick_filter == 'yesterday':
        yesterday = today - timedelta(days=1)
        date_from = yesterday.isoformat()
        date_to = yesterday.isoformat()
    elif quick_filter == 'week':
        week_start = today - timedelta(days=today.weekday())
        date_from = week_start.isoformat()
        date_to = today.isoformat()
    elif quick_filter == 'month':
        month_start = today.replace(day=1)
        date_from = month_start.isoformat()
        date_to = today.isoformat()

    # Filtrování podle zakázky
    if zakazka_id:
        query = query.join(Projekt).filter(Projekt.zakazka_id == int(zakazka_id))

    # Filtrování podle projektu
    if project_id:
        query = query.filter(LogEntry.project_id == int(project_id))

    # Filtrování podle data
    if date_from:
        query = query.filter(func.date(LogEntry.start_time) >= date_from)
    if date_to:
        query = query.filter(func.date(LogEntry.start_time) <= date_to)

    # Filtrování podle statusu
    if status == 'running':
        query = query.filter(LogEntry.end_time == None)
    elif status == 'completed':
        query = query.filter(LogEntry.end_time != None)

    # Vyhledávání v poznámkách
    if search:
        query = query.filter(LogEntry.note.contains(search))

    # Stránkování
    pagination = query.order_by(LogEntry.start_time.desc())\
                     .paginate(page=page, per_page=per_page, error_out=False)

    logs_with_hours = []
    for log in pagination.items:
        total_minutes = 0
        if log.start_time and log.end_time:
            total_minutes = (log.end_time - log.start_time).total_seconds() / 60.0
        if log.pause_start and log.pause_end:
            total_minutes -= (log.pause_end - log.pause_start).total_seconds() / 60.0
        logs_with_hours.append({
            "id": log.id,
            "projekt_name": log.project.name if log.project else "",
            "zakazka_name": log.project.zakazka.name if log.project and log.project.zakazka else "",
            "projekt_color": log.project.color if log.project else "#28a745",
            "zakazka_color": log.project.zakazka.color if log.project and log.project.zakazka else "#0d6efd",
            "start_time": log.start_time,
            "end_time": log.end_time,
            "pause_start": log.pause_start,
            "pause_end": log.pause_end,
            "note": log.note,
            "hours": total_minutes / 60.0
        })

    # Získáme všechny zakázky s projekty pro filtr
    zakazky = Zakazka.query.filter_by(user_id=current_user.id)\
        .options(db.joinedload(Zakazka.projekty)).all()

    return render_template('logs.html',
                          logs=logs_with_hours,
                          pagination=pagination,
                          zakazky=zakazky,
                          filters={
                              'search': search,
                              'project_id': project_id,
                              'zakazka_id': zakazka_id,
                              'date_from': date_from,
                              'date_to': date_to,
                              'status': status,
                              'quick': quick_filter
                          })

@app.route('/logs/delete/<int:log_id>', methods=['POST'])
@login_required
def delete_log(log_id):
    log_entry = LogEntry.query.get_or_404(log_id)
    if log_entry.user_id != current_user.id:
        flash('Nemáte oprávnění smazat tento záznam.')
        return redirect(url_for('logs'))
    db.session.delete(log_entry)
    db.session.commit()
    flash('Záznam byl úspěšně smazán.')
    return redirect(url_for('logs'))

@app.route('/logs/edit/<int:log_id>', methods=['GET', 'POST'])
@login_required
def edit_log(log_id):
    log_entry = LogEntry.query.get_or_404(log_id)
    if log_entry.user_id != current_user.id:
        flash('Nemáte oprávnění upravit tento záznam.')
        return redirect(url_for('logs'))
    if request.method == 'POST':
        log_entry.start_time = parse_local_time(request.form.get('start_time')) or log_entry.start_time
        log_entry.end_time = parse_local_time(request.form.get('end_time'))
        log_entry.pause_start = parse_local_time(request.form.get('pause_start_time'))
        log_entry.pause_end = parse_local_time(request.form.get('pause_end_time'))
        log_entry.note = request.form.get('note')
        db.session.commit()
        flash('Záznam byl upraven.')
        return redirect(url_for('logs'))
    return render_template('edit_log.html', log=log_entry)

@app.route('/export', methods=['GET'])
@login_required
def export():
    zakazky = Zakazka.query.filter_by(user_id=current_user.id)\
        .options(db.joinedload(Zakazka.projekty)).all()
    return render_template('export.html', zakazky=zakazky)

@app.route('/reports', methods=['GET'])
@login_required
def reports_view():
    """Opravená verze reportů s funkčními filtry."""
    # Čtení filtrů
    period = request.args.get('period', 'monthly')
    zakazka_id = request.args.get('zakazka_id', 'all')
    projekt_id = request.args.get('projekt_id', 'all')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Načtení zakázek s projekty pro dropdown
    zakazky = Zakazka.query.filter_by(user_id=current_user.id)\
        .options(db.joinedload(Zakazka.projekty)).all()

    # Seskupení podle periody
    if period == 'daily':
        grouping = func.date(LogEntry.start_time)
        label_fmt = lambda d: d.isoformat() if d else ''
    elif period == 'weekly':
        grouping = func.yearweek(LogEntry.start_time)
        label_fmt = lambda w: f"Týden {w}" if w else ''
    else:  # monthly
        grouping = func.date_format(LogEntry.start_time, '%Y-%m')
        label_fmt = lambda m: m if m else ''

    # Agregace dat - podle zakázky nebo projektu
    # Rozhodneme se, zda agregovat podle zakázky nebo projektu
    if zakazka_id != 'all' or projekt_id == 'all':
        # Agreguj podle zakázek
        raw_data = db.session.query(
            grouping.label('period'),
            Zakazka.name.label('group_name'),
            Zakazka.color.label('group_color'),
            func.sum(
                func.timestampdiff(text('MINUTE'), LogEntry.start_time, LogEntry.end_time)
                - func.coalesce(
                    func.timestampdiff(text('MINUTE'), LogEntry.pause_start, LogEntry.pause_end), 0
                )
            ).label('total_minutes')
        ).select_from(LogEntry)\
         .join(Projekt, LogEntry.project_id == Projekt.id)\
         .join(Zakazka, Projekt.zakazka_id == Zakazka.id)\
         .filter(
            LogEntry.user_id == current_user.id,
            LogEntry.end_time.isnot(None)
        )

        # Filtr podle zakázky
        if zakazka_id != 'all':
            raw_data = raw_data.filter(Zakazka.id == int(zakazka_id))

        raw_data = raw_data.group_by(grouping, Zakazka.name, Zakazka.color)
    else:
        # Agreguj podle projektů
        raw_data = db.session.query(
            grouping.label('period'),
            Projekt.name.label('group_name'),
            Projekt.color.label('group_color'),
            func.sum(
                func.timestampdiff(text('MINUTE'), LogEntry.start_time, LogEntry.end_time)
                - func.coalesce(
                    func.timestampdiff(text('MINUTE'), LogEntry.pause_start, LogEntry.pause_end), 0
                )
            ).label('total_minutes')
        ).select_from(LogEntry)\
         .join(Projekt, LogEntry.project_id == Projekt.id)\
         .filter(
            LogEntry.user_id == current_user.id,
            LogEntry.end_time.isnot(None)
        )

        # Filtr podle projektu
        if projekt_id != 'all':
            raw_data = raw_data.filter(Projekt.id == int(projekt_id))

        raw_data = raw_data.group_by(grouping, Projekt.name, Projekt.color)

    # Aplikace společných filtrů
    if start_date:
        raw_data = raw_data.filter(LogEntry.start_time >= datetime.fromisoformat(start_date))
    if end_date:
        end_dt = datetime.fromisoformat(end_date) + relativedelta(days=1)
        raw_data = raw_data.filter(LogEntry.start_time < end_dt)

    raw_data = raw_data.all()

    # Pivot data pro graf
    pivot = {}
    proj_names = set()
    color_map = {}

    for per, name, color, minutes in raw_data:
        key = label_fmt(per)
        if key:  # Přeskočit prázdné klíče
            hours = float(minutes or 0) / 60.0
            pivot.setdefault(key, {})[name] = round(hours, 2)
            proj_names.add(name)
            color_map[name] = color or '#0d6efd'

    # Připravit data pro Chart.js
    labels = sorted(pivot.keys())
    datasets = []

    def hex_to_rgba(hex_color, alpha=0.5):
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return f"rgba({r}, {g}, {b}, {alpha})"

    for name in sorted(proj_names):
        bg_color = hex_to_rgba(color_map.get(name, '#0d6efd'), 0.5)
        border_color = hex_to_rgba(color_map.get(name, '#0d6efd'), 1)
        dataset = {
            "label": name,
            "data": [pivot.get(l, {}).get(name, 0) for l in labels],
            "backgroundColor": bg_color,
            "borderColor": border_color,
            "borderWidth": 1
        }
        datasets.append(dataset)
    
    chart_data = {
        "labels": labels,
        "datasets": datasets
    }

    return render_template(
        'reports.html',
        period=period,
        zakazky=zakazky,
        zakazka_id=zakazka_id,
        projekt_id=projekt_id,
        start_date=start_date,
        end_date=end_date,
        chart_data=chart_data,
        data_exists=bool(datasets and any(sum(d['data']) > 0 for d in datasets))
    )

@app.route('/export/csv')
@login_required
def export_csv():
    """Export do CSV."""
    project_ids = request.args.getlist('project_ids')
    all_projects = request.args.get('all_projects')
    month = request.args.get('month')
    selected_columns = request.args.getlist('columns')

    if not selected_columns:
        selected_columns = [col[0] for col in ALL_COLUMNS]

    query = LogEntry.query.filter_by(user_id=current_user.id)

    # Filtrování podle projektů
    if not all_projects and project_ids:
        query = query.filter(LogEntry.project_id.in_([int(pid) for pid in project_ids]))
    
    if month:
        start_date = datetime.strptime(month, '%Y-%m')
        end_date = start_date + relativedelta(months=1)
        query = query.filter(LogEntry.start_time >= start_date,
                           LogEntry.start_time < end_date)
    
    user_logs = query.order_by(LogEntry.start_time.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Hlavičky
    headers = [label for key, label in ALL_COLUMNS if key in selected_columns]
    writer.writerow(headers)
    
    # Data
    for log in user_logs:
        minutes = 0
        if log.start_time and log.end_time:
            minutes = (log.end_time - log.start_time).total_seconds() / 60.0
        if log.pause_start and log.pause_end:
            minutes -= (log.pause_end - log.pause_start).total_seconds() / 60.0
        hours = round(minutes / 60.0, 2)
        
        row = []
        for key in selected_columns:
            if key == 'id':
                row.append(log.id)
            elif key == 'project':
                row.append(log.project.name if log.project else '')
            elif key == 'start_time':
                row.append(log.start_time.strftime('%Y-%m-%d %H:%M') if log.start_time else '')
            elif key == 'end_time':
                row.append(log.end_time.strftime('%Y-%m-%d %H:%M') if log.end_time else '')
            elif key == 'pause_start':
                row.append(log.pause_start.strftime('%Y-%m-%d %H:%M') if log.pause_start else '')
            elif key == 'pause_end':
                row.append(log.pause_end.strftime('%Y-%m-%d %H:%M') if log.pause_end else '')
            elif key == 'note':
                row.append(log.note or '')
            elif key == 'hours':
                row.append(hours)
        writer.writerow(row)
    
    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=dochazka_export.csv"}
    )

@app.route('/export/excel')
@login_required
def export_excel():
    project_ids = request.args.getlist('project_ids')
    all_projects = request.args.get('all_projects')
    month = request.args.get('month')
    selected_columns = request.args.getlist('columns')

    if not selected_columns:
        selected_columns = ['id', 'project', 'start_time', 'end_time', 'note', 'hours']

    query = LogEntry.query.filter_by(user_id=current_user.id)

    # Filtrování podle projektů
    if not all_projects and project_ids:
        query = query.filter(LogEntry.project_id.in_([int(pid) for pid in project_ids]))
    
    if month:
        start_date = datetime.strptime(month, '%Y-%m')
        end_date = start_date + relativedelta(months=1)
        query = query.filter(LogEntry.start_time >= start_date,
                           LogEntry.start_time < end_date)

    user_logs = query.order_by(LogEntry.start_time.desc()).all()

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet("Docházka")

    # Formáty
    header_format = workbook.add_format({'bold': True, 'bg_color': '#DCE6F1'})

    # Hlavičky
    headers = []
    for key in selected_columns:
        if key == 'id': headers.append('ID')
        elif key == 'project': headers.append('Projekt')
        elif key == 'start_time': headers.append('Začátek')
        elif key == 'end_time': headers.append('Konec')
        elif key == 'pause_start': headers.append('Start pauzy')
        elif key == 'pause_end': headers.append('Konec pauzy')
        elif key == 'note': headers.append('Poznámka')
        elif key == 'hours': headers.append('Hodiny')
    
    for col_idx, header in enumerate(headers):
        worksheet.write(0, col_idx, header, header_format)

    # Data
    total_hours = 0
    for row_idx, log in enumerate(user_logs, 1):
        # Výpočet hodin
        minutes = 0
        if log.start_time and log.end_time:
            minutes = (log.end_time - log.start_time).total_seconds() / 60.0
        if log.pause_start and log.pause_end:
            minutes -= (log.pause_end - log.pause_start).total_seconds() / 60.0
        hours = round(minutes / 60.0, 2)
        total_hours += hours

        # Zápis řádku
        col_idx = 0
        for key in selected_columns:
            if key == 'id':
                worksheet.write(row_idx, col_idx, log.id)
            elif key == 'project':
                worksheet.write(row_idx, col_idx, log.project.name if log.project else '')
            elif key == 'start_time':
                worksheet.write(row_idx, col_idx, log.start_time.strftime('%d.%m.%Y %H:%M') if log.start_time else '')
            elif key == 'end_time':
                worksheet.write(row_idx, col_idx, log.end_time.strftime('%d.%m.%Y %H:%M') if log.end_time else '')
            elif key == 'pause_start':
                worksheet.write(row_idx, col_idx, log.pause_start.strftime('%d.%m.%Y %H:%M') if log.pause_start else '')
            elif key == 'pause_end':
                worksheet.write(row_idx, col_idx, log.pause_end.strftime('%d.%m.%Y %H:%M') if log.pause_end else '')
            elif key == 'note':
                worksheet.write(row_idx, col_idx, log.note or '')
            elif key == 'hours':
                worksheet.write(row_idx, col_idx, hours)
            col_idx += 1

    # Součet hodin
    if 'hours' in selected_columns:
        hours_col = selected_columns.index('hours')
        worksheet.write(len(user_logs) + 1, 0, "Celkem hodin:", header_format)
        worksheet.write(len(user_logs) + 1, hours_col, total_hours, header_format)

    workbook.close()
    output.seek(0)
    
    return Response(
        output.read(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-disposition": f"attachment; filename=dochazka_export.xlsx"}
    )

@app.route('/templates')
@login_required
def templates():
    templates = TaskTemplate.query.filter_by(user_id=current_user.id).all()
    zakazky = Zakazka.query.filter_by(user_id=current_user.id)\
        .options(db.joinedload(Zakazka.projekty)).all()
    return render_template('templates.html', templates=templates, zakazky=zakazky)

@app.route('/templates/create', methods=['POST'])
@login_required
def create_template():
    name = request.form.get('name')
    project_id = request.form.get('project_id')
    duration = request.form.get('duration_minutes', 60)
    note = request.form.get('note')
    
    template = TaskTemplate(
        name=name,
        project_id=project_id,
        user_id=current_user.id,
        duration_minutes=int(duration),
        note=note
    )
    db.session.add(template)
    db.session.commit()
    flash('Šablona vytvořena')
    return redirect(url_for('templates'))

@app.route('/templates/apply/<int:template_id>', methods=['POST'])
@login_required
def apply_template(template_id):
    template = TaskTemplate.query.get_or_404(template_id)
    if template.user_id != current_user.id:
        flash('Neplatná šablona')
        return redirect(url_for('calendar_view'))
    
    # Vytvoř nový záznam podle šablony
    start = datetime.now()
    end = start + timedelta(minutes=template.duration_minutes)
    
    log = LogEntry(
        project_id=template.project_id,
        user_id=current_user.id,
        start_time=start,
        end_time=end,
        note=template.note
    )
    db.session.add(log)
    db.session.commit()
    
    flash(f'Vytvořen záznam podle šablony: {template.name}')
    return redirect(url_for('calendar_view'))

@app.route('/templates/delete/<int:template_id>', methods=['POST'])
@login_required
def delete_template(template_id):
    template = TaskTemplate.query.get_or_404(template_id)
    if template.user_id != current_user.id:
        flash('Nemáte oprávnění smazat tuto šablonu.')
        return redirect(url_for('templates'))
    db.session.delete(template)
    db.session.commit()
    flash('Šablona byla smazána.')
    return redirect(url_for('templates'))

@app.route('/invoicing')
@login_required
def invoicing():
    """Stránka pro správu fakturace - agregace podle zakázek"""
    # Načti souhrny po měsících podle ZAKÁZEK (sečti všechny projekty)
    monthly_data = db.session.query(
        func.date_format(LogEntry.start_time, '%Y-%m').label('month'),
        Zakazka.id.label('zakazka_id'),
        Zakazka.name.label('zakazka_name'),
        func.sum(
            func.timestampdiff(text('MINUTE'), LogEntry.start_time, LogEntry.end_time)
        ) / 60.0
    ).select_from(LogEntry)\
     .join(Projekt, LogEntry.project_id == Projekt.id)\
     .join(Zakazka, Projekt.zakazka_id == Zakazka.id)\
     .filter(
        LogEntry.user_id == current_user.id,
        LogEntry.end_time.isnot(None)
    ).group_by('month', Zakazka.id).order_by(text('month DESC')).all()

    # Načti historii faktur - pozor, invoice_history má project_id (který je teď projekt, ne zakázka)
    # Potřebujeme mapovat projekty na zakázky
    invoice_history = InvoiceHistory.query.filter_by(user_id=current_user.id).all()
    # Vytvoř set fakturovaných měsíců/zakázek
    invoiced_months = set()
    for h in invoice_history:
        if h.projekt:
            invoiced_months.add((h.month, h.projekt.zakazka_id))

    # Připrav data s informací o fakturaci
    summaries = []
    for row in monthly_data:
        summaries.append({
            'month': row.month,
            'zakazka_id': row.zakazka_id,
            'zakazka_name': row.zakazka_name,
            'hours': round(row[3], 2),
            'is_invoiced': (row.month, row.zakazka_id) in invoiced_months
        })

    # Načti nastavení pro zakázky
    settings = InvoiceSettings.query.join(Zakazka).filter(
        Zakazka.user_id == current_user.id
    ).all()

    return render_template('invoicing.html',
                          summaries=summaries,
                          settings=settings)

@app.route('/invoicing/settings')
@login_required
def invoicing_settings():
    """Nastavení fakturace pro zakázky"""
    user_settings = UserSettings.query.filter_by(user_id=current_user.id).first()
    zakazky = Zakazka.query.filter_by(user_id=current_user.id).all()
    invoice_settings = InvoiceSettings.query.join(Zakazka).filter(
        Zakazka.user_id == current_user.id
    ).all()

    return render_template('invoicing_settings.html',
                          user_settings=user_settings,
                          zakazky=zakazky,
                          invoice_settings=invoice_settings)

@app.route('/invoicing/settings/save', methods=['POST'])
@login_required
def save_invoicing_settings():
    """Uložení nastavení"""
    # Ulož API klíče
    user_settings = UserSettings.query.filter_by(user_id=current_user.id).first()
    if not user_settings:
        user_settings = UserSettings(user_id=current_user.id)
        db.session.add(user_settings)
    
    user_settings.idoklad_api_key = request.form.get('api_key')
    user_settings.idoklad_api_secret = request.form.get('api_secret')
    
    # Ulož nastavení zakázek
    for key in request.form:
        if key.startswith('contact_'):
            zakazka_id = key.split('_')[1]
            settings = InvoiceSettings.query.filter_by(zakazka_id=zakazka_id).first()
            if not settings:
                settings = InvoiceSettings(zakazka_id=zakazka_id)
                db.session.add(settings)

            # Ošetři prázdné hodnoty
            contact_id = request.form.get(f'contact_{zakazka_id}')
            settings.idoklad_contact_id = int(contact_id) if contact_id and contact_id.strip() else None

            settings.idoklad_item_name = request.form.get(f'item_{zakazka_id}') or None

            rate = request.form.get(f'rate_{zakazka_id}')
            settings.hourly_rate = float(rate) if rate and rate.strip() else None

            md = request.form.get(f'md_{zakazka_id}')
            settings.hours_per_md = float(md) if md and md.strip() else 8.0
    
    db.session.commit()
    flash('Nastavení uloženo')
    return redirect(url_for('invoicing_settings'))

@app.route('/invoicing/create', methods=['POST'])
@login_required
def create_invoice_route():
    """Vytvoření faktury v iDokladu - agreguje hodiny ze všech projektů zakázky"""
    month = request.form.get('month')
    zakazka_id = int(request.form.get('zakazka_id'))
    description = request.form.get('description')

    # Načti nastavení pro zakázku
    settings = InvoiceSettings.query.filter_by(zakazka_id=zakazka_id).first()
    user_settings = UserSettings.query.filter_by(user_id=current_user.id).first()
    
    if not settings or not user_settings:
        flash('Chybí nastavení pro fakturaci')
        return redirect(url_for('invoicing'))
    
    # Spočítej hodiny ze VŠECH projektů pod zakázkou
    start_date = datetime.strptime(f"{month}-01", '%Y-%m-%d')
    end_date = start_date + relativedelta(months=1)

    total_minutes = db.session.query(
        func.sum(
            func.timestampdiff(text('MINUTE'), LogEntry.start_time, LogEntry.end_time)
        )
    ).join(Projekt).filter(
        Projekt.zakazka_id == zakazka_id,
        LogEntry.user_id == current_user.id,
        LogEntry.start_time >= start_date,
        LogEntry.start_time < end_date
    ).scalar() or 0
    
    hours = total_minutes / 60.0
    man_days = hours / settings.hours_per_md
    
    # Vytvoř fakturu přes API
    api = IDokladAPI(user_settings.idoklad_api_key, user_settings.idoklad_api_secret)
    
    items = [{
        'Name': settings.idoklad_item_name or f'Práce za {month}',
        'Quantity': round(man_days, 2),
        'UnitPrice': settings.hourly_rate * settings.hours_per_md,
        'Unit': 'MD',
        'VatRateType': 1  # Základní sazba DPH
    }]
    
    result = api.create_invoice(settings.idoklad_contact_id, items, description)
    
    if result.get('Data'):
        # Ulož do historie - použijeme první projekt zakázky pro kompatibilitu
        first_projekt = Projekt.query.filter_by(zakazka_id=zakazka_id).first()
        history = InvoiceHistory(
            user_id=current_user.id,
            project_id=first_projekt.id if first_projekt else None,
            month=month,
            hours=hours,
            invoice_number=result['Data'].get('DocumentNumber'),
            idoklad_invoice_id=result['Data'].get('Id')
        )
        db.session.add(history)
        db.session.commit()
        
        flash(f'Faktura {result["Data"]["DocumentNumber"]} vytvořena v iDokladu!')
    else:
        flash('Chyba při vytváření faktury: ' + str(result.get('Message', 'Neznámá chyba')))
    
    return redirect(url_for('invoicing'))

@app.route('/invoicing/test-connection', methods=['POST'])
@login_required
def test_idoklad_connection():
    """Test připojení k iDoklad API"""
    data = request.get_json()
    
    try:
        api = IDokladAPI(data['client_id'], data['client_secret'])
        if api.token:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Nepodařilo se získat token'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    
# --------------------------------------------------
#                Spuštění aplikace
# --------------------------------------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            user = User(username='admin', password=generate_password_hash('admin'))
            db.session.add(user)
            db.session.commit()
    
    # Spusť aplikaci
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
