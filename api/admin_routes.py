from flask import jsonify, make_response, request
from flask_restful import Resource
from flask_security import auth_token_required, roles_required

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


class AdminEmployerResource(Resource):
    # Returns list of employers/companies.
    @auth_token_required
    @roles_required("admin")
    def get(self, approval_status=None):
        employers = None
        if not approval_status:
            employers = Employer.query.filter_by(approval_status="approved").all()
        else:
            if approval_status not in {"pending", "approved"}:
                return make_response(
                    jsonify(
                        {"message": "Valid approval_status required: pending/approved"}
                    ),
                    400,
                )
            employers = Employer.query.filter_by(approval_status=approval_status).all()

        result = []
        for employer in employers:
            result.append(
                {
                    "employer_id": employer.id,
                    "name": employer.name,
                    "approval_status": employer.approval_status,
                    "active": employer.user.active if employer.user else None,
                }
            )
        return make_response(jsonify(result), 200)

    # PATCH body:
    # {"employer_id": 1, "action": "approve"} or {"employer_id": 1, "action": "deactivate"} or {"employer_id": 1, "action": "activate"}
    @auth_token_required
    @roles_required("admin")
    def patch(self):
        payload = request.get_json()

        if not payload:
            return make_response(jsonify({"message": "Invalid Operation"}), 400)

        employer_id = payload.get("employer_id")
        action = payload.get("action")

        if not action:
            return make_response(
                jsonify(
                    {"message": "Valid action required: approve/deactivate/activate"}
                ),
                400,
            )
        else:
            action = action.strip().lower()

        if not employer_id:
            return make_response(
                jsonify({"message": "Valid employer_id required"}), 400
            )
        if action not in {"approve", "deactivate", "activate"}:
            return make_response(
                jsonify(
                    {"message": "Valid action required: approve/deactivate/activate"}
                ),
                400,
            )

        employer = Employer.query.filter_by(id=employer_id).first()
        if not employer:
            return make_response(
                jsonify({"message": f"Employer with id {employer_id} does not exist"}),
                404,
            )

        if (
            action in {"deactivate", "activate"}
            and employer.approval_status != "approved"
        ):
            return make_response(
                jsonify(
                    {
                        "message": "Only approved employers can be activated or deactivated"
                    }
                ),
                400,
            )

        if action == "approve":
            employer.approval_status = "approved"
            if employer.user:
                employer.user.active = True
        elif action == "deactivate":
            if employer.user:
                employer.user.active = False
            active_drives = PlacementDrive.query.filter_by(
                employer_id=employer.id, status=DRIVE_STATUS_MAP["ongoing"]
            ).all()
            for drive in active_drives:
                drive.status = DRIVE_STATUS_MAP["cancelled"]
        else:
            if employer.user:
                employer.user.active = True

        try:
            db.session.commit()
        except Exception as ex:
            return make_response(jsonify({"message": str(ex)}), 400)

        return make_response(
            jsonify(
                {
                    "message": f"Employer {action}d successfully",
                    "details": {
                        "employer_id": employer.id,
                        "approval_status": (
                            employer.approval_status
                            if employer.user.active == 1
                            else None
                        ),
                        "active": employer.user.active if employer.user else None,
                    },
                }
            ),
            200,
        )


class AdminCandidateResource(Resource):
    # Returns list of candidates/students.
    @auth_token_required
    @roles_required("admin")
    def get(self):
        rows = Candidate.query.order_by(Candidate.id.desc()).all()
        result = []
        for candidate in rows:
            result.append(
                {
                    "candidate_id": candidate.id,
                    "full_name": candidate.full_name,
                    "email": candidate.user.email if candidate.user else None,
                    "active": candidate.user.active if candidate.user else None,
                }
            )
        return make_response(jsonify(result), 200)

    # PATCH body:
    # {"candidate_id": 1, "action": "deactivate"} or {"candidate_id": 1, "action": "activate"}
    @auth_token_required
    @roles_required("admin")
    def patch(self):
        payload = request.get_json()

        if not payload:
            return make_response(jsonify({"message": "Invalid Operation"}), 400)

        candidate_id = payload.get("candidate_id")
        action = payload.get("action")

        if not action:
            return make_response(
                jsonify({"message": "Valid action required: deactivate/activate"}), 400
            )
        else:
            action = action.strip().lower()

        if not candidate_id:
            return make_response(
                jsonify({"message": "Valid candidate_id required"}), 400
            )
        if action not in {"deactivate", "activate"}:
            return make_response(
                jsonify({"message": "Valid action required: deactivate/activate"}), 400
            )

        candidate = Candidate.query.filter_by(id=candidate_id).first()
        if not candidate:
            return make_response(
                jsonify(
                    {"message": f"Candidate with id {candidate_id} does not exist"}
                ),
                404,
            )

        if not candidate.user:
            return make_response(
                jsonify(
                    {"message": f"Candidate user profile missing for {candidate_id}"}
                ),
                400,
            )

        candidate.user.active = action == "activate"

        if action == "deactivate":
            active_candidate_apps = Application.query.filter(
                Application.candidate_id == candidate.id,
                Application.status.in_(
                    [APP_STATUS_MAP["applied"], APP_STATUS_MAP["shortlisted"]]
                ),
            ).all()
            for application in active_candidate_apps:
                application.status = APP_STATUS_MAP["cancelled"]

        try:
            db.session.commit()
        except Exception as ex:
            return make_response(jsonify({"message": str(ex)}), 400)

        return make_response(
            jsonify(
                {
                    "message": f"Candidate {action}d successfully",
                    "details": {
                        "candidate_id": candidate.id,
                        "active": candidate.user.active,
                    },
                }
            ),
            200,
        )


