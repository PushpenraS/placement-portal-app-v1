from flask import Flask
from flask_restful import Api
from flask_security import Security, SQLAlchemyUserDatastore
from configuration import LocalDevelopmentConfig
from extensions import db
from models import *
from controllers import register_blueprints
from user_datastore import user_datastore
import os


def create_app():
    app = Flask(__name__, template_folder="templates")
    app.config.from_object(LocalDevelopmentConfig)

    os.makedirs(app.config["SQLITE_DB_DIR"], exist_ok=True)

    db.init_app(app)
    register_blueprints(app)

    Security(app, user_datastore)
    api = Api(app)

    create_database(app, user_datastore)

    return app, api


def create_database(app: Flask, datastore: SQLAlchemyUserDatastore):
    with app.app_context():
        db.create_all()

        admin_role = datastore.find_or_create_role(
            name="admin", description="Admin Role"
        )

        datastore.find_or_create_role(name="employer", description="Employer Role")

        datastore.find_or_create_role(name="candidate", description="Candidate Role")

        if not datastore.find_user(email="admin@admin.com"):
            datastore.create_user(
                email="admin@admin.com", password="admin", roles=[admin_role]
            )

        db.session.commit()


app, api = create_app()

from api import *

api.add_resource(LoginUser, "/api/login")
api.add_resource(EmailAvailability, "/api/check-email")
api.add_resource(LogoutUser, "/api/logout")
api.add_resource(RegisterCandidate, "/api/register/candidate")
api.add_resource(RegisterEmployer, "/api/register/employer")
api.add_resource(
    AdminEmployerResource,
    "/api/admin/employer",
    "/api/admin/employer/<string:approval_status>",
)
api.add_resource(AdminCandidateResource, "/api/admin/candidate")
api.add_resource(AdminPlacementDriveItemResource, "/api/admin/drive/<int:drive_id>")
api.add_resource(AdminPlacementDriveListResource, "/api/admin/drive")
api.add_resource(
    AdminCandidateApplicationItemResource,
    "/api/admin/candidate/application/<int:application_id>",
)
api.add_resource(
    AdminCandidateApplicationListResource, "/api/admin/candidate/application"
)
api.add_resource(EmployerResource, "/api/employer/profile")
api.add_resource(EmployerPlacementDriveResource, "/api/employer/drive")
api.add_resource(
    EmployerPlacementDriveItemResource, "/api/employer/drive/item/<int:drive_id>"
)
api.add_resource(
    EmployerDriveApplicationListResource,
    "/api/employer/drive/<int:drive_id>/application",
)
api.add_resource(
    EmployerApplicationItemResource, "/api/employer/application/<int:application_id>"
)
api.add_resource(CandidateResource, "/api/candidate/profile")
api.add_resource(CandidateEmployerListResource, "/api/candidate/employer")
api.add_resource(
    CandidateEmployerItemResource, "/api/candidate/employer/<int:employer_id>"
)
api.add_resource(CandidateDriveItemResource, "/api/candidate/drive/<int:drive_id>")
api.add_resource(
    CandidateDriveApplicationResource,
    "/api/candidate/drive/<int:drive_id>/apply",
    "/api/candidate/drive/application/check/<int:drive_id>",
)
api.add_resource(CandidateAppliedDriveListResource, "/api/candidate/application")
api.add_resource(CandidateApplicationHistoryResource, "/api/candidate/history")

if __name__ == "__main__":
    app.run(debug=True)
