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
from models import db, User, Project, LogEntry, TaskTemplate


# Import kalendářového blueprintu
from calendar_bp import bp as calendar_bp


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
    
    # Aktivní projekty
    active_projects = Project.query.filter_by(user_id=current_user.id).count()
    
    # Posledních 5 záznamů
    recent_logs = LogEntry.query.filter_by(user_id=current_user.id)\
                                 .order_by(LogEntry.start_time.desc())\
                                 .limit(5).all()
    
    # Aktuálně běžící aktivita
    active_log = LogEntry.query.filter_by(
        user_id=current_user.id,
        end_time=None
    ).first()
    
    # Top 3 projekty tento měsíc
    top_projects = db.session.query(
        Project.name,
        func.sum(
            func.timestampdiff(text('MINUTE'), LogEntry.start_time, LogEntry.end_time) 
            - func.coalesce(
                func.timestampdiff(text('MINUTE'), LogEntry.pause_start, LogEntry.pause_end), 0
            )
        ) / 60.0
    ).join(Project).filter(
        LogEntry.user_id == current_user.id,
        func.date(LogEntry.start_time) >= month_start
    ).group_by(Project.name).order_by(text('2 DESC')).limit(3).all()
    
    return render_template('dashboard.html',
                          today_hours=round(today_hours, 2),
                          week_hours=round(week_hours, 2),
                          month_hours=round(month_hours, 2),
                          active_projects=active_projects,
                          recent_logs=recent_logs,
                          active_log=active_log,
                          top_projects=top_projects)

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
    return render_template('calendar.html')

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
    projects = Project.query.filter_by(user_id=current_user.id).all()
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

    return render_template('log_time.html', projects=projects)

@app.route('/logs')
@login_required
def logs():
    """Vylepšená verze s podporou filtrování a stránkování."""
    # Parametry z URL
    page = request.args.get('page', 1, type=int)
    per_page = 50  # Pevný počet záznamů na stránku
    
    # Základní query s stránkováním
    pagination = LogEntry.query.filter_by(user_id=current_user.id)\
                               .order_by(LogEntry.start_time.desc())\
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
            "project_name": log.project.name if log.project else "",
            "start_time": log.start_time,
            "end_time": log.end_time,
            "pause_start": log.pause_start,
            "pause_end": log.pause_end,
            "note": log.note,
            "hours": total_minutes / 60.0
        })
    
    # Získáme všechny projekty pro filtr
    projects = Project.query.filter_by(user_id=current_user.id).all()
    
    return render_template('logs.html', 
                          logs=logs_with_hours,
                          pagination=pagination,
                          projects=projects)

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
    projects = Project.query.filter_by(user_id=current_user.id).all()
    return render_template('export.html', projects=projects)

@app.route('/reports', methods=['GET'])
@login_required
def reports_view():
    """Opravená verze reportů s funkčními filtry."""
    # Čtení filtrů
    period = request.args.get('period', 'monthly')
    project_id = request.args.get('project_id', 'all')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Načtení projektů pro dropdown
    projects = Project.query.filter_by(user_id=current_user.id).all()

    # Základní query s JOIN
    query = db.session.query(
        LogEntry, Project
    ).join(
        Project, Project.id == LogEntry.project_id
    ).filter(
        LogEntry.user_id == current_user.id,
        LogEntry.end_time.isnot(None)  # Pouze dokončené záznamy
    )
    
    # Filtry
    if project_id != 'all':
        query = query.filter(LogEntry.project_id == int(project_id))
    
    if start_date:
        query = query.filter(LogEntry.start_time >= datetime.fromisoformat(start_date))
    
    if end_date:
        # Přidat jeden den pro inclusive end date
        end_dt = datetime.fromisoformat(end_date) + relativedelta(days=1)
        query = query.filter(LogEntry.start_time < end_dt)

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

    # Agregace dat
    raw_data = db.session.query(
        grouping.label('period'),
        Project.name.label('project_name'),
        func.sum(
            func.timestampdiff(text('MINUTE'), LogEntry.start_time, LogEntry.end_time)
            - func.coalesce(
                func.timestampdiff(text('MINUTE'), LogEntry.pause_start, LogEntry.pause_end), 0
            )
        ).label('total_minutes')
    ).join(
        Project, Project.id == LogEntry.project_id
    ).filter(
        LogEntry.user_id == current_user.id,
        LogEntry.end_time.isnot(None)
    )
    
    # Aplikace filtrů na agregovaný dotaz
    if project_id != 'all':
        raw_data = raw_data.filter(LogEntry.project_id == int(project_id))
    if start_date:
        raw_data = raw_data.filter(LogEntry.start_time >= datetime.fromisoformat(start_date))
    if end_date:
        end_dt = datetime.fromisoformat(end_date) + relativedelta(days=1)
        raw_data = raw_data.filter(LogEntry.start_time < end_dt)
    
    raw_data = raw_data.group_by(grouping, Project.name).all()

    # Pivot data pro graf
    pivot = {}
    proj_names = set()
    
    for per, name, minutes in raw_data:
        key = label_fmt(per)
        if key:  # Přeskočit prázdné klíče
            hours = float(minutes or 0) / 60.0
            pivot.setdefault(key, {})[name] = round(hours, 2)
            proj_names.add(name)
    
    # Připravit data pro Chart.js
    labels = sorted(pivot.keys())
    datasets = []
    colors = [
        "rgba(54, 162, 235, 0.5)",
        "rgba(255, 99, 132, 0.5)",
        "rgba(255, 206, 86, 0.5)",
        "rgba(75, 192, 192, 0.5)",
        "rgba(153, 102, 255, 0.5)"
    ]
    
    for i, name in enumerate(sorted(proj_names)):
        dataset = {
            "label": name,
            "data": [pivot.get(l, {}).get(name, 0) for l in labels],
            "backgroundColor": colors[i % len(colors)],
            "borderColor": colors[i % len(colors)].replace('0.5', '1'),
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
        projects=projects,
        project_id=project_id,
        start_date=start_date,
        end_date=end_date,
        chart_data=chart_data,
        data_exists=bool(datasets and any(sum(d['data']) > 0 for d in datasets))
    )

@app.route('/export/csv')
@login_required
def export_csv():
    """Export do CSV."""
    project_id = request.args.get('project_id')
    month = request.args.get('month')
    selected_columns = request.args.getlist('columns')
    
    if not selected_columns:
        selected_columns = [col[0] for col in ALL_COLUMNS]
    
    query = LogEntry.query.filter_by(user_id=current_user.id)
    
    if project_id and project_id.lower() != 'all':
        query = query.filter(LogEntry.project_id == int(project_id))
    
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
    project_id = request.args.get('project_id')
    month = request.args.get('month')
    selected_columns = request.args.getlist('columns')
    
    if not selected_columns:
        selected_columns = ['id', 'project', 'start_time', 'end_time', 'note', 'hours']

    query = LogEntry.query.filter_by(user_id=current_user.id)
    
    if project_id and project_id.lower() != 'all':
        query = query.filter(LogEntry.project_id == int(project_id))
    
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
    projects = Project.query.filter_by(user_id=current_user.id).all()
    return render_template('templates.html', templates=templates, projects=projects)

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
