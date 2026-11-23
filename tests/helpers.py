"""Fungsi bantu yang dipakai bersama oleh beberapa file test."""

from datetime import datetime

from app import storage

# Waktu "sekarang" yang tetap, supaya hasil test tidak berubah tergantung hari.
NOW = datetime(2026, 12, 1, 9, 0)


def make_conn():
    """Database baru di memori: cepat dan otomatis hilang setelah test."""
    conn = storage.connect(":memory:")
    storage.init_db(conn)
    return conn


def valid_offline_data(**overrides):
    """Data form sesi OFFLINE yang valid. Field tertentu bisa ditimpa."""
    data = {
        "title": "Belajar Struktur Data",
        "subject": "Struktur Data dan Algoritma",
        "topic": "Linked list",
        "description": "Latihan soal bersama",
        "starts_at": "2026-12-02T13:00",
        "ends_at": "2026-12-02T15:00",
        "mode": "OFFLINE",
        "location_text": "Perpustakaan Pusat UI",
        "map_url": "",
        "meeting_url": "",
        "capacity": "5",
    }
    data.update(overrides)
    return data


def valid_online_data(**overrides):
    data = valid_offline_data(
        mode="ONLINE", location_text="", meeting_url="https://meet.google.com/abc-defg-hij"
    )
    data.update(overrides)
    return data
