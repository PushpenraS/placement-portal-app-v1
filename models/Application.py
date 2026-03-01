# models/application.py
from datetime import datetime
from extensions import db

class Application(db.Model):
    __tablename__ = "applications"
    __table_args__ = (
        db.UniqueConstraint("candidate_id", "placement_drive_id", name="uq_application_candidate_drive"),
    )

    id = db.Column(db.Integer, primary_key=True)
    applied_at = db.Column(db.DateTime, nullable=False, default=datetime.UTC)
    status = db.Column(db.String(20), nullable=False, default="applied")  # applied/shortlisted/selected/rejected

    candidate_id = db.Column(db.Integer, db.ForeignKey("candidates.id"), nullable=False, index=True)
    placement_drive_id = db.Column(db.Integer, db.ForeignKey("placement_drives.id"), nullable=False, index=True)
