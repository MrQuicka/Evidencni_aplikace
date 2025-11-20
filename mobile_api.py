"""
REST API Blueprint pro mobilní aplikaci
"""
from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from models import db, User, Project, LogEntry
from auth_api import generate_jwt_token, jwt_required
from fakturoid_client import FakturoidClient

mobile_bp = Blueprint('mobile_api', __name__, url_prefix='/api/mobile')


# ========== AUTENTIZACE ==========

@mobile_bp.route('/auth/login', methods=['POST'])
def api_login():
    """
    Přihlášení uživatele - vrací JWT token

    Request body:
    {
        "username": "admin",
        "password": "heslo123"
    }

    Response:
    {
        "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "user_id": 1,
        "username": "admin"
    }
    """
    data = request.get_json()

    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Chybí username nebo password'}), 400

    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if user and check_password_hash(user.password, password):
        token = generate_jwt_token(user.id)
        return jsonify({
            'token': token,
            'user_id': user.id,
            'username': user.username
        }), 200
    else:
        return jsonify({'error': 'Neplatné přihlašovací údaje'}), 401


@mobile_bp.route('/auth/register', methods=['POST'])
def api_register():
    """
    Registrace nového uživatele

    Request body:
    {
        "username": "novyuzivatel",
        "password": "heslo123"
    }
    """
    data = request.get_json()

    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Chybí username nebo password'}), 400

    username = data.get('username')
    password = data.get('password')

    # Zkontrolovat, jestli uživatel již existuje
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Uživatel s tímto jménem již existuje'}), 409

    # Vytvořit nového uživatele
    new_user = User(
        username=username,
        password=generate_password_hash(password)
    )
    db.session.add(new_user)
    db.session.commit()

    # Vygenerovat token
    token = generate_jwt_token(new_user.id)

    return jsonify({
        'token': token,
        'user_id': new_user.id,
        'username': new_user.username
    }), 201


def _calculate_hours(log: LogEntry) -> float:
    if not log.end_time:
        return 0

    duration = log.end_time - log.start_time

    if log.pause_start and log.pause_end:
        duration -= log.pause_end - log.pause_start

    return max(duration.total_seconds() / 3600, 0)


# ========== PROJEKTY ==========

@mobile_bp.route('/projects', methods=['GET'])
@jwt_required
def api_get_projects(current_user):
    """
    Získat všechny projekty aktuálního uživatele

    Response:
    {
        "projects": [
            {"id": 1, "name": "Projekt A", "user_id": 1},
            {"id": 2, "name": "Projekt B", "user_id": 1}
        ]
    }
    """
    projects = Project.query.filter_by(user_id=current_user.id).all()

    return jsonify({
        'projects': [
            {
                'id': p.id,
                'name': p.name,
                'user_id': p.user_id
            }
            for p in projects
        ]
    }), 200


@mobile_bp.route('/projects', methods=['POST'])
@jwt_required
def api_create_project(current_user):
    """
    Vytvořit nový projekt

    Request body:
    {
        "name": "Nový projekt"
    }
    """
    data = request.get_json()

    if not data or not data.get('name'):
        return jsonify({'error': 'Chybí název projektu'}), 400

    new_project = Project(
        name=data.get('name'),
        user_id=current_user.id
    )
    db.session.add(new_project)
    db.session.commit()

    return jsonify({
        'id': new_project.id,
        'name': new_project.name,
        'user_id': new_project.user_id
    }), 201


@mobile_bp.route('/projects/<int:project_id>', methods=['DELETE'])
@jwt_required
def api_delete_project(current_user, project_id):
    """
    Smazat projekt
    """
    project = Project.query.get(project_id)

    if not project:
        return jsonify({'error': 'Projekt nenalezen'}), 404

    if project.user_id != current_user.id:
        return jsonify({'error': 'Nemáte oprávnění smazat tento projekt'}), 403

    db.session.delete(project)
    db.session.commit()

    return jsonify({'message': 'Projekt smazán'}), 200


# ========== LOG ENTRIES (DOCHÁZKA) ==========

