"""Create the local helpdesk database and app account without saving root credentials."""
import getpass
import os
import re
from pathlib import Path

import mysql.connector


def load_local_env():
    for line in Path(__file__).with_name('.env').read_text(encoding='utf-8').splitlines():
        match = re.match(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$', line)
        if match and match.group(1) not in os.environ:
            os.environ[match.group(1)] = match.group(2).strip('"\'')


def quote_sql(value):
    return "'" + value.replace('\\', '\\\\').replace("'", "''") + "'"


def main():
    load_local_env()
    database = os.getenv('MYSQL_DATABASE', 'smart_it_helpdesk')
    app_user = os.getenv('MYSQL_USER', 'helpdesk_app')
    app_password = os.getenv('MYSQL_PASSWORD', '')
    if not app_password or database != 'smart_it_helpdesk' or app_user != 'helpdesk_app':
        raise SystemExit('Set MYSQL_DATABASE=smart_it_helpdesk, MYSQL_USER=helpdesk_app, and MYSQL_PASSWORD in .env first.')

    root_password = getpass.getpass('MySQL root password (entered locally, not saved): ')
    host = os.getenv('MYSQL_HOST', '127.0.0.1')
    port = int(os.getenv('MYSQL_PORT', '3306'))
    try:
        connection = mysql.connector.connect(
            host=host,
            port=port,
            user='root',
            password=root_password,
        )
    except mysql.connector.Error as error:
        if error.errno == 1045:
            raise SystemExit(
                f'MySQL rejected the root password for {host}:{port}. '
                'Use the administrator password for this exact MySQL server; it is separate from MYSQL_PASSWORD in .env.'
            ) from None
        raise
    cursor = connection.cursor()
    try:
        cursor.execute(f'CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
        cursor.execute(
            f'CREATE USER IF NOT EXISTS {quote_sql(app_user)}@{quote_sql("127.0.0.1")} IDENTIFIED BY {quote_sql(app_password)}'
        )
        cursor.execute(
            f'ALTER USER {quote_sql(app_user)}@{quote_sql("127.0.0.1")} IDENTIFIED BY {quote_sql(app_password)}'
        )
        cursor.execute(
            f'GRANT ALL PRIVILEGES ON `{database}`.* TO {quote_sql(app_user)}@{quote_sql("127.0.0.1")}'
        )
        connection.commit()
        cursor.execute(f'USE `{database}`')
        schema = Path(__file__).with_name('schema.sql').read_text(encoding='utf-8')
        statements = [part.strip() for part in schema.split(';') if part.strip()]
        for statement in statements:
            if statement.upper().startswith('CREATE DATABASE') or statement.upper().startswith('USE '):
                continue
            cursor.execute(statement)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
    print('Database, tables, and least-scoped application user are ready.')


if __name__ == '__main__':
    main()
