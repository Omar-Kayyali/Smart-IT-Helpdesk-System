import hashlib
import os
import re
import secrets
from pathlib import Path

import mysql.connector


def load_local_env():
    env_path = Path(__file__).with_name('.env')
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding='utf-8').splitlines():
        match = re.match(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$', line)
        if match and match.group(1) not in os.environ:
            os.environ[match.group(1)] = match.group(2).strip('"\'')


def password_hash(password):
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1, dklen=64).hex()
    return f'{salt}:{digest}'


def main():
    load_local_env()
    connection = mysql.connector.connect(
        host=os.getenv('MYSQL_HOST', '127.0.0.1'),
        port=int(os.getenv('MYSQL_PORT', '3306')),
        user=os.getenv('MYSQL_USER', 'helpdesk_app'),
        password=os.getenv('MYSQL_PASSWORD', ''),
        database=os.getenv('MYSQL_DATABASE', 'smart_it_helpdesk'),
    )
    cursor = connection.cursor()
    try:
        cursor.execute("SHOW TABLES LIKE 'users'")
        if cursor.fetchone() is None:
            raise SystemExit('The users table does not exist yet. Run setup_database.py successfully before seed_users.py.')
        demo_users = [
            ('Sara Employee', 'sara@example.com', 'Employee123!', 'employee'),
            ('Omar Support', 'omar@example.com', 'Support123!', 'support'),
        ]
        for name, email, password, role in demo_users:
            cursor.execute(
                '''INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE name=VALUES(name), password_hash=VALUES(password_hash), role=VALUES(role)''',
                (name, email, password_hash(password), role),
            )
        connection.commit()
    finally:
        cursor.close()
        connection.close()
    print('Demo users ready. Change these passwords before any shared deployment.')


if __name__ == '__main__':
    main()
