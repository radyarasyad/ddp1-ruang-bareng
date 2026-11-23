# Draf Issue GitHub — RuangBareng (Fasilkom Study Hub)

Dokumen ini berisi 8 draf issue yang siap disalin ke tab **Issues** di GitHub.
Satu issue dikerjakan di satu branch oleh satu pemilik, lalu digabung lewat pull request.

> Status: **DRAF** — kelompok perlu menyetujui isi issue, keputusan desain, dan siapa pemilik tiap issue sebelum mulai coding.

## Cara pakai

1. Buka `https://github.com/radyarasyad/ddp1-ruang-bareng/issues/new`.
2. Salin **judul** ke kolom Title dan **semua isi di bawah judul** ke kolom deskripsi.
3. Isi `Pemilik` dan pasang label yang disarankan.
4. Buat issue sesuai urutan nomor, supaya nomor di GitHub sama dengan nomor di dokumen ini.
5. Pemilik membuat branch dari `main` dengan nama yang tertulis di issue.

## Keputusan desain yang dipakai di semua issue

Keputusan ini mengikuti default blueprint (Lampiran B) dan wajib dicatat di `docs/decision-log.md`. Ubah di sini dulu kalau kelompok memutuskan lain.

| ID | Keputusan | Alasan |
|---|---|---|
| D-01 | Kapasitas menghitung **host**. `capacity = 5` berarti host ditambah maksimal 4 peserta. Nilai minimum 2, maksimum 20. | Default blueprint §11.3. Angka maksimum 20 bisa diubah kelompok. |
| D-02 | Status **FULL dihitung otomatis**, tidak disimpan. Database hanya menyimpan `OPEN`, `CANCELLED`, `COMPLETED`. | Satu sumber kebenaran. Jumlah peserta dan status tidak mungkin saling bertentangan. |
| D-03 | Peserta yang keluar lalu **bergabung lagi** memakai baris enrollment lama yang statusnya diubah kembali menjadi `ACTIVE`. Tidak ada INSERT baru. | `UNIQUE(session_id, user_id)` akan menolak INSERT kedua. |
| D-04 | Join dan leave berjalan di dalam transaksi **`BEGIN IMMEDIATE`** SQLite. | Mencegah dua join bersamaan mengisi slot terakhir (test T-15). |
| D-05 | Login MVP memakai **akun demo lokal** yang dipilih dari daftar. Tidak ada password dan tidak ada SSO UI. | Blueprint §12: SSO ditunda sampai ada izin resmi. |
| D-06 | Waktu disimpan sebagai teks ISO 8601 dalam zona waktu lokal (WIB), misalnya `2026-12-01T14:00`. | Sederhana, bisa dibandingkan dengan `datetime.fromisoformat`. |

## Kontrak antar-modul

Bagian ini mengunci nama fungsi supaya issue #2, #3, dan #4 bisa dikerjakan paralel tanpa saling menunggu.
Setiap fungsi service mengembalikan **tuple `(berhasil, hasil)`**. `berhasil` bertipe `bool`; `hasil` berisi objek, daftar pesan error, atau satu pesan teks.

```
app/models.py        -> konstanta status/mode, dataclass User, StudySession, Enrollment,
                        compute_display_status(session, active_count, now)
app/validation.py    -> validate_session(data) -> list[str], is_valid_http_url(url) -> bool
app/storage.py       -> connect(db_path), init_db(conn), transaction(conn),
                        fungsi CRUD (lihat Issue #4)
app/services/session_service.py    -> create_session, list_open_sessions,
                                      get_session_detail, cancel_session, list_my_sessions
app/services/enrollment_service.py -> join_session, leave_session
app/web.py           -> create_app(db_path=None): adapter Flask, tanpa logika bisnis
```

Arah dependensi hanya satu: `web -> services -> (validation, storage) -> models`.
`models.py` tidak boleh meng-import modul lain di dalam `app/`.

## Peta dependensi

```
#1 Setup
 └─ #2 Models
     ├─ #3 Validation ─┐
     └─ #4 Storage ────┼─ #5 Session service ─┐
                       └─ #6 Enrollment ──────┴─ #7 Flask ─ #8 UI
```

