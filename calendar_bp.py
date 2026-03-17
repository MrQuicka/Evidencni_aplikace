from flask import Blueprint, jsonify, request, abort
from flask_login import login_required, current_user
from models import db, LogEntry, Projekt, Zakazka
from datetime import datetime

bp = Blueprint('calendar_api', __name__, url_prefix='/api')

def to_local_str(dt):
    """
    Vrací ISO string nebo None, pokud dt je None.
    """
    return dt.isoformat() if dt else None

@bp.route('/logs', methods=['GET'])
@login_required
def get_logs():
    entries = LogEntry.query.filter_by(user_id=current_user.id).all()
    events = []
    for e in entries:
        projekt = e.project
        projekt_name = projekt.name if projekt else '—'
        zakazka = projekt.zakazka if projekt else None
        zakazka_name = zakazka.name if zakazka else '—'
        projekt_color = projekt.color if projekt else '#28a745'

        # Krátký title: jen poznámka, nebo název projektu jako fallback
        if e.note:
            title = e.note
        else:
            title = projekt_name

        events.append({
            'id': e.id,
            'title': title,
            'project_id': e.project_id,
            'projekt_name': projekt_name,
            'zakazka_name': zakazka_name,
            'color': projekt_color,
            'start': to_local_str(e.start_time),
            'end':   to_local_str(e.end_time),
            'note':  e.note
        })
    return jsonify(events)

@bp.route('/logs', methods=['POST'])
@login_required
def create_log():
    data = request.get_json()
    e = LogEntry(
      user_id=current_user.id,
      project_id = data['project_id'],
      start_time = datetime.fromisoformat(data['start']),
      end_time   = datetime.fromisoformat(data['end']),
      note       = data.get('note')
    )
    db.session.add(e)
    db.session.commit()
    return jsonify({'id': e.id}), 201

@bp.route('/logs/<int:id>', methods=['PUT'])
@login_required
def update_log(id):
    e = LogEntry.query.get_or_404(id)
    if e.user_id != current_user.id:
        abort(403)
    data = request.get_json()
    e.project_id = data['project_id']
    e.start_time = datetime.fromisoformat(data['start'])
    e.end_time   = datetime.fromisoformat(data['end'])
    e.note       = data.get('note')
    db.session.commit()
    return jsonify({'status':'ok'})

@bp.route('/logs/<int:id>', methods=['DELETE'])
@login_required
def delete_log(id):
    e = LogEntry.query.get_or_404(id)
    if e.user_id != current_user.id:
        abort(403)
    db.session.delete(e)
    db.session.commit()
    return jsonify({'status':'deleted'})
