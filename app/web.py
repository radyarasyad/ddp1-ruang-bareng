"""Adapter web Flask.

Tugas route di file ini hanya tiga:
1. membaca input dari request,
2. memanggil fungsi di services/,
3. menampilkan hasilnya lewat template.
Aturan bisnis (boleh join atau tidak, dsb.) TIDAK ditulis di sini.

Menjalankan: flask --app app.web run
"""

import secrets
from functools import wraps

from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)
from flask import session as cookie_session  # Diberi nama lain agar tidak tertukar dengan StudySession.

from app import config, storage
from app.models import MAX_CAPACITY, MIN_CAPACITY, MODE_OFFLINE, MODE_ONLINE, parse_time
from app.services import enrollment_service, session_service

DAY_NAMES = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def create_app(db_path=None):
    """Membuat aplikasi Flask (pola "application factory").

    db_path bisa diisi saat testing supaya test memakai database sementara.
    """
    app = Flask(__name__)
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["DATABASE_PATH"] = db_path or config.DATABASE_PATH

    # Pastikan tabel sudah ada sebelum request pertama.
    conn = storage.connect(app.config["DATABASE_PATH"])
    storage.init_db(conn)
    conn.close()

    # -----------------------------------------------------------------------
    # Koneksi database per request
    # -----------------------------------------------------------------------
    def get_db():
        """Satu koneksi per request, disimpan di objek g milik Flask."""
        if "db" not in g:
            g.db = storage.connect(app.config["DATABASE_PATH"])
        return g.db

    @app.teardown_appcontext
    def close_db(error):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    # -----------------------------------------------------------------------
    # Login demo dan proteksi CSRF
    # -----------------------------------------------------------------------
    def current_user():
        user_id = cookie_session.get("user_id")
        if user_id is None:
            return None
        return storage.get_user(get_db(), user_id)

    def login_required(view):
        """Decorator: mengarahkan ke halaman login jika belum login."""
        @wraps(view)
        def wrapper(*args, **kwargs):
            if current_user() is None:
                flash("Pilih akun demo dulu untuk melanjutkan.", "info")
                return redirect(url_for("login", next=request.path))
            return view(*args, **kwargs)
        return wrapper

    def csrf_token():
        """Token acak per pengguna. Form POST wajib mengirim token yang sama.

        Ini mencegah situs lain diam-diam mengirim form atas nama pengguna.
        """
        if "csrf_token" not in cookie_session:
            cookie_session["csrf_token"] = secrets.token_hex(16)
        return cookie_session["csrf_token"]

    @app.before_request
    def check_csrf():
        if request.method == "POST":
            sent = request.form.get("csrf_token", "")
            expected = cookie_session.get("csrf_token", "")
            if not expected or not secrets.compare_digest(sent, expected):
                abort(400, description="Form kedaluwarsa. Muat ulang halaman lalu coba lagi.")

    @app.context_processor
    def inject_globals():
        """Variabel yang otomatis tersedia di semua template."""
        return {
            "current_user": current_user(),
            "csrf_token": csrf_token,
            "MODE_ONLINE": MODE_ONLINE,
            "MODE_OFFLINE": MODE_OFFLINE,
        }

    # -----------------------------------------------------------------------
    # Filter template untuk format waktu Indonesia
    # -----------------------------------------------------------------------
    @app.template_filter("day_label")
    def day_label(iso_text):
        """'2026-12-01T14:00' -> 'Selasa, 1 Des 2026'"""
        moment = parse_time(iso_text)
        return f"{DAY_NAMES[moment.weekday()]}, {moment.day} {MONTH_NAMES[moment.month - 1]} {moment.year}"

    @app.template_filter("clock")
    def clock(iso_text):
        """'2026-12-01T14:00' -> '14.00'"""
        return parse_time(iso_text).strftime("%H.%M")

    @app.template_filter("month_short")
    def month_short(iso_text):
        return MONTH_NAMES[parse_time(iso_text).month - 1]

    @app.template_filter("day_number")
    def day_number(iso_text):
        return parse_time(iso_text).day

    # -----------------------------------------------------------------------
    # Halaman
    # -----------------------------------------------------------------------
    @app.get("/")
    def index():
        keyword = request.args.get("q", "")
        subject = request.args.get("subject", "")
        db = get_db()
        items = session_service.list_open_sessions(db, keyword=keyword, subject=subject)
        subjects = session_service.list_subjects(db)
        has_filter = bool(keyword.strip() or subject.strip())
        return render_template(
            "index.html", items=items, subjects=subjects,
            keyword=keyword, subject=subject, has_filter=has_filter,
        )

    @app.route("/sessions/new", methods=["GET", "POST"])
    @login_required
    def new_session():
        form = {"mode": MODE_OFFLINE, "capacity": "5"}
        errors = {}
        if request.method == "POST":
            form = request.form.to_dict()
            ok, result = session_service.create_session(get_db(), current_user().id, form)
            if ok:
                flash("Sesi berhasil dibuat dan sudah tampil di daftar.", "success")
                return redirect(url_for("session_detail", session_id=result.id))
            errors = result
            # Status 400: data yang dikirim tidak valid.
            return render_template(
                "form.html", form=form, errors=errors,
                min_capacity=MIN_CAPACITY, max_capacity=MAX_CAPACITY,
            ), 400
        return render_template(
            "form.html", form=form, errors=errors,
            min_capacity=MIN_CAPACITY, max_capacity=MAX_CAPACITY,
        )

    @app.get("/sessions/<session_id>")
    def session_detail(session_id):
        detail = session_service.get_session_detail(get_db(), session_id)
        if detail is None:
            abort(404)
        user = current_user()
        is_host = user is not None and user.id == detail["session"].host_user_id
        is_member = user is not None and any(m.id == user.id for m in detail["members"])
        return render_template("detail.html", d=detail, is_host=is_host, is_member=is_member)

    @app.post("/sessions/<session_id>/join")
    @login_required
    def join(session_id):
        ok, message = enrollment_service.join_session(get_db(), session_id, current_user().id)
        flash(message, "success" if ok else "error")
        return redirect(url_for("session_detail", session_id=session_id))

    @app.post("/sessions/<session_id>/leave")
    @login_required
    def leave(session_id):
        ok, message = enrollment_service.leave_session(get_db(), session_id, current_user().id)
        flash(message, "success" if ok else "error")
        return redirect(url_for("session_detail", session_id=session_id))

    @app.post("/sessions/<session_id>/cancel")
    @login_required
    def cancel(session_id):
        ok, message = session_service.cancel_session(get_db(), session_id, current_user().id)
        flash(message, "success" if ok else "error")
        return redirect(url_for("session_detail", session_id=session_id))

    @app.get("/me")
    @login_required
    def my_sessions():
        data = session_service.list_my_sessions(get_db(), current_user().id)
        return render_template("me.html", hosted=data["hosted"], joined=data["joined"])

    @app.route("/login", methods=["GET", "POST"])
    def login():
        db = get_db()
        next_path = request.values.get("next", "")
        # Hanya izinkan path internal ("/..."), bukan alamat situs lain.
        if not next_path.startswith("/") or next_path.startswith("//"):
            next_path = url_for("index")

        if request.method == "POST":
            user = storage.get_user(db, request.form.get("user_id", ""))
            if user is None:
                flash("Akun tidak ditemukan.", "error")
            else:
                cookie_session["user_id"] = user.id
                flash(f"Masuk sebagai {user.display_name}.", "success")
                return redirect(next_path)
        return render_template("login.html", users=storage.list_users(db), next_path=next_path)

    @app.post("/logout")
    def logout():
        cookie_session.pop("user_id", None)
        flash("Kamu sudah keluar dari akun demo.", "info")
        return redirect(url_for("index"))

    @app.errorhandler(404)
    def not_found(error):
        return render_template("error.html", title="Halaman tidak ditemukan",
                               message="Sesi atau halaman yang kamu cari tidak ada."), 404

    @app.errorhandler(400)
    def bad_request(error):
        return render_template("error.html", title="Permintaan tidak valid",
                               message=error.description), 400

    return app