Setelah #2 masuk ke `main`, issue #3 dan #4 bisa dikerjakan bersamaan. Setelah #4 masuk, #6 bisa jalan paralel dengan #5.

## Usulan pembagian (4 anggota)

Pembagian ini menyeimbangkan jumlah commit, dan setiap orang memegang setidaknya satu modul logika Python.

| Anggota | Issue | Alasan |
|---|---|---|
| A | #1, #5 | Setup sekaligus service sesi |
| B | #2, #6 | Model sekaligus aturan join yang paling kritis |
| C | #3, #8 | Validasi sekaligus pesan error di UI |
| D | #4, #7 | Storage sekaligus adapter web yang memakainya |

Untuk 3 anggota: gabungkan #1 ke pemilik #2, dan bagi #7 serta #8 ke dua orang yang berbeda.

## Aturan umum setiap issue

- Branch dibuat dari `main` yang terbaru. Tidak boleh push langsung ke `main`.
- Pull request menjelaskan tujuan, perubahan, cara menguji, dan hasil test yang benar-benar dijalankan.
- `python -m unittest discover -s tests -v` harus lulus sebelum PR di-review.
- Minimal satu anggota lain me-review PR sebelum merge.
- Jangan commit `.env`, file database (`*.db`), atau data mahasiswa sungguhan.
- Pemilik issue harus bisa menjelaskan setiap baris kodenya di video demo.

---

## Issue #1 — Setup: struktur proyek, README, dan konfigurasi

**Label:** `setup` · **Branch:** `feat/1-setup` · **Pemilik:** ___ · **Bergantung pada:** –

### Tujuan
Menyiapkan kerangka repo supaya semua anggota bisa clone, menjalankan test, dan mulai bekerja di modul masing-masing tanpa bertabrakan.

### File yang boleh diubah
- `README.md`
- `.gitignore`, `.env.example`, `requirements.txt`
- `app/__init__.py`, `app/config.py`, `app/services/__init__.py`
- `tests/__init__.py`, `tests/test_smoke.py`
- `docs/decision-log.md`

### Pekerjaan
1. Buat struktur folder sesuai blueprint §10.3 (`app/`, `app/services/`, `tests/`, `docs/`).
2. `requirements.txt` hanya berisi `Flask` dengan versi tertentu (misalnya `Flask==3.1.*`).
3. `.gitignore` mengabaikan `__pycache__/`, `.venv/`, `.env`, `*.db`, dan `instance/`.
4. `.env.example` berisi nama variabel tanpa nilai rahasia: `SECRET_KEY=`, `DATABASE_PATH=instance/ruangbareng.db`.
5. `app/config.py` membaca variabel itu memakai `os.environ.get`, dengan nilai default yang aman untuk pengembangan lokal.
6. README menjelaskan tujuan produk, versi Python minimum (3.11), cara membuat virtualenv, cara install, cara menjalankan test, dan alur kerja branch/PR.
7. `docs/decision-log.md` berisi tabel keputusan D-01 sampai D-06.
8. `tests/test_smoke.py` berisi satu test yang memastikan paket `app` bisa di-import.

### Acceptance criteria
- [ ] `python -m unittest discover -s tests -v` lulus di laptop yang baru clone repo.
- [ ] Tidak ada secret, file `.db`, atau `.env` yang ikut ter-commit.
- [ ] README cukup untuk orang yang belum pernah melihat proyek ini.

### Konsep DDP1 yang harus bisa dijelaskan
Modul dan paket (`__init__.py`), `import`, variabel lingkungan, virtualenv.

---

## Issue #2 — Model data dan status

**Label:** `core` · **Branch:** `feat/2-models` · **Pemilik:** ___ · **Bergantung pada:** #1

### Tujuan
Mendefinisikan bentuk data `User`, `StudySession`, dan `Enrollment` beserta konstanta status, supaya semua modul lain memakai nama field yang sama.

### File yang boleh diubah
- `app/models.py`
- `tests/test_models.py`

