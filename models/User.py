from extensions import db
from datetime import datetime, UTC

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    is_blacklisted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(UTC))

    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)

    role = db.relationship("Role")
    employer_profile = db.relationship("Employer", back_populates="user", uselist=False, cascade="all, delete-orphan")
    candidate_profile = db.relationship("Candidate", back_populates="user", uselist=False, cascade="all, delete-orphan")
