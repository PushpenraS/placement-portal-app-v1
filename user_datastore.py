from flask_security import SQLAlchemyUserDatastore

from extensions import db
from models import Role, User

user_datastore = SQLAlchemyUserDatastore(db, User, Role)
