# RuangBareng — Fasilkom Study Hub

Platform *peer learning* untuk mahasiswa Fasilkom UI: cari sesi belajar kelompok kecil berdasarkan mata kuliah, topik, waktu, dan lokasi, atau buat sesi sendiri lalu ajak orang lain bergabung.

Proyek kelompok **Dasar-Dasar Pemrograman 1**, semester gasal 2026/2027.

> **Status: prototipe MVP.** Login memakai akun demo lokal, bukan SSO UI. Data yang dibuat oleh `scripts/seed_demo.py` diberi label DEMO dan bukan penggunaan nyata.

## Fitur MVP

| Fitur | User story |
|---|---|
| Daftar sesi terdekat, dengan pencarian kata kunci dan filter mata kuliah | US-01, US-02 |
| Detail sesi: jadwal, mode, lokasi atau link, host, peserta, sisa tempat | US-03 |
| Buat sesi dengan validasi di backend | US-04, US-08 |
| Gabung dan keluar dari sesi, tanpa pendaftaran ganda atau melebihi kapasitas | US-05, US-06 |
| Host membatalkan sesi (data tidak dihapus) | US-07 |
| Halaman "Sesi saya" | – |

## Arsitektur

```
Browser
  │  HTTP
  ▼
app/web.py                 Adapter Flask: baca request → panggil service → render template
  │
  ▼
app/services/              Aturan bisnis (Python murni, bisa diuji tanpa browser)
  ├─ session_service.py    buat, cari, detail, batalkan
  └─ enrollment_service.py join dan leave di dalam transaksi
  │
  ├──► app/validation.py   Pemeriksaan input form
  ▼
app/storage.py             Query SQLite (selalu memakai parameter ?)
  │
  ▼
app/models.py              Dataclass + aturan status (OPEN/FULL/CANCELLED/COMPLETED)
```

Arah import hanya satu: `web → services → validation/storage → models`. Keputusan desain dicatat di [docs/decision-log.md](docs/decision-log.md).

## Menjalankan di laptop sendiri

Butuh Python 3.11 atau lebih baru.

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Isi data demo (6 akun dan 2 sesi), lalu jalankan server:

```powershell
python scripts/seed_demo.py
flask --app app.web run
```

Buka `http://127.0.0.1:5000`, klik **Masuk (akun demo)**, lalu pilih salah satu akun.

Konfigurasi opsional: salin `.env.example` menjadi `.env`, lalu isi `SECRET_KEY` dengan nilai acak. File `.env` dan database (`instance/`) tidak ikut di-commit.

## Deploy online

Website dideploy ke **Vercel**, dengan database **Neon Postgres**. Langkah lengkapnya ada di [docs/deploy-vercel.md](docs/deploy-vercel.md).
Di laptop, aplikasi tetap memakai SQLite. Postgres hanya dipakai jika variabel `DATABASE_URL` diisi.

## Menjalankan test

```powershell
python -m unittest discover -s tests -v
```

| File test | Yang diuji |
|---|---|
| `test_models.py` | Status tampilan dan sisa slot |
| `test_validation.py` | T-01 s.d. T-06, T-14: input wajib, waktu, kapasitas, URL |
| `test_storage.py` | CRUD, UNIQUE enrollment, rollback, T-12 data persisten |
| `test_session_service.py` | Buat, cari, filter, batal (T-11), T-13 hasil kosong |
| `test_enrollment_service.py` | T-07 s.d. T-10 join, rejoin, T-15 dua join bersamaan |
| `test_web.py` | Alur demo end-to-end, CSRF, escape HTML, link meeting tersembunyi, konfigurasi Vercel |
| `test_postgres.py` | Alur utama dan T-15 di Postgres sungguhan (dilewati kecuali `TEST_DATABASE_URL` diisi) |

## Alur kerja Git

1. Ambil issue di tab **Issues** (draf ada di [docs/issue-drafts.md](docs/issue-drafts.md)).
2. Buat branch dari `main`: `git switch -c feat/<nomor>-<nama>`.
3. Commit dari akun sendiri, lalu buka pull request.
4. Minimal satu anggota lain me-review sebelum merge. Tidak ada push langsung ke `main`.

## Keterbatasan yang diketahui

- Login hanya akun demo tanpa password. Siapa pun yang membuka aplikasi bisa memilih akun mana saja.
- Di Postgres, semua join dan leave diantrekan dengan satu kunci (`pg_advisory_xact_lock`). Cara ini aman dan sederhana, tapi bisa memperlambat jika ada ratusan join per detik.
- Belum ada waitlist, edit sesi, notifikasi, atau moderasi (fase 2).
- Tampilan hanya tema terang.
