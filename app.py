import hashlib
import hmac
import os
import re
from datetime import timedelta
from pathlib import Path

import mysql.connector
from flask import Flask, g, jsonify, request, send_from_directory, session
from werkzeug.exceptions import HTTPException


def load_local_env():
    """Load .env values for local development; real process variables take precedence."""
    env_path = Path(__file__).with_name('.env')
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding='utf-8').splitlines():
        match = re.match(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$', line)
        if match and match.group(1) not in os.environ:
            os.environ[match.group(1)] = match.group(2).strip('"\'')


load_local_env()

app = Flask(__name__, static_folder='public', static_url_path='')
app.config.update(
    SECRET_KEY=os.getenv('SESSION_SECRET', 'local-development-secret-change-this'),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE', 'false').lower() == 'true',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    MAX_CONTENT_LENGTH=32 * 1024,
)

DB_CONFIG = dict(
    host=os.getenv('MYSQL_HOST', '127.0.0.1'),
    port=int(os.getenv('MYSQL_PORT', '3306')),
    user=os.getenv('MYSQL_USER', 'helpdesk_app'),
    password=os.getenv('MYSQL_PASSWORD', ''),
    database=os.getenv('MYSQL_DATABASE', 'smart_it_helpdesk'),
    autocommit=False,
)

CATEGORIES = {'Hardware', 'Software', 'Network', 'Email', 'Access Issue', 'Other'}
PRIORITIES = {'Low', 'Medium', 'High', 'Critical'}


def db_connection():
    return mysql.connector.connect(**DB_CONFIG)


def user_public(row):
    return {'id': row['id'], 'name': row['name'], 'email': row['email'], 'role': row['role']}


@app.before_request
def load_authenticated_user():
    g.user = None
    if not request.path.startswith('/api/') or request.path in {'/api/login', '/api/logout'}:
        return
    user_id = session.get('user_id')
    if not user_id:
        return
    connection = db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute('SELECT id, name, email, role FROM users WHERE id = %s', (user_id,))
        g.user = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()


def require_user():
    if not g.user:
        return jsonify(error='Please sign in to continue.'), 401
    return None


@app.post('/api/login')
def login():
    body = request.get_json(silent=True) or {}
    email = str(body.get('email', '')).strip().lower()
    password = str(body.get('password', ''))
    if not email or not password:
        return jsonify(error='Enter your email and password.'), 400

    connection = db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute('SELECT id, name, email, password_hash, role FROM users WHERE email = %s', (email,))
        row = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()

    if not row:
        return jsonify(error='Email or password is incorrect.'), 401
    try:
        salt, stored_hash = row['password_hash'].split(':', 1)
        candidate = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1, dklen=64).hex()
    except (ValueError, TypeError):
        return jsonify(error='Email or password is incorrect.'), 401
    if not hmac.compare_digest(candidate, stored_hash):
        return jsonify(error='Email or password is incorrect.'), 401

    session.clear()
    session.permanent = True
    session['user_id'] = row['id']
    return jsonify(user=user_public(row))


@app.post('/api/logout')
def logout():
    session.clear()
    return jsonify(ok=True)


@app.get('/api/me')
def me():
    error = require_user()
    if error:
        return error
    return jsonify(user=user_public(g.user))


@app.get('/api/tickets')
def list_tickets():
    error = require_user()
    if error:
        return error
    is_support = g.user['role'] == 'support'
    query = '''SELECT t.id, t.title, t.description, t.category, t.priority, t.status,
                      t.created_at, t.updated_at, creator.name AS created_by_name,
                      assignee.name AS assigned_to_name
               FROM tickets t JOIN users creator ON creator.id = t.created_by
               LEFT JOIN users assignee ON assignee.id = t.assigned_to'''
    params = ()
    if not is_support:
        query += ' WHERE t.created_by = %s'
        params = (g.user['id'],)
    query += ' ORDER BY t.created_at DESC'

    connection = db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        tickets = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    for ticket in tickets:
        ticket['created_at'] = ticket['created_at'].isoformat()
        ticket['updated_at'] = ticket['updated_at'].isoformat()
    metrics = {
        'total': len(tickets),
        'open': sum(t['status'] == 'Open' for t in tickets),
        'inProgress': sum(t['status'] == 'In Progress' for t in tickets),
        'resolved': sum(t['status'] == 'Resolved' for t in tickets),
        'closed': sum(t['status'] == 'Closed' for t in tickets),
        'critical': sum(t['priority'] == 'Critical' for t in tickets),
    }
    return jsonify(tickets=tickets, metrics=metrics)


@app.post('/api/tickets')
def create_ticket():
    error = require_user()
    if error:
        return error
    if g.user['role'] != 'employee':
        return jsonify(error='Only employees can submit a ticket.'), 403
    body = request.get_json(silent=True) or {}
    title = str(body.get('title', '')).strip()
    description = str(body.get('description', '')).strip()
    category = str(body.get('category', ''))
    priority = str(body.get('priority', 'Medium'))
    if not title or len(title) > 160:
        return jsonify(error='Title is required and must be 160 characters or fewer.'), 400
    if not description:
        return jsonify(error='Description is required.'), 400
    if category not in CATEGORIES:
        return jsonify(error='Choose a valid category.'), 400
    if priority not in PRIORITIES:
        return jsonify(error='Choose a valid priority.'), 400

    connection = db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            'INSERT INTO tickets (title, description, category, priority, created_by) VALUES (%s, %s, %s, %s, %s)',
            (title, description, category, priority, g.user['id']),
        )
        ticket_id = cursor.lastrowid
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
    return jsonify(id=ticket_id), 201


@app.get('/api/tickets/<int:ticket_id>')
def ticket_detail(ticket_id):
    error = require_user()
    if error:
        return error
    connection = db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            '''SELECT t.id, t.title, t.description, t.category, t.priority, t.status,
                      t.created_at, t.updated_at, creator.name AS created_by_name,
                      t.created_by, assignee.name AS assigned_to_name
               FROM tickets t JOIN users creator ON creator.id = t.created_by
               LEFT JOIN users assignee ON assignee.id = t.assigned_to WHERE t.id = %s''',
            (ticket_id,),
        )
        ticket = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()
    if not ticket:
        return jsonify(error='Ticket not found.'), 404
    if g.user['role'] != 'support' and ticket['created_by'] != g.user['id']:
        return jsonify(error='You cannot access this ticket.'), 403
    ticket.pop('created_by')
    ticket['created_at'] = ticket['created_at'].isoformat()
    ticket['updated_at'] = ticket['updated_at'].isoformat()
    return jsonify(ticket=ticket)


@app.errorhandler(mysql.connector.Error)
def database_error(error):
    app.logger.exception('MySQL request failed: %s', error)
    return jsonify(error='The helpdesk database is unavailable. Check the server configuration and try again.'), 503


@app.errorhandler(HTTPException)
def http_error(error):
    if request.path.startswith('/api/'):
        return jsonify(error=error.description), error.code
    return error


@app.errorhandler(Exception)
def unexpected_error(error):
    app.logger.exception('Unexpected request error: %s', error)
    if request.path.startswith('/api/'):
        return jsonify(error='Something went wrong. Please try again.'), 500
    return 'Something went wrong. Please try again.', 500


@app.get('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.getenv('PORT', '3000')), debug=False)
