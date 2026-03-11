from datetime import datetime

from flask import jsonify, make_response, request
from flask_restful import Resource
from flask_security import auth_token_required, current_user, roles_required

from extensions import db, to_date_only
from models import Application, Candidate, Employer, PlacementDrive

DRIVE_STATUS_MAP = {"cancelled": 0, "ongoing": 1, "closed": 2}
REV_DRIVE_STATUS_MAP = {value: key for key, value in DRIVE_STATUS_MAP.items()}

APP_STATUS_MAP = {
    "cancelled": 0,
    "applied": 1,
    "shortlisted": 2,
    "selected": 3,
    "rejected": 4,
}
REV_APP_STATUS_MAP = {value: key for key, value in APP_STATUS_MAP.items()}


def _current_employer_id():
    employer_profile = getattr(current_user, "employer_profile", None)
    return employer_profile.id if employer_profile else None


class EmployerResource(Resource):
    @auth_token_required
    @roles_required("employer")
    def get(self):
        current_employer_id = _current_employer_id()
        if not current_employer_id:
            return make_response(jsonify({"message": "Forbidden"}), 403)

        employer = Employer.query.filter_by(id=current_employer_id).first()

        if not employer:
            return make_response(
                jsonify(
                    {
                        "message": f"Employer with id {current_employer_id} does not exist"
                    }
                ),
                404,
            )
        result = {
            "employer_id": employer.id,
            "name": employer.name,
            "email": employer.user.email if employer.user else None,
            "approval_status": employer.approval_status,
            "active": employer.user.active if employer.user else None,
            "about": employer.about,
            "industry": employer.industry,
            "location": employer.location,
            "website": employer.website,
        }

        return make_response(jsonify(result), 200)

    @auth_token_required
    @roles_required("employer")
    def put(self):
        current_employer_id = _current_employer_id()
        if not current_employer_id:
            return make_response(jsonify({"message": "Forbidden"}), 403)

        employer = Employer.query.filter_by(id=current_employer_id).first()

        if not employer:
            return make_response(
                jsonify(
                    {
                        "message": f"Employer with id {current_employer_id} does not exist"
                    }
                ),
                404,
            )

        payload = request.get_json()

        if not payload:
            return make_response(jsonify({"message": "Invalid Operation"}), 400)

        employer.about = payload.get("about")
        employer.industry = payload.get("industry")
        employer.location = payload.get("location")
        employer.website = payload.get("website")

        try:
            db.session.commit()
        except Exception as ex:
            return make_response(jsonify({"message": str(ex)}), 400)

        return make_response(jsonify({"message": "Profile updated successfully"}), 200)


class EmployerPlacementDriveResource(Resource):
    # GET: list employer drives (ongoing/closed)
    # POST: create a new drive
    @auth_token_required
    @roles_required("employer")
    def get(self):
        current_employer_id = _current_employer_id()
        if not current_employer_id:
            return make_response(jsonify({"message": "Forbidden"}), 403)

        drive_status = (request.args.get("status") or "ongoing").strip().lower()
        if drive_status not in {"ongoing", "closed"}:
            return make_response(
                jsonify({"message": "Valid status required: ongoing/closed"}), 400
            )

        drives = (
            PlacementDrive.query.filter_by(
                employer_id=current_employer_id, status=DRIVE_STATUS_MAP[drive_status]
            )
            .order_by(PlacementDrive.id.desc())
            .all()
        )
        result = []
        for drive in drives:
            result.append(
                {
                    "drive_id": drive.id,
                    "name": drive.name,
                    "job_title": drive.job_title,
                    "status": REV_DRIVE_STATUS_MAP.get(drive.status, "unknown"),
                    "application_deadline": to_date_only(drive.application_deadline),
                }
            )
        return make_response(jsonify(result), 200)

    @auth_token_required
    @roles_required("employer")
    def post(self):
        payload = request.get_json() or {}
        current_employer_id = _current_employer_id()
        if not current_employer_id:
            return make_response(jsonify({"message": "Forbidden"}), 403)

        name = (payload.get("name") or "").strip()
        job_title = (payload.get("job_title") or "").strip()
        job_description = (payload.get("job_description") or "").strip()
        location = (payload.get("location") or "").strip()
        eligibility_criteria = (payload.get("eligibility_criteria") or "").strip()
        application_deadline_str = (payload.get("application_deadline") or "").strip()
        salary = payload.get("salary")

        if not name or not job_title or not job_description:
            return make_response(
                jsonify({"message": "Valid name/job_title/job_description required"}),
                400,
            )
        if not location or not eligibility_criteria:
            return make_response(
                jsonify({"message": "Valid location/eligibility_criteria required"}),
                400,
            )
        if salary is None:
            return make_response(jsonify({"message": "Valid salary required"}), 400)
        if not application_deadline_str:
            return make_response(
                jsonify(
                    {"message": "Valid application_deadline required in YYYY-MM-DD"}
                ),
                400,
            )

        employer: Employer = Employer.query.filter_by(id=current_employer_id).first()
        if not employer:
            return make_response(
                jsonify(
                    {
                        "message": f"Employer with id {current_employer_id} does not exist"
                    }
                ),
                404,
            )

        if employer.user.active == 0:
            return make_response(
                jsonify(
                    {
                        "message": f"privilege for Employer with id {current_employer_id} is either yet to be approved or has been revoked."
                    }
                ),
                404,
            )

        try:
            application_deadline = datetime.strptime(
                application_deadline_str, "%Y-%m-%d"
            )
        except ValueError:
            return make_response(
                jsonify(
                    {"message": "Valid application_deadline required in YYYY-MM-DD"}
                ),
                400,
            )

        new_drive = PlacementDrive(
            name=name,
            job_title=job_title,
            job_description=job_description,
            salary=salary,
            location=location,
            eligibility_criteria=eligibility_criteria,
            application_deadline=application_deadline,
            employer_id=current_employer_id,
            status=DRIVE_STATUS_MAP["ongoing"],
        )
        db.session.add(new_drive)

        try:
            db.session.commit()
        except Exception as ex:
            return make_response(jsonify({"message": str(ex)}), 400)

        return make_response(
            jsonify(
                {
                    "message": "Drive created successfully",
                    "details": {
                        "drive_id": new_drive.id,
                        "name": new_drive.name,
                        "job_title": new_drive.job_title,
                        "status": REV_DRIVE_STATUS_MAP[new_drive.status],
                    },
                }
            ),
            201,
        )


