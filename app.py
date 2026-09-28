import datetime
import html
import os
import secrets
import sqlite3
from functools import wraps

import bcrypt
import jwt
from flask import Flask, g, jsonify, request

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.db")
JWT_ALGO = "HS256"


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
        """
    )
    count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if count == 0:
        login_name = os.environ["SEED_LOGIN"]
        password = os.environ["SEED_PASSWORD"]
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        db.execute(
            "INSERT INTO users (login, password_hash) VALUES (?, ?)",
            (login_name, password_hash),
        )
    db.commit()
    db.close()


def require_auth(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        parts = header.split()
        if len(parts) != 2 or parts[0] != "Bearer":
            return jsonify({"error": "unauthorized"}), 401
        try:
            jwt.decode(parts[1], os.environ["JWT_SECRET"], algorithms=[JWT_ALGO])
        except jwt.PyJWTError:
            return jsonify({"error": "unauthorized"}), 401
        return view(*args, **kwargs)

    return wrapped


@app.post("/auth/login")
def login():
    body = request.get_json(silent=True) or {}
    login_name = body.get("login")
    password = body.get("password")
    if not isinstance(login_name, str) or not isinstance(password, str):
        return jsonify({"error": "unauthorized"}), 401

    row = get_db().execute(
        "SELECT login, password_hash FROM users WHERE login = ?",
        (login_name,),
    ).fetchone()
    if row is None or not bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
        return jsonify({"error": "unauthorized"}), 401

    token = jwt.encode(
        {
            "sub": row["login"],
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1),
        },
        os.environ["JWT_SECRET"],
        algorithm=JWT_ALGO,
    )
    return jsonify({"token": token})


@app.get("/api/data")
@require_auth
def data():
    rows = get_db().execute("SELECT id, login FROM users").fetchall()
    users = [{"id": row["id"], "login": html.escape(row["login"])} for row in rows]
    return jsonify({"users": users})


@app.get("/dice")
def dice():
    return jsonify({"result": secrets.randbelow(6) + 1})


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000)
