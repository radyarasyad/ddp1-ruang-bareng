"""Akses database. Modul ini hanya membaca dan menulis data.

Dua jenis database didukung:
- SQLite   : untuk laptop dan test (path file .db atau ":memory:")
- Postgres : untuk deploy di Vercel (alamat "postgresql://...", misalnya dari Neon)

Fungsi CRUD di bawah tidak perlu tahu database mana yang sedang dipakai.
Aturan bisnis (boleh join atau tidak, siapa yang boleh membatalkan)
ada di folder services/, bukan di sini.

Semua query memakai tanda tanya (?) sebagai tempat nilai. Driver database
yang memasukkan nilainya dengan aman, sehingga teks dari pengguna tidak bisa
mengubah perintah SQL (mencegah SQL injection).
"""

import os
import sqlite3
import uuid
from contextlib import contextmanager

from app.models import ENROLLMENT_ACTIVE, Enrollment, StudySession, User, now_wib

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")

# Nomor kunci bebas untuk pg_advisory_xact_lock (lihat transaction()).
ENROLLMENT_LOCK_ID = 2026


# ---------------------------------------------------------------------------
# Utilitas
# ---------------------------------------------------------------------------
def new_id():
    """ID acak 32 karakter, misalnya '3f9c...'. Sulit ditebak, tidak bisa bentrok."""
    return uuid.uuid4().hex


def now_text():
    """Waktu sekarang (WIB) sebagai teks ISO, misalnya '2026-12-01T14:00:05'."""
    return now_wib().isoformat(timespec="seconds")


def is_postgres_url(target):
    """True jika target adalah alamat Postgres, bukan path file SQLite."""
    return target.startswith(("postgres://", "postgresql://"))


def to_postgres_sql(sql):
    """Postgres memakai %s sebagai tempat nilai, SQLite memakai ?."""
    return sql.replace("?", "%s")


# ---------------------------------------------------------------------------
# Koneksi
# ---------------------------------------------------------------------------
class Database:
    """Pembungkus kecil supaya SQLite dan Postgres bisa dipakai dengan cara yang sama.

    Kode lain cukup memanggil db.execute(sql, params) dan db.close().
    """

    def __init__(self, raw_connection, kind):
        self.raw = raw_connection   # Koneksi asli dari sqlite3 atau psycopg
        self.kind = kind            # "sqlite" atau "postgres"

    def execute(self, sql, params=()):
        if self.kind == "postgres":
            return self.raw.execute(to_postgres_sql(sql), params if params else None)
        return self.raw.execute(sql, params)

    def close(self):
        self.raw.close()


def connect(target):
    """Membuka koneksi. target = path file SQLite, ":memory:", atau URL Postgres."""
    if is_postgres_url(target):
        return _connect_postgres(target)
    return _connect_sqlite(target)


def _connect_sqlite(db_path):
    if db_path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

    conn = sqlite3.connect(
        db_path,
        timeout=10,               # Tunggu maksimal 10 detik jika database sedang dikunci.
        isolation_level=None,     # Kita atur transaksi sendiri lewat transaction().
        check_same_thread=False,  # Dipakai oleh test akses bersamaan (threading).
    )
    conn.row_factory = sqlite3.Row  # Baris bisa dibaca seperti dict: row["title"].
    conn.execute("PRAGMA foreign_keys = ON")
    return Database(conn, "sqlite")


def _connect_postgres(url):
    # Di-import di sini, bukan di atas file, supaya laptop yang hanya
    # memakai SQLite tetap bisa jalan walau psycopg belum terpasang.
    import psycopg
    from psycopg.rows import dict_row

    conn = psycopg.connect(
        url,
        autocommit=True,        # Sama seperti SQLite: transaksi diatur lewat transaction().
        row_factory=dict_row,   # Baris berupa dict: row["title"].
        connect_timeout=10,
    )
    return Database(conn, "postgres")


def init_db(conn):
    """Membuat tabel dari schema.sql jika belum ada."""
    with open(SCHEMA_PATH, encoding="utf-8") as schema_file:
        schema = schema_file.read()
    if conn.kind == "sqlite":
        conn.raw.executescript(schema)
    else:
        conn.raw.execute(schema)


@contextmanager
def transaction(conn):
    """Menjalankan beberapa query sebagai satu kesatuan (atomik).

    Pemakaian:
        with transaction(conn):
            ...query 1...
            ...query 2...

    Di dalam blok, hanya satu proses yang boleh berjalan pada satu waktu:
    - SQLite  : BEGIN IMMEDIATE langsung mengunci database untuk penulisan.
    - Postgres: pg_advisory_xact_lock membuat proses lain menunggu sampai COMMIT.
    Jika terjadi error di tengah jalan, ROLLBACK membatalkan semua perubahan.
    """
    if conn.kind == "sqlite":
        conn.execute("BEGIN IMMEDIATE")
    else:
        conn.execute("BEGIN")
        conn.execute("SELECT pg_advisory_xact_lock(?)", (ENROLLMENT_LOCK_ID,))
    try:
        yield
    except Exception:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