### Pekerjaan
1. Konstanta:
   - `MODE_ONLINE = "ONLINE"`, `MODE_OFFLINE = "OFFLINE"`, `VALID_MODES`
   - `STATUS_OPEN`, `STATUS_FULL`, `STATUS_CANCELLED`, `STATUS_COMPLETED`
   - `STORED_SESSION_STATUSES = {OPEN, CANCELLED, COMPLETED}` (keputusan D-02)
   - `ENROLLMENT_ACTIVE`, `ENROLLMENT_CANCELLED`
   - `MIN_CAPACITY = 2`, `MAX_CAPACITY = 20`
2. `@dataclass` untuk ketiga entitas, dengan field sesuai skema blueprint §11.4:
   - `User(id, username, display_name, created_at)`
   - `StudySession(id, host_user_id, title, subject, topic, description, starts_at, ends_at, mode, location_text, map_url, meeting_url, capacity, status, created_at)`
   - `Enrollment(id, session_id, user_id, status, joined_at)`
3. `compute_display_status(session, active_count, now)` mengembalikan status yang ditampilkan ke pengguna:
   - `CANCELLED` atau `COMPLETED` dikembalikan apa adanya.
   - `now` sudah melewati `ends_at` → `COMPLETED`.
   - `active_count + 1 >= capacity` (host ikut dihitung, D-01) → `FULL`.
   - Selain itu → `OPEN`.
4. `slots_left(session, active_count)` mengembalikan sisa slot, tidak pernah negatif.

### Test case wajib
- [ ] Dataclass bisa dibuat dan field-nya bisa dibaca.
- [ ] `compute_display_status` diuji untuk setiap cabang: OPEN, FULL, CANCELLED, COMPLETED (dari status), dan COMPLETED (karena waktu sudah lewat).
- [ ] Kapasitas 5 dengan 4 peserta aktif → FULL. Dengan 3 peserta aktif → OPEN, `slots_left` = 1.

### Acceptance criteria
- [ ] `models.py` tidak meng-import modul lain di dalam `app/`.
- [ ] Semua test lulus.

### Konsep DDP1 yang harus bisa dijelaskan
Tipe data, konstanta, kondisional bercabang, fungsi. **Konsep baru:** `dataclasses`, type hints, `datetime`.

---

## Issue #3 — Validasi input sesi

**Label:** `core` · **Branch:** `feat/3-validation` · **Pemilik:** ___ · **Bergantung pada:** #2

### Tujuan
Menolak data sesi yang tidak valid sebelum disimpan, dengan pesan error dalam bahasa Indonesia yang menyebut field yang salah.

### File yang boleh diubah
- `app/validation.py`
- `tests/test_validation.py`

### Pekerjaan
1. `is_valid_http_url(url) -> bool`: hanya menerima skema `http`/`https` dengan domain yang tidak kosong. Gunakan `urllib.parse.urlparse`.
2. `validate_session(data: dict) -> list[str]` mengembalikan daftar pesan error. Daftar kosong berarti data valid. Aturan:
   - `title` dan `subject` wajib, setelah `.strip()`; maksimal 100 karakter.
   - `mode` harus salah satu dari `VALID_MODES`.
   - `starts_at` dan `ends_at` harus format ISO yang valid, `ends_at` harus setelah `starts_at`, dan `starts_at` tidak boleh di masa lalu.
   - `capacity` harus bilangan bulat antara `MIN_CAPACITY` dan `MAX_CAPACITY`. Teks seperti `"lima"` ditolak, bukan membuat program crash.
   - Mode `OFFLINE` → `location_text` wajib. `map_url` opsional, tapi kalau diisi harus URL yang valid.
   - Mode `ONLINE` → `meeting_url` wajib dan harus URL yang valid. `location_text` tidak diwajibkan.
   - Field bernilai `None` diperlakukan sama dengan string kosong, bukan menyebabkan `AttributeError`.
3. Supaya bisa diuji, waktu "sekarang" diterima lewat parameter opsional: `validate_session(data, now=None)`.

