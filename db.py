import sqlite3
from contextlib import closing

DB_PATH = "election.db"

def init_db():
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY,
            finger_id INTEGER UNIQUE,
            name TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS parties(
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS votes(
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            party_id INTEGER NOT NULL,
            voted_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(party_id) REFERENCES parties(id)
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS audit(
            id INTEGER PRIMARY KEY,
            event TEXT NOT NULL,
            info TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        con.commit()

def add_audit(event, info=""):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("INSERT INTO audit(event, info) VALUES(?,?)", (event, info))
        con.commit()

def get_user_by_finger(finger_id):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute("SELECT id, name, is_admin FROM users WHERE finger_id=?", (finger_id,))
        row = cur.fetchone()
        return row  # (id, name, is_admin) or None

def create_user(name, finger_id, is_admin=0):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("INSERT INTO users(name, finger_id, is_admin) VALUES(?,?,?)", (name, finger_id, is_admin))
        con.commit()
        add_audit("create_user", f"{name} finger_id={finger_id} admin={is_admin}")

def delete_user_by_finger(finger_id):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("DELETE FROM users WHERE finger_id=?", (finger_id,))
        con.commit()
        add_audit("delete_user", f"finger_id={finger_id}")

def list_parties():
    with sqlite3.connect(DB_PATH) as con:
        return con.execute("SELECT id, name FROM parties ORDER BY name").fetchall()

def add_party(name):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("INSERT INTO parties(name) VALUES(?)", (name,))
        con.commit()
        add_audit("add_party", name)

def update_party(party_id, name):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("UPDATE parties SET name=? WHERE id=?", (name, party_id))
        con.commit()
        add_audit("update_party", f"{party_id}->{name}")

def delete_party(party_id):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("DELETE FROM parties WHERE id=?", (party_id,))
        con.commit()
        add_audit("delete_party", str(party_id))

def vote_once(user_id, party_id):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        try:
            cur.execute("INSERT INTO votes(user_id, party_id) VALUES(?,?)", (user_id, party_id))
            con.commit()
            add_audit("vote_cast", f"user={user_id} party={party_id}")
            return True
        except sqlite3.IntegrityError as e:
            return False

def get_results():
    with sqlite3.connect(DB_PATH) as con:
        return con.execute("""
            SELECT p.name, COUNT(v.id) as votes
            FROM parties p
            LEFT JOIN votes v ON p.id = v.party_id
            GROUP BY p.id
            ORDER BY votes DESC, p.name
        """).fetchall()