class AdminPlacementDriveItemResource(Resource):
    # Returns full details of an individual drive.
    @auth_token_required
    @roles_required("admin")
    def get(self, drive_id):
        drive = PlacementDrive.query.filter_by(id=drive_id).first()
        if not drive:
            return make_response(
                jsonify({"message": f"Drive with id {drive_id} does not exist"}), 404
            )

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
                    "status": REV_DRIVE_STATUS_MAP[drive.status],
                    "employer_id": drive.employer_id,
                    "employer_name": drive.employer.name if drive.employer else None,
                }
            ),
            200,
        )

    # Closes an ongoing drive ("mark as complete").
    # PATCH body: {"action": "mark_complete"} (optional)
    @auth_token_required
    @roles_required("admin")
    def patch(self, drive_id):
        drive = PlacementDrive.query.filter_by(id=drive_id).first()
        if not drive:
            return make_response(
                jsonify({"message": f"Drive with id {drive_id} does not exist"}), 404
            )

        payload = request.get_json(silent=True) or {}
        action = (payload.get("action") or "mark_complete").strip().lower()
        if action != "mark_complete":
            return make_response(
                jsonify({"message": "Valid action required: mark_complete"}), 400
            )

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
                    "message": "Drive marked as complete successfully",
                    "details": {
                        "drive_id": drive.id,
                        "status": REV_DRIVE_STATUS_MAP[drive.status],
                    },
                }
            ),
            200,
        )


class AdminPlacementDriveListResource(Resource):
    # Returns ongoing drives for admin dashboard "Ongoing Drives" table.
    @auth_token_required
    @roles_required("admin")
    def get(self):
        ongoing_drives = (
            PlacementDrive.query.filter_by(status=DRIVE_STATUS_MAP["ongoing"])
            .order_by(PlacementDrive.id.desc())
            .all()
        )

        result = []
        for drive in ongoing_drives:
            result.append({"drive_id": drive.id, "name": drive.name})
        return make_response(jsonify(result), 200)


class AdminCandidateApplicationItemResource(Resource):
    # Returns details for admin "view" action on one application.
    @auth_token_required
    @roles_required("admin")
    def get(self, application_id):
        app = Application.query.filter_by(id=application_id).first()
        if not app:
            return make_response(
                jsonify(
                    {"message": f"Application with id {application_id} does not exist"}
                ),
                404,
            )

        candidate = app.candidate
        drive = app.placement_drive
        employer = drive.employer if drive else None

        return make_response(
            jsonify(
                {
                    "application_id": app.id,
                    "status": REV_APP_STATUS_MAP.get(app.status, "unknown"),
                    "applied_at": to_date_only(app.applied_at),
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
                        "employer_name": employer.name if employer else None,
                    },
                }
            ),
            200,
        )


class AdminCandidateApplicationListResource(Resource):
    # Returns applications for admin "Candidate Applications" table.
    @auth_token_required
    @roles_required("admin")
    def get(self):
        applications = Application.query.order_by(Application.id.desc()).all()

        result = []
        for app in applications:
            candidate = app.candidate
            drive = app.placement_drive
            employer = drive.employer if drive else None

            result.append(
                {
                    "application_id": app.id,
                    "candidate_name": candidate.full_name if candidate else None,
                    "drive_name": drive.name if drive else None,
                    "employer_name": employer.name if employer else None,
                    "applied_at": to_date_only(app.applied_at),
                }
            )

        return make_response(jsonify(result), 200)
