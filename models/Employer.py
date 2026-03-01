from extensions import db

class Employer(db.Model):
    __tablename__ = "employers"

    id = db.Column(db.Integer, autoincrement = True, primary_key=True)

    name = db.Column(db.String(120), nullable=False, index=True)
    hr_contact = db.Column(db.String(120))
    website = db.Column(db.String(255))
    approval_status = db.Column(db.String(20), nullable=False, default="pending")  # pending/approved
    industry = db.Column(db.String(100), nullable = False)
    location = db.Column(db.String(50), nullable = False)
    about = db.Column(db.String(500))

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)

    user = db.relationship("User", back_populates="employer_profile")
    placement_drives = db.relationship("PlacementDrive", cascade="all, delete-orphan")