from flask import Flask, render_template, redirect, url_for, request, flash, Response
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import func, text
import json
import os
import csv
import io
import xlsxwriter
from dateutil.relativedelta import relativedelta  # pro posun v datech

# Import modelů – předpokládáme, že models.py obsahuje třídy User, Project, LogEntry
from models import db, User, Project, LogEntry

# Import kalendářového blueprintu
from calendar_bp import bp as calendar_bp


def parse_local_time(value):
    """
    Přijme string ve formátu "YYYY-MM-DDTHH:MM" a vrátí naive datetime.
    """
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
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI','mysql+pymysql://dochazka_user:dochazka_pass@db:3306/dochazka')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'supertajnyklic'

# Inicializace databáze a Flask-Login
db.init_app(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Import a registrace kalendářového Blueprintu
from calendar_bp import bp as calendar_bp
app.register_blueprint(calendar_bp)


# Inicializace Flask-Migrate
from flask_migrate import Migrate
migrate = Migrate(app, db)

#Registrace kalendářového blueprintu
#app.register_blueprint(calendar_bp)

# Načítání uživatele pro Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --------------------------------------------------
#                  ROUTY A FUNKCE
# --------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('projects'))
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
        project_id      = request.form.get('project_id')
        action          = request.form.get('action')
        note            = request.form.get('note')
        parsed_start    = parse_local_time(request.form.get('start_time'))
        parsed_end      = parse_local_time(request.form.get('end_time'))
        parsed_pause_s  = parse_local_time(request.form.get('pause_start_time'))
        parsed_pause_e  = parse_local_time(request.form.get('pause_end_time'))

        if not parsed_start and action == 'start':
            parsed_start = datetime.now(LOCAL_TZ).astimezone(UTC_TZ)

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
    user_logs = LogEntry.query.filter_by(user_id=current_user.id).order_by(LogEntry.start_time.desc()).all()
    logs_with_hours = []
    for log in user_logs:
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
    return render_template('logs.html', logs=logs_with_hours)

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
        log_entry.start_time  = parse_local_time(request.form.get('start_time')) or log_entry.start_time
        log_entry.end_time    = parse_local_time(request.form.get('end_time'))
        log_entry.pause_start = parse_local_time(request.form.get('pause_start_time'))
        log_entry.pause_end   = parse_local_time(request.form.get('pause_end_time'))
        log_entry.note        = request.form.get('note')
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
    # 1) Read incoming filters
    period     = request.args.get('period', 'monthly')
    project_id = request.args.get('project_id', 'all')
    start_date = request.args.get('start_date')
    end_date   = request.args.get('end_date')

    # 2) Load all user’s projects for the dropdown
    projects = Project.query.filter_by(user_id=current_user.id).all()

    # 3) Build base query
    query = LogEntry.query.join(Project).filter(LogEntry.user_id == current_user.id)
    if project_id != 'all':
        query = query.filter(LogEntry.project_id == int(project_id))
    if start_date:
        query = query.filter(LogEntry.start_time >= datetime.fromisoformat(start_date))
    if end_date:
        # add one day so “Do” is inclusive
        query = query.filter(LogEntry.start_time < datetime.fromisoformat(end_date) + relativedelta(days=1))

    # 4) Fetch raw_data exactly as before, but using `query` instead of LogEntry.query.filter_by
    if period == 'daily':
        grouping = func.date(LogEntry.start_time)
        label_fmt = lambda d: d.isoformat()
    elif period == 'weekly':
        grouping = func.yearweek(LogEntry.start_time)
        label_fmt = str
    else:  # monthly
        grouping = func.date_format(LogEntry.start_time, '%Y-%m')
        label_fmt = str

    raw_data = (
      db.session.query(
        grouping.label('period'),
        Project.name.label('project_name'),
        (func.sum(
            func.timestampdiff(text('MINUTE'), LogEntry.start_time, LogEntry.end_time)
            - func.coalesce(func.timestampdiff(text('MINUTE'),
                               LogEntry.pause_start, LogEntry.pause_end), 0)
         ) / 60.0).label('total_hours')
      )
      .join(Project, Project.id == LogEntry.project_id)
      .filter(LogEntry.user_id == current_user.id)
      .group_by(grouping, Project.name)
      .all()
    )

    # 5) Pivot + build chart_data same as before
    pivot = {}
    proj_names = set()
    for per, name, hrs in raw_data:
        key = label_fmt(per)
        pivot.setdefault(key, {})[name] = float(hrs or 0)
        proj_names.add(name)
    labels = sorted(pivot.keys())
    datasets = []
    colors = [ "rgba(54,162,235,0.5)", "rgba(255,99,132,0.5)", "rgba(255,206,86,0.5)" ]
    for i, name in enumerate(sorted(proj_names)):
        ds = {
          "label": name,
          "data": [ pivot[l].get(name, 0) for l in labels ],
          "backgroundColor": colors[i % len(colors)],
          "borderColor": colors[i % len(colors)].replace('0.5','1'),
          "borderWidth": 1
        }
        datasets.append(ds)
    chart_data = {"labels": labels, "datasets": datasets}

    # 6) Pass everything into the template
    return render_template(
      'reports.html',
      period=period,
      projects=projects,
      project_id=project_id,
      start_date=start_date,
      end_date=end_date,
      chart_data=chart_data,
      data_exists=bool(datasets)
    )


@app.route('/export/csv')
@login_required
def export_csv():
    # ... (původní export CSV) ...
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

    # Zde definujeme output, do kterého workbook zapisuje
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet("Dochazka")

    header_format = workbook.add_format({'bold': True, 'bg_color': '#DCE6F1'})
    # hlavičky
    headers = [label for key, label in ALL_COLUMNS if key in selected_columns]
    for col_idx, header in enumerate(headers):
        worksheet.write(0, col_idx, header, header_format)

    # IDENTIFIKUJEME index sloupce s "hours"
    hours_col = selected_columns.index('hours')

    total_hours_sum = 0.0
    row_idx = 1
    for log in user_logs:
        # vypočítáme odpracované hodiny
        minutes = 0
        if log.start_time and log.end_time:
            minutes = (log.end_time - log.start_time).total_seconds() / 60.0
        if log.pause_start and log.pause_end:
            minutes -= (log.pause_end - log.pause_start).total_seconds() / 60.0
        hours = round(minutes / 60.0, 2)
        total_hours_sum += hours

        # data řádku
        data = []
        for key in selected_columns:
            if key == 'id':
                data.append(log.id)
            elif key == 'project':
                data.append(log.project.name if log.project else '')
            elif key == 'start_time':
                data.append(log.start_time)
            elif key == 'end_time':
                data.append(log.end_time)
            elif key == 'pause_start':
                data.append(log.pause_start)
            elif key == 'pause_end':
                data.append(log.pause_end)
            elif key == 'note':
                data.append(log.note or '')
            elif key == 'hours':
                data.append(hours)
        # zapíšeme řádek
        for col, val in enumerate(data):
            worksheet.write(row_idx, col, str(val))
        row_idx += 1

    # Přidáme na konec řádek se součtem hodin
    sum_format = workbook.add_format({'bold': True})
    worksheet.write(row_idx, 0, "Celkem hodin", sum_format)
    worksheet.write(row_idx, hours_col, total_hours_sum, sum_format)

    workbook.close()
    output.seek(0)

    return Response(
        output.read(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-disposition": "attachment; filename=dochazka_export.xlsx"}
    )


# --- Nová route pro kalendářové UI ---
@app.route('/calendar')
@login_required
def calendar_view():
    return render_template('calendar.html')

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

    # --------------------------------------------------
    #   Vypišme všechny zaregistrované routy
    # --------------------------------------------------
    print("=== URL MAP ===")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint:30s} -> {rule}")
    print("===============")

    app.run(host='0.0.0.0', debug=True)

