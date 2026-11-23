import unittest


class SmokeTest(unittest.TestCase):
    def test_app_package_imports(self):
        import app  # noqa: F401
        from app import config, models, storage, validation, web  # noqa: F401
        from app.services import enrollment_service, session_service  # noqa: F401


if __name__ == "__main__":
    unittest.main()
