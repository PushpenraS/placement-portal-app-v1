import os
from .config import Config

basedir = os.path.abspath(os.path.dirname(__file__))


class LocalDevelopmentConfig(Config):
    SQLITE_DB_DIR = os.path.join(basedir, "../instance")
    SQLALCHEMY_DATABASE_URI = (
        f"sqlite:///{os.path.join(SQLITE_DB_DIR, 'placement_portal.sqlite3')}"
    )
    DEBUG = True
    SECRET_KEY = "23YJSLjdyqoz93ljdzb"  # Read from an environment file
    SECURITY_PASSWORD_SALT = "JUST_IN_TIME"  # Read from an environment file
    SECURITY_PASSWORD_HASH = "argon2"
    # AUTO_SEED = str(os.getenv("AUTO_SEED", "true")).strip().lower() == "true"
