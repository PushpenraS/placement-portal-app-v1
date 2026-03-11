from extensions import db
from datetime import datetime, UTC
from flask_security import UserMixin


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(UTC))
    fs_uniquifier = db.Column(db.String(255), unique=True, nullable=False)
    fs_token_uniquifier = db.Column(db.String(255), unique=True, nullable=True)

    roles = db.relationship("Role", secondary="roles_users", back_populates="users")
    employer_profile = db.relationship(
        "Employer", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    candidate_profile = db.relationship(
        "Candidate", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
