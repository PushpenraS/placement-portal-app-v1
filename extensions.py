from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def to_date_only(dt):
    return dt.strftime("%Y-%m-%d") if dt else None