### Test case wajib (dari matriks blueprint §14.1)
- [ ] T-01: semua field valid → `[]`.
- [ ] T-02: judul kosong atau hanya spasi → ada error judul.
- [ ] T-03: waktu selesai sebelum waktu mulai → ditolak.
- [ ] T-04: kapasitas `0`, `-1`, `"abc"`, dan `21` → ditolak.
- [ ] T-05: OFFLINE tanpa lokasi → ditolak.
- [ ] T-06: ONLINE tanpa lokasi fisik tapi dengan `meeting_url` → valid.
- [ ] T-14: `map_url = "javascript:alert(1)"` dan `"ftp://x"` → ditolak.
- [ ] Field bernilai `None` tidak membuat program crash.

### Konsep DDP1 yang harus bisa dijelaskan
String, list, dictionary, kondisional, `try/except` (`ValueError`, `TypeError`). **Konsep baru:** `urllib.parse`, `datetime.fromisoformat`.

---

## Issue #4 — Storage SQLite

**Label:** `core` · **Branch:** `feat/4-storage` · **Pemilik:** ___ · **Bergantung pada:** #2

### Tujuan
Menyimpan data secara persisten di SQLite, sehingga data tetap ada setelah aplikasi di-restart. Modul ini hanya mengurus baca/tulis dan tidak berisi aturan bisnis.

### File yang boleh diubah
- `app/storage.py`
- `app/schema.sql`
- `tests/test_storage.py`

### Pekerjaan
1. `app/schema.sql` mengikuti blueprint §11.4, dengan dua penyesuaian:
   - `CHECK (status IN ('OPEN','CANCELLED','COMPLETED'))` untuk `study_sessions` (keputusan D-02).
   - `CHECK (capacity BETWEEN 2 AND 20)`.
2. `connect(db_path) -> sqlite3.Connection`: aktifkan `PRAGMA foreign_keys = ON`, atur `row_factory = sqlite3.Row`, dan buka dengan `isolation_level=None` supaya transaksi dikontrol manual.
3. `init_db(conn)`: menjalankan `schema.sql` dengan `CREATE TABLE IF NOT EXISTS`.
4. `transaction(conn)`: context manager (`@contextmanager`) yang menjalankan `BEGIN IMMEDIATE`, lalu `COMMIT` kalau berhasil dan `ROLLBACK` kalau ada exception (keputusan D-04).
5. Fungsi CRUD. Semua query **wajib memakai parameter `?`**, tidak boleh menyusun SQL dengan f-string:
   - `insert_user`, `get_user`, `get_user_by_username`, `list_users`
   - `insert_session`, `get_session`, `list_sessions(statuses=None)`, `update_session_status`
   - `list_sessions_by_host(user_id)`, `list_sessions_joined(user_id)`
   - `get_enrollment(session_id, user_id)`, `insert_enrollment`, `set_enrollment_status`
   - `count_active_members(session_id)`, `list_active_members(session_id)` (mengembalikan daftar `User`)
6. Fungsi `get_*` mengembalikan dataclass dari `models.py`, atau `None` kalau data tidak ditemukan.
7. ID dibuat dengan `uuid.uuid4().hex`.

### Test case wajib
- [ ] Test memakai database sementara (`tempfile` atau `":memory:"`), bukan database pengembangan.
- [ ] T-12: data yang ditulis lewat satu koneksi masih bisa dibaca setelah koneksi ditutup dan dibuka lagi (memakai file sementara).
- [ ] Insert enrollment kedua dengan `(session_id, user_id)` yang sama memunculkan `sqlite3.IntegrityError`.
- [ ] `transaction` melakukan rollback ketika exception terjadi di dalam blok `with`.
- [ ] `count_active_members` hanya menghitung enrollment yang statusnya `ACTIVE`.

### Konsep DDP1 yang harus bisa dijelaskan
Operasi database, perulangan untuk mengubah baris menjadi objek, penanganan error. **Konsep baru:** `sqlite3`, SQL, query berparameter (mencegah SQL injection), transaksi, context manager.

---

## Issue #5 — Session service: buat, cari, detail, batalkan

**Label:** `core` · **Branch:** `feat/5-session-service` · **Pemilik:** ___ · **Bergantung pada:** #3, #4

