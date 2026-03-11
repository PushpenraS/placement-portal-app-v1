# models/drive.py
from datetime import datetime, UTC
from extensions import db


class PlacementDrive(db.Model):
    __tablename__ = "placement_drives"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    job_title = db.Column(db.String(255), nullable=False)
    job_description = db.Column(db.Text, nullable=False)
    salary = db.Column(db.Integer, nullable=False)
    location = db.Column(db.String(255), nullable=False)
    eligibility_criteria = db.Column(db.Text, nullable=False)
    application_deadline = db.Column(db.DateTime, nullable=False)
    status = db.Column(
        db.Integer, nullable=False, default=1
    )  # cancelled-0/ongoing-1/closed-2/pending-3/rejected-4
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(UTC))

    employer_id = db.Column(
        db.Integer, db.ForeignKey("employers.id"), nullable=False, index=True
    )

    applications = db.relationship("Application", cascade="all, delete-orphan")
    employer = db.relationship("Employer", back_populates="placement_drives")
