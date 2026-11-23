import os
import tempfile
import unittest

from app import storage
from app.models import STATUS_OPEN
from app.web import create_app

FUTURE = {"starts_at": "2030-01-10T13:00", "ends_at": "2030-01-10T15:00"}
TOKEN = "token-test"


class WebTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.folder.name, "web.db")
        self.app = create_app(self.db_path)
        self.client = self.app.test_client()

        conn = storage.connect(self.db_path)
        self.users = {
            name: storage.insert_user(conn, name, name.title())
            for name in ["host", "budi", "citra", "dewi"]
        }
        conn.close()

    def tearDown(self):
        self.folder.cleanup()

    # --- Bantuan -----------------------------------------------------------
    def login_as(self, name):
        """Mengisi cookie session langsung (seolah sudah login) plus token CSRF."""
        with self.client.session_transaction() as cookie:
            cookie["user_id"] = self.users[name].id
            cookie["csrf_token"] = TOKEN

    def post(self, url, data=None):
        payload = dict(data or {})
        payload["csrf_token"] = TOKEN
        return self.client.post(url, data=payload)

    def session_form(self, **overrides):
        data = {
            "title": "Belajar Struktur Data", "subject": "Struktur Data", "topic": "",
            "description": "", "mode": "OFFLINE", "location_text": "Perpustakaan Pusat",
            "map_url": "", "meeting_url": "", "capacity": "3", **FUTURE,
        }
        data.update(overrides)
        return data

    def create_session_as_host(self, **overrides):
        self.login_as("host")
        response = self.post("/sessions/new", self.session_form(**overrides))
        self.assertEqual(response.status_code, 302)
        return response.headers["Location"].rsplit("/", 1)[-1]

    def status_of(self, session_id):
        conn = storage.connect(self.db_path)
        status = storage.get_session(conn, session_id).status
        conn.close()
        return status

    # --- Test --------------------------------------------------------------
    def test_index_empty_state(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Belum ada sesi yang tersedia", response.get_data(as_text=True))

    def test_create_requires_login(self):
        response = self.client.get("/sessions/new")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_post_without_csrf_rejected(self):
        self.login_as("host")
        response = self.client.post("/sessions/new", data=self.session_form())
        self.assertEqual(response.status_code, 400)

    def test_invalid_form_shows_errors(self):
        self.login_as("host")
        response = self.post("/sessions/new", self.session_form(title="", capacity="abc"))
        self.assertEqual(response.status_code, 400)
        html = response.get_data(as_text=True)
        self.assertIn("Judul wajib diisi", html)
        self.assertIn('aria-invalid="true"', html)

    def test_demo_flow(self):
        # Alur demo blueprint §21.1 (kapasitas 3 = host + 2 peserta).
        session_id = self.create_session_as_host()
        self.assertIn("Belajar Struktur Data", self.client.get("/").get_data(as_text=True))

        self.login_as("budi")
        self.post(f"/sessions/{session_id}/join")
        page = self.client.get(f"/sessions/{session_id}").get_data(as_text=True)
        self.assertIn("Berhasil bergabung", page)

        self.post(f"/sessions/{session_id}/join")
        page = self.client.get(f"/sessions/{session_id}").get_data(as_text=True)
        self.assertIn("sudah bergabung", page)

        self.login_as("citra")
        self.post(f"/sessions/{session_id}/join")

        self.login_as("dewi")
        self.post(f"/sessions/{session_id}/join")
        page = self.client.get(f"/sessions/{session_id}").get_data(as_text=True)
        self.assertIn("Sesi sudah penuh", page)

        self.login_as("host")
        self.post(f"/sessions/{session_id}/cancel")
        self.assertEqual(self.status_of(session_id), "CANCELLED")

    def test_non_host_cannot_cancel(self):
        session_id = self.create_session_as_host()
        self.login_as("budi")
        self.post(f"/sessions/{session_id}/cancel")
        page = self.client.get(f"/sessions/{session_id}").get_data(as_text=True)
        self.assertIn("Hanya host", page)
        self.assertEqual(self.status_of(session_id), STATUS_OPEN)

    def test_meeting_link_hidden_until_joined(self):
        session_id = self.create_session_as_host(
            mode="ONLINE", location_text="", meeting_url="https://meet.google.com/rahasia"
        )
        self.login_as("budi")
        self.assertNotIn("meet.google.com/rahasia", self.client.get(f"/sessions/{session_id}").get_data(as_text=True))
        self.post(f"/sessions/{session_id}/join")
        self.assertIn("meet.google.com/rahasia", self.client.get(f"/sessions/{session_id}").get_data(as_text=True))

    def test_user_text_is_escaped(self):
        session_id = self.create_session_as_host(title="<script>alert(1)</script>")
        html = self.client.get(f"/sessions/{session_id}").get_data(as_text=True)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_unknown_session_404(self):
        self.assertEqual(self.client.get("/sessions/tidak-ada").status_code, 404)

    def test_login_ignores_external_next(self):
        with self.client.session_transaction() as cookie:
            cookie["csrf_token"] = TOKEN
        response = self.post("/login", {"user_id": self.users["budi"].id, "next": "https://jahat.example"})
        self.assertEqual(response.headers["Location"], "/")

    def test_vercel_refuses_unsafe_config(self):
        from app import config
        original = (config.IS_VERCEL, config.SECRET_KEY, config.DATABASE_URL)
        try:
            config.IS_VERCEL = True
            config.SECRET_KEY = config.DEV_SECRET_KEY
            config.DATABASE_URL = "postgresql://contoh"
            with self.assertRaises(RuntimeError):
                create_app()  # SECRET_KEY masih default
            config.SECRET_KEY = "rahasia-acak"
            config.DATABASE_URL = ""
            with self.assertRaises(RuntimeError):
                create_app()  # DATABASE_URL kosong
        finally:
            config.IS_VERCEL, config.SECRET_KEY, config.DATABASE_URL = original

    def test_search_no_result(self):
        self.create_session_as_host()
        html = self.client.get("/?q=biologi").get_data(as_text=True)
        self.assertIn("Tidak ada sesi yang cocok", html)


if __name__ == "__main__":
    unittest.main()
