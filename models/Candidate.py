# models/candidate.py
from extensions import db

class Candidate(db.Model):
    __tablename__ = "candidates"

    id = db.Column(db.Integer, primary_key=True)

    full_name = db.Column(db.String(100), nullable=False)
    qualification = db.Column(db.String(120))
    skills = db.Column(db.Text)
    resume_path = db.Column(db.String(255))
    dob = db.Column(db.Date)
    
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)

    user = db.relationship("User", back_populates="candidate_profile")
    applications = db.relationship("Application", back_populates="candidate", cascade="all, delete-orphan")
