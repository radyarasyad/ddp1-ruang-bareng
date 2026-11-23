-- Skema database RuangBareng (blueprint §11.4, dengan keputusan D-01 dan D-02).
-- IF NOT EXISTS membuat file ini aman dijalankan berkali-kali.

CREATE TABLE IF NOT EXISTS users (
    id           TEXT PRIMARY KEY,
    username     TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS study_sessions (
    id            TEXT PRIMARY KEY,
    host_user_id  TEXT NOT NULL,
    title         TEXT NOT NULL,
    subject       TEXT NOT NULL,
    topic         TEXT,
    description   TEXT,
    starts_at     TEXT NOT NULL,
    ends_at       TEXT NOT NULL,
    mode          TEXT NOT NULL CHECK (mode IN ('ONLINE', 'OFFLINE')),
    location_text TEXT,
    map_url       TEXT,
    meeting_url   TEXT,
    -- Harus sama dengan MIN_CAPACITY dan MAX_CAPACITY di models.py.
    capacity      INTEGER NOT NULL CHECK (capacity BETWEEN 2 AND 20),
    -- FULL tidak disimpan; dihitung dari jumlah peserta (D-02).
    status        TEXT NOT NULL CHECK (status IN ('OPEN', 'CANCELLED', 'COMPLETED')),
    created_at    TEXT NOT NULL,
    FOREIGN KEY (host_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS enrollments (
    id         TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_id    TEXT NOT NULL,
    status     TEXT NOT NULL CHECK (status IN ('ACTIVE', 'CANCELLED')),
    joined_at  TEXT NOT NULL,
    -- Satu orang hanya punya satu baris per sesi. Rejoin = ubah status (D-03).
    UNIQUE (session_id, user_id),
    FOREIGN KEY (session_id) REFERENCES study_sessions(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
