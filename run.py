from app import app, db
from models import User
from werkzeug.security import generate_password_hash

if __name__ == '__main__':
    with app.app_context():
        # Inicializace DB
        try:
            db.create_all()
            if not User.query.filter_by(username='admin').first():
                user = User(username='admin', password=generate_password_hash('admin'))
                db.session.add(user)
                db.session.commit()
                print("Admin user created")
        except Exception as e:
            print(f"DB init error: {e}")
    
    print("Starting Flask app on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