### Tujuan
Menggabungkan validasi dan storage menjadi aturan bisnis untuk sesi belajar (US-01 sampai US-04, US-07, US-08).

### File yang boleh diubah
- `app/services/session_service.py`
- `tests/test_session_service.py`

### Pekerjaan
1. `create_session(conn, host_user_id, data, now=None) -> (bool, StudySession | list[str])`:
   validasi dulu; kalau ada error, kembalikan `(False, errors)` tanpa menyimpan apa pun. Kalau valid, simpan dengan status `OPEN`.
2. `list_open_sessions(conn, keyword=None, subject=None, now=None) -> list[dict]`:
   - Hanya menampilkan sesi yang status tampilannya OPEN atau FULL (US-01).
   - `keyword` dicocokkan ke `title`, `subject`, dan `topic` tanpa membedakan huruf besar/kecil (US-02).
   - Diurutkan berdasarkan `starts_at` yang paling dekat.
   - Setiap item berisi `session`, `active_count`, `display_status`, dan `slots_left`.
3. `get_session_detail(conn, session_id, now=None) -> dict | None`: data yang sama seperti item list, ditambah nama host dan daftar nama tampilan peserta dari `storage.list_active_members` (US-03). NPM tidak ditampilkan.
4. `cancel_session(conn, session_id, user_id) -> (bool, str)`:
   - Ditolak kalau sesi tidak ditemukan.
   - Ditolak kalau `user_id` bukan host (T-11).
   - Ditolak kalau sesi sudah CANCELLED atau COMPLETED.
   - Kalau lolos, status diubah menjadi `CANCELLED`. Data tidak dihapus.
5. `list_my_sessions(conn, user_id) -> dict` berisi dua daftar, `hosted` dan `joined`.

### Test case wajib
- [ ] T-01: sesi valid tersimpan dan muncul di `list_open_sessions`.
- [ ] T-02: input tidak valid tidak membuat record baru.
- [ ] T-13: keyword yang tidak cocok mengembalikan list kosong, bukan error.
- [ ] Sesi CANCELLED tidak muncul di daftar default.
- [ ] T-11: user yang bukan host gagal membatalkan sesi, dan status sesi tidak berubah.
- [ ] Pencarian `"struktur"` menemukan sesi berjudul `"Belajar Struktur Data"`.

### Konsep DDP1 yang harus bisa dijelaskan
Fungsi dengan banyak nilai kembali (tuple), perulangan dan filter list, `.lower()` dan `in`, sorting dengan `key=`.

---

## Issue #6 — Enrollment service: join, leave, kapasitas

**Label:** `core` · `critical` · **Branch:** `feat/6-enrollment` · **Pemilik:** ___ · **Bergantung pada:** #4

### Tujuan
Peserta bisa bergabung dan keluar dari sesi, tanpa pernah terjadi pendaftaran ganda atau peserta melebihi kapasitas (US-05, US-06).

### File yang boleh diubah
- `app/services/enrollment_service.py`
- `tests/test_enrollment_service.py`

### Pekerjaan
1. `join_session(conn, session_id, user_id, now=None) -> (bool, str)`. Seluruh pemeriksaan dan penulisan berada di dalam **satu** `with storage.transaction(conn):`. Urutan pemeriksaan (blueprint §8.3):
   1. Sesi ada → kalau tidak: `"Sesi tidak ditemukan."`
   2. Status tampilan OPEN → kalau tidak: `"Sesi tidak lagi menerima peserta."` atau `"Sesi sudah penuh."`
   3. User bukan host → kalau host: `"Kamu adalah host sesi ini."`
   4. Belum punya enrollment ACTIVE → kalau sudah: `"Kamu sudah bergabung."`
   5. Hitung ulang kapasitas di dalam transaksi: `count_active_members + 1 (host) < capacity`. Langkah 2 saja tidak cukup, karena peserta lain bisa join tepat di antara pemeriksaan dan penulisan.
   6. Kalau ada enrollment lama berstatus CANCELLED → ubah menjadi ACTIVE (D-03). Kalau tidak ada → insert baru.