@mobile_bp.route('/logs', methods=['GET'])
@jwt_required
def api_get_logs(current_user):
    """
    Získat všechny záznamy docházky aktuálního uživatele

    Query parametry:
    - since: ISO timestamp - vrátí jen záznamy změněné po tomto datu (pro synchronizaci)
    - project_id: ID projektu - filtrovat podle projektu

    Response:
    {
        "logs": [
            {
                "id": 1,
                "project_id": 1,
                "project_name": "Projekt A",
                "start_time": "2025-10-28T08:00:00",
                "end_time": "2025-10-28T16:00:00",
                "pause_start": null,
                "pause_end": null,
                "note": "Pracovní den",
                "created_at": "2025-10-28T08:00:00",
                "updated_at": "2025-10-28T16:00:00"
            }
        ],
        "timestamp": "2025-10-28T18:00:00"
    }
    """
    query = LogEntry.query.filter_by(user_id=current_user.id)

    # Filtrování podle času (pro synchronizaci)
    since = request.args.get('since')
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            # Poznámka: Pro správnou synchronizaci bychom potřebovali updated_at sloupec
            # Zatím použijeme start_time jako náhradu
            query = query.filter(LogEntry.start_time >= since_dt)
        except ValueError:
            return jsonify({'error': 'Neplatný formát data'}), 400

    # Filtrování podle projektu
    project_id = request.args.get('project_id')
    if project_id:
        query = query.filter_by(project_id=int(project_id))

    logs = query.order_by(LogEntry.start_time.desc()).all()

    return jsonify({
        'logs': [
            {
                'id': log.id,
                'project_id': log.project_id,
                'project_name': log.project.name if log.project else None,
                'start_time': log.start_time.isoformat() if log.start_time else None,
                'end_time': log.end_time.isoformat() if log.end_time else None,
                'pause_start': log.pause_start.isoformat() if log.pause_start else None,
                'pause_end': log.pause_end.isoformat() if log.pause_end else None,
                'note': log.note
            }
            for log in logs
        ],
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@mobile_bp.route('/logs', methods=['POST'])
@jwt_required
def api_create_log(current_user):
    """
    Vytvořit nový záznam docházky

    Request body:
    {
        "project_id": 1,
        "start_time": "2025-10-28T08:00:00",
        "end_time": "2025-10-28T16:00:00",  // volitelné
        "pause_start": null,  // volitelné
        "pause_end": null,  // volitelné
        "note": "Pracovní den"  // volitelné
    }
    """
    data = request.get_json()

    if not data or not data.get('project_id'):
        return jsonify({'error': 'Chybí project_id'}), 400

    # Zkontrolovat, jestli projekt existuje a patří uživateli
    project = Project.query.get(data.get('project_id'))
    if not project or project.user_id != current_user.id:
        return jsonify({'error': 'Neplatný projekt'}), 400

    # Parsovat datetime
    try:
        start_time = datetime.fromisoformat(data.get('start_time').replace('Z', '+00:00')) if data.get('start_time') else datetime.utcnow()
        end_time = datetime.fromisoformat(data.get('end_time').replace('Z', '+00:00')) if data.get('end_time') else None
        pause_start = datetime.fromisoformat(data.get('pause_start').replace('Z', '+00:00')) if data.get('pause_start') else None
        pause_end = datetime.fromisoformat(data.get('pause_end').replace('Z', '+00:00')) if data.get('pause_end') else None
    except (ValueError, AttributeError) as e:
        return jsonify({'error': f'Neplatný formát data: {str(e)}'}), 400

    new_log = LogEntry(
        project_id=data.get('project_id'),
        user_id=current_user.id,
        start_time=start_time,
        end_time=end_time,
        pause_start=pause_start,
        pause_end=pause_end,
        note=data.get('note')
    )

    db.session.add(new_log)
    db.session.commit()

    return jsonify({
        'id': new_log.id,
        'project_id': new_log.project_id,
        'start_time': new_log.start_time.isoformat() if new_log.start_time else None,
        'end_time': new_log.end_time.isoformat() if new_log.end_time else None,
        'pause_start': new_log.pause_start.isoformat() if new_log.pause_start else None,
        'pause_end': new_log.pause_end.isoformat() if new_log.pause_end else None,
        'note': new_log.note
    }), 201


@mobile_bp.route('/logs/<int:log_id>', methods=['PUT'])
@jwt_required
def api_update_log(current_user, log_id):
    """
    Aktualizovat existující záznam docházky

    Request body: stejný jako u POST
    """
    log = LogEntry.query.get(log_id)

    if not log:
        return jsonify({'error': 'Záznam nenalezen'}), 404

    if log.user_id != current_user.id:
        return jsonify({'error': 'Nemáte oprávnění upravit tento záznam'}), 403

    data = request.get_json()

    # Aktualizovat pouze pokud je hodnota v requestu
    if 'project_id' in data:
        project = Project.query.get(data['project_id'])
        if not project or project.user_id != current_user.id:
            return jsonify({'error': 'Neplatný projekt'}), 400
        log.project_id = data['project_id']

    try:
        if 'start_time' in data:
            log.start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00')) if data['start_time'] else None
        if 'end_time' in data:
            log.end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00')) if data['end_time'] else None
        if 'pause_start' in data:
            log.pause_start = datetime.fromisoformat(data['pause_start'].replace('Z', '+00:00')) if data['pause_start'] else None
        if 'pause_end' in data:
            log.pause_end = datetime.fromisoformat(data['pause_end'].replace('Z', '+00:00')) if data['pause_end'] else None
        if 'note' in data:
            log.note = data['note']
    except (ValueError, AttributeError) as e:
        return jsonify({'error': f'Neplatný formát data: {str(e)}'}), 400

    db.session.commit()

    return jsonify({
        'id': log.id,
        'project_id': log.project_id,
        'start_time': log.start_time.isoformat() if log.start_time else None,
        'end_time': log.end_time.isoformat() if log.end_time else None,
        'pause_start': log.pause_start.isoformat() if log.pause_start else None,
        'pause_end': log.pause_end.isoformat() if log.pause_end else None,
        'note': log.note
    }), 200


@mobile_bp.route('/logs/<int:log_id>', methods=['DELETE'])
@jwt_required
def api_delete_log(current_user, log_id):
    """
    Smazat záznam docházky
    """
    log = LogEntry.query.get(log_id)

    if not log:
        return jsonify({'error': 'Záznam nenalezen'}), 404

    if log.user_id != current_user.id:
        return jsonify({'error': 'Nemáte oprávnění smazat tento záznam'}), 403

    db.session.delete(log)
    db.session.commit()

    return jsonify({'message': 'Záznam smazán'}), 200


# ========== AKTIVNÍ ČINNOST ==========

@mobile_bp.route('/logs/active', methods=['GET'])
@jwt_required
def api_get_active_log(current_user):
    """
    Získat aktuálně aktivní činnost (záznam bez end_time)

    Response:
    {
        "active_log": {...} nebo null
    }
    """
    active_log = LogEntry.query.filter_by(
        user_id=current_user.id,
        end_time=None
    ).first()

    if active_log:
        return jsonify({
            'active_log': {
                'id': active_log.id,
                'project_id': active_log.project_id,
                'project_name': active_log.project.name if active_log.project else None,
                'start_time': active_log.start_time.isoformat() if active_log.start_time else None,
                'pause_start': active_log.pause_start.isoformat() if active_log.pause_start else None,
                'pause_end': active_log.pause_end.isoformat() if active_log.pause_end else None,
                'note': active_log.note
            }
        }), 200
    else:
        return jsonify({'active_log': None}), 200


@mobile_bp.route('/logs/start', methods=['POST'])
@jwt_required
def api_start_work(current_user):
    """
    Rychlý start práce na projektu

    Request body:
    {
        "project_id": 1,
        "note": "volitelná poznámka"
    }
    """
    data = request.get_json()

    if not data or not data.get('project_id'):
        return jsonify({'error': 'Chybí project_id'}), 400

    # Zkontrolovat, jestli už nějaká činnost neběží
    active_log = LogEntry.query.filter_by(
        user_id=current_user.id,
        end_time=None
    ).first()

    if active_log:
        return jsonify({'error': 'Již běží jiná činnost'}), 409

    # Zkontrolovat projekt
    project = Project.query.get(data.get('project_id'))
    if not project or project.user_id != current_user.id:
        return jsonify({'error': 'Neplatný projekt'}), 400

    new_log = LogEntry(
        project_id=data.get('project_id'),
        user_id=current_user.id,
        start_time=datetime.utcnow(),
        note=data.get('note')
    )

    db.session.add(new_log)
    db.session.commit()

    return jsonify({
        'id': new_log.id,
        'project_id': new_log.project_id,
        'start_time': new_log.start_time.isoformat()
    }), 201


@mobile_bp.route('/logs/stop', methods=['POST'])
@jwt_required
def api_stop_work(current_user):
    """
    Ukončit aktuálně běžící činnost
    """
    active_log = LogEntry.query.filter_by(
        user_id=current_user.id,
        end_time=None
    ).first()

    if not active_log:
        return jsonify({'error': 'Žádná aktivní činnost'}), 404

    active_log.end_time = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'id': active_log.id,
        'end_time': active_log.end_time.isoformat()
    }), 200


