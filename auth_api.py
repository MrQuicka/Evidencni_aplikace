"""
JWT autentizace a pomocné funkce pro REST API
"""
import jwt
import os
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from models import User

# Tajný klíč pro JWT (v produkci by měl být v environment variables)
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'super-tajny-jwt-klic-zmenit-v-produkci')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24 * 7  # Token platný 7 dní


def generate_jwt_token(user_id):
    """
    Vygeneruje JWT token pro uživatele
    """
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def decode_jwt_token(token):
    """
    Dekóduje JWT token a vrátí user_id
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None  # Token vypršel
    except jwt.InvalidTokenError:
        return None  # Neplatný token


def jwt_required(f):
    """
    Dekorátor pro ověření JWT tokenu v API endpointech
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None

        # Token je v Authorization headeru ve formátu: "Bearer <token>"
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # Získat token za "Bearer "
            except IndexError:
                return jsonify({'error': 'Neplatný formát Authorization headeru'}), 401

        if not token:
            return jsonify({'error': 'Token chybí'}), 401

        user_id = decode_jwt_token(token)
        if user_id is None:
            return jsonify({'error': 'Neplatný nebo vypršelý token'}), 401

        # Najít uživatele v databázi
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'Uživatel nenalezen'}), 401

        # Předat uživatele do route funkce
        return f(current_user=user, *args, **kwargs)

    return decorated_function
