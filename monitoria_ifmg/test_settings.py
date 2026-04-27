from .settings import *  # noqa

TEST_DB_PATH = BASE_DIR / "test_db.sqlite3"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": TEST_DB_PATH,
    }
}

DEBUG = False