2. `leave_session(conn, session_id, user_id, now=None) -> (bool, str)`: hanya bisa dilakukan kalau user punya enrollment ACTIVE dan sesi belum CANCELLED atau COMPLETED. Statusnya diubah menjadi CANCELLED, bukan dihapus.

### Test case wajib
- [ ] T-07: join ke sesi OPEN yang masih punya slot berhasil, dan `count_active_members` bertambah 1.
- [ ] T-08: join dua kali → join kedua ditolak, jumlah peserta tidak berubah.
- [ ] T-09: kapasitas 3 dengan 2 peserta aktif → peserta ketiga ditolak.
- [ ] T-10: join ke sesi CANCELLED ditolak.
- [ ] Host mencoba join ke sesinya sendiri → ditolak.
- [ ] Leave lalu join lagi berhasil, dan tetap hanya ada satu baris enrollment (D-03).
- [ ] T-15: dua koneksi ke file database yang sama memakai `threading` untuk join ke slot terakhir hampir bersamaan → hanya satu yang berhasil. Atur `timeout` koneksi supaya proses kedua menunggu, bukan langsung error.

### Konsep DDP1 yang harus bisa dijelaskan
Kondisional berurutan dengan *early return*, perbandingan bilangan. **Konsep baru:** transaksi atomik, race condition, `threading` untuk menguji akses bersamaan.

---

## Issue #7 — Adapter web Flask dan login demo

**Label:** `web` · **Branch:** `feat/7-flask` · **Pemilik:** ___ · **Bergantung pada:** #5, #6

### Tujuan
Membuat semua fitur bisa dipakai lewat browser. Route hanya menerima input, memanggil service, lalu menampilkan hasilnya. Tidak boleh ada aturan bisnis di route.

### File yang boleh diubah
- `app/web.py`
- `app/templates/*.html` (versi awal: HTML semantik tanpa styling)
- `scripts/seed_demo.py`
- `tests/test_web.py`

### Pekerjaan
1. `create_app(db_path=None)` memakai pola *application factory*, supaya test bisa memakai database sementara.
2. Route:

   | Method | Path | Fungsi |
   |---|---|---|
   | GET | `/` | Daftar sesi, dengan query `?q=` dan `?subject=` |
   | GET, POST | `/sessions/new` | Form buat sesi (wajib login) |
   | GET | `/sessions/<id>` | Detail sesi |
   | POST | `/sessions/<id>/join` | Bergabung |
   | POST | `/sessions/<id>/leave` | Keluar |
   | POST | `/sessions/<id>/cancel` | Batalkan (hanya host) |
   | GET | `/me` | Sesi yang dibuat dan diikuti |
   | GET, POST | `/login` | Pilih akun demo |
   | POST | `/logout` | Keluar dari akun demo |

3. Simpan `user_id` di `flask.session`. `SECRET_KEY` diambil dari `config.py`, tidak ditulis langsung di kode.
4. Kalau validasi gagal, form ditampilkan lagi dengan nilai yang sudah diisi dan pesan error di dekat field terkait. Status HTTP 400.
5. Pesan hasil join/leave/cancel ditampilkan dengan `flash()`.
6. Biarkan autoescape Jinja tetap aktif. Jangan pakai filter `|safe` untuk teks yang diketik pengguna.
7. Link Maps dan meeting dibuka dengan `target="_blank" rel="noopener noreferrer"`.
8. `scripts/seed_demo.py` membuat 3 akun demo (`Host A`, `Peserta B`, `Peserta C`) dan 2 sesi contoh. Semua data diberi label **DEMO** dan tidak boleh disajikan sebagai penggunaan nyata.
9. Tambahkan cara menjalankan ke README: `flask --app app.web run`.

### Test case wajib (pakai `app.test_client()`)
- [ ] GET `/` mengembalikan 200, termasuk ketika database masih kosong (empty state).
- [ ] POST `/sessions/new` tanpa login diarahkan ke `/login`.
- [ ] POST `/sessions/new` dengan data tidak valid → status 400, dan pesan error tampil.
- [ ] Alur demo blueprint §21.1: Host A membuat sesi, Peserta B join, join kedua ditolak, sesi penuh menolak peserta berikutnya, host membatalkan sesi.
- [ ] POST `/sessions/<id>/cancel` oleh user yang bukan host → pesan penolakan tampil, dan status sesi di database tetap OPEN. Pemeriksaan host tetap dilakukan di service, bukan di route.