class EmployerPlacementDriveItemResource(Resource):
    # GET: view details of one drive
    # PATCH: mark ongoing drive as complete (closed)
    @auth_token_required
    @roles_required("employer")
    def get(self, drive_id):
        current_employer_id = _current_employer_id()
        drive = PlacementDrive.query.filter_by(id=drive_id).first()
        if not drive:
            return make_response(
                jsonify({"message": f"Drive with id {drive_id} does not exist"}), 404
            )
        if not current_employer_id or drive.employer_id != current_employer_id:
            return make_response(jsonify({"message": "Forbidden"}), 403)

        return make_response(
            jsonify(
                {
                    "drive_id": drive.id,
                    "name": drive.name,
                    "job_title": drive.job_title,
                    "job_description": drive.job_description,
                    "salary": drive.salary,
                    "location": drive.location,
                    "eligibility_criteria": drive.eligibility_criteria,
                    "application_deadline": to_date_only(drive.application_deadline),
                    "status": REV_DRIVE_STATUS_MAP.get(drive.status, "unknown"),
                    "employer_id": drive.employer_id,
                    "employer_name": drive.employer.name if drive.employer else None,
                }
            ),
            200,
        )

    # PATCH: mark ongoing drive as complete (no body required)
    @auth_token_required
    @roles_required("employer")
    def patch(self, drive_id):
        current_employer_id = _current_employer_id()
        drive = PlacementDrive.query.filter_by(id=drive_id).first()
        if not drive:
            return make_response(
                jsonify({"message": f"Drive with id {drive_id} does not exist"}), 404
            )
        if not current_employer_id or drive.employer_id != current_employer_id:
            return make_response(jsonify({"message": "Forbidden"}), 403)
        if drive.status != DRIVE_STATUS_MAP["ongoing"]:
            return make_response(
                jsonify({"message": "Only ongoing drives can be marked complete"}), 400
            )

        applications = Application.query.filter(
            Application.placement_drive_id == drive_id,
            Application.status.in_(
                [APP_STATUS_MAP["applied"], APP_STATUS_MAP["shortlisted"]]
            ),
        ).all()

        application: Application

        for application in applications:
            application.status = APP_STATUS_MAP["rejected"]

        drive.status = DRIVE_STATUS_MAP["closed"]

        try:
            db.session.commit()
        except Exception as ex:
            return make_response(jsonify({"message": str(ex)}), 400)

        return make_response(
            jsonify(
                {
                    "message": "Drive marked as complete",
                    "details": {
                        "drive_id": drive.id,
                        "status": REV_DRIVE_STATUS_MAP[drive.status],
                    },
                }
            ),
            200,
        )


class EmployerDriveApplicationListResource(Resource):
    # GET: list applications received for one drive
    @auth_token_required
    @roles_required("employer")
    def get(self, drive_id):
        current_employer_id = _current_employer_id()
        drive = PlacementDrive.query.filter_by(id=drive_id).first()
        if not drive:
            return make_response(
                jsonify({"message": f"Drive with id {drive_id} does not exist"}), 404
            )
        if not current_employer_id or drive.employer_id != current_employer_id:
            return make_response(jsonify({"message": "Forbidden"}), 403)

        status_key = (request.args.get("status") or "").strip().lower()
        if status_key:
            if status_key == "active":
                status_values = [
                    APP_STATUS_MAP["applied"],
                    APP_STATUS_MAP["shortlisted"],
                ]
                applications = Application.query.filter(
                    Application.placement_drive_id == drive_id,
                    Application.status.in_(status_values),
                ).all()
            elif status_key in APP_STATUS_MAP:
                applications = Application.query.filter_by(
                    placement_drive_id=drive_id, status=APP_STATUS_MAP[status_key]
                ).all()
            else:
                return make_response(
                    jsonify(
                        {
                            "message": "Valid status required: active/applied/shortlisted/selected/rejected/cancelled"
                        }
                    ),
                    400,
                )
        else:
            applications = Application.query.filter(
                Application.placement_drive_id == drive_id,
                Application.status.in_(
                    [APP_STATUS_MAP["applied"], APP_STATUS_MAP["shortlisted"]]
                ),
            ).all()

        result = []
        for app in applications:
            candidate = app.candidate
            result.append(
                {
                    "application_id": app.id,
                    "candidate_id": candidate.id if candidate else None,
                    "candidate_name": candidate.full_name if candidate else None,
                    "status": REV_APP_STATUS_MAP.get(app.status, "unknown"),
                    "applied_at": to_date_only(app.applied_at),
                }
            )

        return make_response(
            jsonify(
                {
                    "drive_id": drive.id,
                    "drive_name": drive.name,
                    "job_title": drive.job_title,
                    "applications": result,
                }
            ),
            200,
        )


