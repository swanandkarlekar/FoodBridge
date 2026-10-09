import os
import sqlite3
from flask import g, current_app

def get_db():
    """Get or create SQLite database connection for the current request."""
    if 'db' not in g:
        db_path = current_app.config['DATABASE']
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        g.db = sqlite3.connect(db_path)
        # Enable column access by name
        g.db.row_factory = sqlite3.Row
        # Enable foreign key constraint enforcement
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db

def close_db(e=None):
    """Close the database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    """Execute a read query and return row results."""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=(), commit=True):
    """Execute an INSERT, UPDATE, or DELETE query and optionally commit."""
    db = get_db()
    cur = db.execute(query, args)
    if commit:
        db.commit()
    last_id = cur.lastrowid
    cur.close()
    return last_id

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('donor', 'ngo', 'volunteer', 'admin')),
    organization TEXT,
    phone TEXT,
    address TEXT,
    city TEXT DEFAULT 'Metropolis',
    is_admin INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

CREATE TABLE IF NOT EXISTS donations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    donor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    quantity TEXT NOT NULL,
    servings INTEGER NOT NULL DEFAULT 1,
    address TEXT NOT NULL,
    city TEXT NOT NULL,
    pickup_deadline TEXT NOT NULL,
    prepared_time TEXT,
    allergens TEXT,
    donor_contact TEXT,
    instructions TEXT,
    status TEXT NOT NULL DEFAULT 'available' CHECK(status IN ('available', 'reserved', 'collected', 'cancelled', 'expired')),
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_donations_status ON donations(status);
CREATE INDEX IF NOT EXISTS idx_donations_category ON donations(category);
CREATE INDEX IF NOT EXISTS idx_donations_city ON donations(city);
CREATE INDEX IF NOT EXISTS idx_donations_donor ON donations(donor_id);

CREATE TABLE IF NOT EXISTS donation_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    donation_id INTEGER NOT NULL REFERENCES donations(id) ON DELETE CASCADE,
    ngo_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    servings_requested INTEGER NOT NULL DEFAULT 1,
    message TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected', 'cancelled', 'collected')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(donation_id, ngo_id, status)
);

CREATE INDEX IF NOT EXISTS idx_requests_donation ON donation_requests(donation_id);
CREATE INDEX IF NOT EXISTS idx_requests_ngo ON donation_requests(ngo_id);
CREATE INDEX IF NOT EXISTS idx_requests_status ON donation_requests(status);

CREATE TABLE IF NOT EXISTS volunteer_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    donation_id INTEGER NOT NULL REFERENCES donations(id) ON DELETE CASCADE,
    volunteer_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'available' CHECK(status IN ('available', 'assigned', 'in_transit', 'delivered')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS contact_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    subject TEXT NOT NULL,
    category TEXT NOT NULL,
    message TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

def init_db(app=None):
    """Initialize the SQLite database schema without dropping existing tables."""
    if app:
        with app.app_context():
            db = get_db()
            db.executescript(SCHEMA_SQL)
            db.commit()
    else:
        db = get_db()
        db.executescript(SCHEMA_SQL)
        db.commit()