# ---------------------------------------------------------------------------
# Konversi baris database -> dataclass
# ---------------------------------------------------------------------------
def _to_user(row):
    return None if row is None else User(**dict(row))


def _to_session(row):
    return None if row is None else StudySession(**dict(row))


def _to_enrollment(row):
    return None if row is None else Enrollment(**dict(row))


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
def insert_user(conn, username, display_name):
    user = User(id=new_id(), username=username, display_name=display_name, created_at=now_text())
    conn.execute(
        "INSERT INTO users (id, username, display_name, created_at) VALUES (?, ?, ?, ?)",
        (user.id, user.username, user.display_name, user.created_at),
    )
    return user


def get_user(conn, user_id):
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _to_user(row)


def get_user_by_username(conn, username):
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    return _to_user(row)


def list_users(conn):
    rows = conn.execute("SELECT * FROM users ORDER BY display_name").fetchall()
    return [_to_user(row) for row in rows]


# ---------------------------------------------------------------------------
# Study sessions
# ---------------------------------------------------------------------------
def insert_session(conn, session):
    conn.execute(
        """
        INSERT INTO study_sessions (
            id, host_user_id, title, subject, topic, description, starts_at, ends_at,
            mode, location_text, map_url, meeting_url, capacity, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session.id, session.host_user_id, session.title, session.subject,
            session.topic, session.description, session.starts_at, session.ends_at,
            session.mode, session.location_text, session.map_url, session.meeting_url,
            session.capacity, session.status, session.created_at,
        ),
    )


def get_session(conn, session_id):
    row = conn.execute("SELECT * FROM study_sessions WHERE id = ?", (session_id,)).fetchone()
    return _to_session(row)


def list_sessions(conn, statuses=None):
    """Daftar sesi, urut dari waktu mulai paling dekat.

    statuses: list status yang ingin diambil, misalnya ["OPEN"]. None = semua.
    """
    if not statuses:
        rows = conn.execute("SELECT * FROM study_sessions ORDER BY starts_at").fetchall()
    else:
        # Membuat "?, ?" sebanyak jumlah status. Yang digabung hanya tanda tanya,
        # bukan teks dari pengguna, jadi tetap aman.
        placeholders = ", ".join("?" for _ in statuses)
        rows = conn.execute(
            f"SELECT * FROM study_sessions WHERE status IN ({placeholders}) ORDER BY starts_at",
            list(statuses),
        ).fetchall()
    return [_to_session(row) for row in rows]


def update_session_status(conn, session_id, status):
    conn.execute("UPDATE study_sessions SET status = ? WHERE id = ?", (status, session_id))


def list_sessions_by_host(conn, user_id):
    rows = conn.execute(
        "SELECT * FROM study_sessions WHERE host_user_id = ? ORDER BY starts_at", (user_id,)
    ).fetchall()
    return [_to_session(row) for row in rows]


def list_sessions_joined(conn, user_id):
    """Sesi yang diikuti user (enrollment ACTIVE), tidak termasuk sesi yang ia host."""
    rows = conn.execute(
        """
        SELECT s.* FROM study_sessions AS s
        JOIN enrollments AS e ON e.session_id = s.id
        WHERE e.user_id = ? AND e.status = ?
        ORDER BY s.starts_at
        """,
        (user_id, ENROLLMENT_ACTIVE),
    ).fetchall()
    return [_to_session(row) for row in rows]


# ---------------------------------------------------------------------------
# Enrollments
# ---------------------------------------------------------------------------
def get_enrollment(conn, session_id, user_id):
    row = conn.execute(
        "SELECT * FROM enrollments WHERE session_id = ? AND user_id = ?", (session_id, user_id)
    ).fetchone()
    return _to_enrollment(row)


def insert_enrollment(conn, session_id, user_id):
    enrollment = Enrollment(
        id=new_id(), session_id=session_id, user_id=user_id,
        status=ENROLLMENT_ACTIVE, joined_at=now_text(),
    )
    conn.execute(
        "INSERT INTO enrollments (id, session_id, user_id, status, joined_at) VALUES (?, ?, ?, ?, ?)",
        (enrollment.id, enrollment.session_id, enrollment.user_id, enrollment.status, enrollment.joined_at),
    )
    return enrollment


def set_enrollment_status(conn, enrollment_id, status):
    conn.execute(
        "UPDATE enrollments SET status = ?, joined_at = ? WHERE id = ?",
        (status, now_text(), enrollment_id),
    )


def count_active_members(conn, session_id):
    """Jumlah peserta ACTIVE di satu sesi (host tidak dihitung di sini)."""
    row = conn.execute(
        "SELECT COUNT(*) AS total FROM enrollments WHERE session_id = ? AND status = ?",
        (session_id, ENROLLMENT_ACTIVE),
    ).fetchone()
    return row["total"]


def list_active_members(conn, session_id):
    rows = conn.execute(
        """
        SELECT u.* FROM users AS u
        JOIN enrollments AS e ON e.user_id = u.id
        WHERE e.session_id = ? AND e.status = ?
        ORDER BY e.joined_at
        """,
        (session_id, ENROLLMENT_ACTIVE),
    ).fetchall()
    return [_to_user(row) for row in rows]