# ========== SYNCHRONIZACE ==========

@mobile_bp.route('/sync/status', methods=['GET'])
@jwt_required
def api_sync_status(current_user):
    """
    Jednoduchý endpoint pro kontrolu spojení a stavu serveru
    """
    return jsonify({
        'status': 'ok',
        'server_time': datetime.utcnow().isoformat(),
        'user_id': current_user.id
    }), 200


# ========== FAKTUROID INTEGRACE ==========


@mobile_bp.route('/invoices/fakturoid', methods=['POST'])
@jwt_required
def api_create_fakturoid_invoice(current_user):
    """
    Vytvoří fakturu ve Fakturoidu na základě odpracovaných hodin.

    Request body:
    {
        "project_id": 1,
        "subject_id": 123456,
        "rate_per_hour": 1200.0,
        "vat_rate": 21,               // volitelné, default 21
        "from": "2024-01-01",        // volitelné, ISO datum
        "to": "2024-01-31",          // volitelné, ISO datum
        "description": "Práce leden", // volitelné
        "note": "Poznámka",           // volitelné
        "due_days": 14                // volitelné
    }
    """

    data = request.get_json() or {}

    required_fields = ['project_id', 'subject_id', 'rate_per_hour']
    missing = [field for field in required_fields if field not in data]
    if missing:
        return jsonify({'error': f"Chybějící pole: {', '.join(missing)}"}), 400

    project = Project.query.get(data['project_id'])
    if not project or project.user_id != current_user.id:
        return jsonify({'error': 'Neplatný projekt'}), 400

    query = LogEntry.query.filter_by(project_id=project.id, user_id=current_user.id)

    for key, comparator in [('from', LogEntry.start_time.__ge__), ('to', LogEntry.start_time.__le__)]:
        if data.get(key):
            try:
                dt = datetime.fromisoformat(data[key])
                query = query.filter(comparator(dt))
            except ValueError:
                return jsonify({'error': f'Neplatné datum v poli {key}'}), 400

    logs = query.all()
    if not logs:
        return jsonify({'error': 'Žádné záznamy pro fakturaci'}), 400

    total_hours = sum(_calculate_hours(log) for log in logs)
    if total_hours <= 0:
        return jsonify({'error': 'Nejsou dostupné ukončené záznamy s časem'}), 400

    try:
        client = FakturoidClient.from_env()
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 500

    description = data.get('description') or f"Práce na projektu {project.name}"
    vat_rate = int(data.get('vat_rate', 21))
    lines = client.build_lines_from_hours(
        description=description,
        total_hours=total_hours,
        rate_per_hour=float(data['rate_per_hour']),
        vat_rate=vat_rate,
    )

    payload = {
        'subject_id': data['subject_id'],
        'lines': lines,
        'due': data.get('due_days', 14),
        'note': data.get('note', ''),
    }

    for optional_field in ['issued_on', 'number']:
        if data.get(optional_field):
            payload[optional_field] = data[optional_field]

    invoice = client.create_invoice(payload)

    return jsonify({
        'invoice': invoice,
        'total_hours': round(total_hours, 2),
        'lines': lines
    }), 201
