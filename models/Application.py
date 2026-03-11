# models/application.py
from datetime import datetime, UTC
from extensions import db


class Application(db.Model):
    __tablename__ = "applications"
    __table_args__ = (
        db.UniqueConstraint(
            "candidate_id", "placement_drive_id", name="uq_application_candidate_drive"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    applied_at = db.Column(db.DateTime, nullable=False, default=datetime.now(UTC))
    status = db.Column(
        db.Integer, nullable=False, default=1
    )  # applied - 1/shortlisted - 2/selected - 3/rejected - 4/cancelled - 0

    candidate_id = db.Column(
        db.Integer, db.ForeignKey("candidates.id"), nullable=False, index=True
    )
    placement_drive_id = db.Column(
        db.Integer, db.ForeignKey("placement_drives.id"), nullable=False, index=True
    )

    candidate = db.relationship("Candidate", back_populates="applications")
    placement_drive = db.relationship("PlacementDrive", back_populates="applications")
