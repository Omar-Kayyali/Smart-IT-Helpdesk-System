# Smart IT Helpdesk

A MySQL backed helpdesk for employees to submit and track IT requests and for IT Support to review all submitted tickets. This repository is being built in assessment milestones; this first milestone covers sign-in, roles, ticket submission, and ticket viewing.

## Technology

- Python with Flask
- MySQL 8+ with `mysql-connector-python`
- HTML, CSS, and browser JavaScript

## Architecture

The Flask server serves the browser app from `public/` and exposes JSON endpoints under `/api`. It validates ticket input and enforces role and ownership checks on the server. MySQL stores users and tickets. Passwords use Python's scrypt password hashing. Flask's signed session cookie stores the user's ID; each authenticated API request reloads the user's current role from MySQL.

## Setup

1. Install Python 3.10 or later and MySQL 8 or later.
2. Create a virtual environment and install the Python dependencies:

   Windows PowerShell:

   ```powershell
   py -3 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

   If `py` is unavailable, use the Python install path, for example `& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m venv .venv`. macOS/Linux: `python3 -m venv .venv`, then `.venv/bin/python -m pip install -r requirements.txt`.

3. Copy `.env.example` to `.env` and set the MySQL connection values and a long random `SESSION_SECRET`. If your MySQL server uses a non-default port, set `MYSQL_PORT` accordingly.
4. Run the setup script. It asks for the MySQL root password in the terminal without saving it, creates the database and limited app user, and installs the schema:

   ```sh
   .\.venv\Scripts\python.exe setup_database.py
   ```

5. Seed the two local demo accounts and start Flask:

   ```sh
   .\.venv\Scripts\python.exe seed_users.py
   .\.venv\Scripts\python.exe app.py
   ```

6. Open <http://localhost:3000>.

## Environment variables

`MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`, `SESSION_SECRET`, and `PORT` are read from `.env` or the process environment. Do not commit `.env` or place real credentials in source control. Flask uses a local fallback session secret for development; set a unique, long `SESSION_SECRET` in `.env`.

## Demo users

The seed command creates or resets these local assessment accounts:

| Role | Email | Password |
| --- | --- | --- |
| Employee | `sara@example.com` | `Employee123!` |
| IT Support | `omar@example.com` | `Support123!` |

These credentials are only for local assessment use. Change them before any shared deployment.

## Day 1 scope

- Employee and IT Support sign in.
- Employees create tickets and can list/open only their own tickets.
- IT Support can list/open all submitted tickets.
- Ticket creation validates title, description, category, and priority in the backend.
- The landing view shows basic ticket totals and recent requests.

## Current limitations

- The signed session cookie expires after eight hours. Use HTTPS and a strong `SESSION_SECRET` for deployment.
- Ticket assignment, updates, comments, activity history, AI suggestions, search, workflow controls, and the final dashboard chart are later assessment milestones.