### Konsep DDP1 yang harus bisa dijelaskan
Alur request → fungsi → response, dictionary (`request.form`). **Konsep baru:** Flask, routing, HTTP method dan status code, template Jinja, session cookie.

---

## Issue #8 — Tampilan UI, aksesibilitas, dan state kosong/error

**Label:** `ui` · **Branch:** `feat/8-ui` · **Pemilik:** ___ · **Bergantung pada:** #7

### Tujuan
Membuat tampilan yang jelas, bisa dipakai di HP, mudah diakses, dan tidak terlihat seperti template generik.

### File yang boleh diubah
- `app/templates/*.html` (markup dan kelas; route di `web.py` tidak diubah)
- `app/static/css/style.css`
- `app/static/fonts/*`

### Pekerjaan
1. **Warna:** warna utama deep teal `#0F766E` dengan teks putih (kontras 5,5:1). Latar `#F8FAFC`, kartu `#FFFFFF`, border `#E2E8F0`, teks `#0F172A`, teks sekunder `#475569`. Didefinisikan sebagai CSS variable di `:root`.
2. **Font:** Cabinet Grotesk untuk judul (file disimpan di `static/fonts/`, jangan ambil dari CDN pihak ketiga). Inter 400/500 untuk teks biasa. Kalau Cabinet Grotesk sulit dipasang, pakai Bricolage Grotesque. Maksimal 2 keluarga font dan 3 ketebalan.
3. **Kartu sesi** (blueprint §9.2): judul atau mata kuliah, waktu, mode, lokasi ringkas atau label "Online", slot dalam format `3/5 orang (termasuk host)`, nama host, dan status.
4. Status ditulis sebagai **teks** (OPEN/FULL/CANCELLED/COMPLETED), bukan hanya warna.
5. State kosong dan error memakai pesan dari blueprint §9.3, masing-masing dengan tombol aksi.
6. Form: setiap input punya `<label>`. Error ditampilkan di bawah field terkait dengan `aria-describedby`, ditambah `aria-invalid="true"`. Form juga menjelaskan bahwa kapasitas sudah termasuk host.
7. Landmark HTML: `<header>`, `<nav>`, satu `<main>`, `<footer>`, dan `lang="id"`.
8. Fokus keyboard terlihat jelas (`:focus-visible`). Elemen yang bisa diklik memakai `<button>` atau `<a>`.
9. Hover hanya mengubah warna, bayangan, atau border, dengan durasi 150ms. Tidak ada efek membesar.
10. Semua animasi dimatikan di `@media (prefers-reduced-motion: reduce)`.
11. Yang dilarang: warna ungu/indigo, teks bergradien, emoji sebagai ikon, efek kaca (glassmorphism), tombol berbentuk pil di semua tempat, dan grid 3 kartu yang identik.

### Acceptance criteria
- [ ] Tidak ada scroll horizontal di lebar 375, 768, 1024, dan 1440 px.
- [ ] Seluruh alur demo bisa diselesaikan hanya dengan keyboard.
- [ ] Kontras teks biasa minimal 4,5:1, dan teks besar/elemen UI minimal 3:1.
- [ ] Screenshot di HP dan desktop dilampirkan di PR.
- [ ] `python -m unittest discover -s tests -v` tetap lulus.

### Konsep yang harus bisa dijelaskan
**Konsep baru:** template inheritance Jinja (`{% extends %}`), CSS variable, layout responsif, dasar aksesibilitas web (WCAG).

---

## Setelah 8 issue selesai (belum dibuat issue-nya)

- **QA dan bukti test:** `docs/test-evidence.md` berisi output test yang sebenarnya dan hasil usability test.
- **Demo:** skrip video maksimal 15 menit, mengikuti urutan blueprint §21.
- **Fase 2** (hanya kalau didukung temuan riset): waitlist, edit sesi oleh host, pengingat.
