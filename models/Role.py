from extensions import db

class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True, autoincrement = True)
    name = db.Column(db.String(32), unique=True, nullable=False)  # admin/employer/candidate
    description = db.Column(db.String(255))
