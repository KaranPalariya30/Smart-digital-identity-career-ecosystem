"""Keep tests off the developer's real database and give them a valid SECRET_KEY."""
import os
import tempfile

os.environ.setdefault("SECRET_KEY", "ci-test-secret-key-at-least-32-characters")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.mkdtemp()}/auth-test.db")
