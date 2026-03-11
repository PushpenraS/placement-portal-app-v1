from extensions import db
from flask_security import RoleMixin


class Role(db.Model, RoleMixin):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(
        db.String(50), unique=True, nullable=False
    )  # admin/employer/candidate
    description = db.Column(db.String(255))

    users = db.relationship("User", secondary="roles_users", back_populates="roles")
