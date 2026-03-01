# models/drive.py
from datetime import datetime, UTC
from extensions import db

class PlacementDrive(db.Model):
    __tablename__ = "placement_drives"

    id = db.Column(db.Integer, primary_key=True)

    job_title = db.Column(db.String(120), nullable=False)
    job_description = db.Column(db.Text, nullable=False)
    eligibility_criteria = db.Column(db.Text)
    application_deadline = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")  # pending/approved/closed
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(UTC))

    employer_id = db.Column(db.Integer, db.ForeignKey("employers.id"), nullable=False, index=True)

    applications = db.relationship("Application", back_populates="placement_drives", cascade="all, delete-orphan")