class EmployerApplicationItemResource(Resource):
    # GET: review one student application
    # PATCH: update application status from employer review screen
    @auth_token_required
    @roles_required("employer")
    def get(self, application_id):
        current_employer_id = _current_employer_id()
        app = Application.query.filter_by(id=application_id).first()
        if not app:
            return make_response(
                jsonify(
                    {"message": f"Application with id {application_id} does not exist"}
                ),
                404,
            )

        candidate: Candidate = app.candidate
        drive: PlacementDrive = app.placement_drive
        if (
            not current_employer_id
            or not drive
            or drive.employer_id != current_employer_id
        ):
            return make_response(jsonify({"message": "Forbidden"}), 403)

        return make_response(
            jsonify(
                {
                    "application_id": app.id,
                    "status": REV_APP_STATUS_MAP.get(app.status, "unknown"),
                    "candidate": {
                        "candidate_id": candidate.id if candidate else None,
                        "full_name": candidate.full_name if candidate else None,
                        "qualification": candidate.qualification if candidate else None,
                        "skills": candidate.skills if candidate else None,
                        "resume_path": candidate.resume_path if candidate else None,
                    },
                    "drive": {
                        "drive_id": drive.id if drive else None,
                        "name": drive.name if drive else None,
                        "job_title": drive.job_title if drive else None,
                        "employer_id": drive.employer_id if drive else None,
                    },
                }
            ),
            200,
        )

    # PATCH body: {"status":"shortlisted|rejected|selected","employer_id":<id>}
    @auth_token_required
    @roles_required("employer")
    def patch(self, application_id):
        current_employer_id = _current_employer_id()
        app = Application.query.filter_by(id=application_id).first()
        if not app:
            return make_response(
                jsonify(
                    {"message": f"Application with id {application_id} does not exist"}
                ),
                404,
            )

        payload = request.get_json() or {}
        employer_id = payload.get("employer_id")
        next_status = (payload.get("status") or "").strip().lower()
        if not current_employer_id:
            return make_response(jsonify({"message": "Forbidden"}), 403)
        if employer_id and int(employer_id) != current_employer_id:
            return make_response(jsonify({"message": "Forbidden"}), 403)
        if next_status not in {"shortlisted", "rejected", "selected"}:
            return make_response(
                jsonify(
                    {"message": "Valid status required: shortlisted/rejected/selected"}
                ),
                400,
            )

        drive = app.placement_drive
        if not drive or drive.employer_id != current_employer_id:
            return make_response(
                jsonify({"message": "Employer cannot update this application"}), 403
            )

        status_translation = {
            "shortlisted": APP_STATUS_MAP["shortlisted"],
            "rejected": APP_STATUS_MAP["rejected"],
            "selected": APP_STATUS_MAP["selected"],
        }

        new_status = status_translation[next_status]
        current_status = app.status

        if current_status in [
            APP_STATUS_MAP["cancelled"],
            APP_STATUS_MAP["selected"],
            APP_STATUS_MAP["rejected"],
        ]:
            return make_response(
                jsonify(
                    {"message": "Application cannot be updated from current status"}
                ),
                400,
            )

        allowed_transitions = {
            APP_STATUS_MAP["applied"]: [
                APP_STATUS_MAP["shortlisted"],
                APP_STATUS_MAP["rejected"],
            ],
            APP_STATUS_MAP["shortlisted"]: [
                APP_STATUS_MAP["selected"],
                APP_STATUS_MAP["rejected"],
            ],
        }

        if new_status not in allowed_transitions.get(current_status, []):
            return make_response(
                jsonify(
                    {
                        "message": "Invalid status transition. Allowed: applied->(shortlisted/rejected), shortlisted->(selected/rejected)"
                    }
                ),
                400,
            )

        app.status = new_status
        try:
            db.session.commit()
        except Exception as ex:
            return make_response(jsonify({"message": str(ex)}), 400)

        return make_response(
            jsonify(
                {
                    "message": "Application updated successfully",
                    "details": {
                        "application_id": app.id,
                        "status": REV_APP_STATUS_MAP.get(app.status, "unknown"),
                    },
                }
            ),
            200,
        )
