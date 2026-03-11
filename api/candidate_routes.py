from datetime import datetime, UTC

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


def _current_candidate_id():
    candidate_profile = getattr(current_user, "candidate_profile", None)
    return candidate_profile.id if candidate_profile else None


class CandidateResource(Resource):
    @auth_token_required
    @roles_required("candidate")
    def get(self):
        current_candidate_id = _current_candidate_id()
        if not current_candidate_id:
            return make_response(jsonify({"message": "Forbidden"}), 403)

        candidate = Candidate.query.filter_by(id=current_candidate_id).first()

        if not candidate:
            return make_response(
                jsonify(
                    {
                        "message": f"Candidate with id {current_candidate_id} does not exist"
                    }
                ),
                404,
            )
        result = {
            "candidate_id": candidate.id,
            "full_name": candidate.full_name,
            "email": candidate.user.email if candidate.user else None,
            "active": candidate.user.active if candidate.user else None,
            "qualification": candidate.qualification,
            "skills": candidate.skills,
            "resume_path": candidate.resume_path,
        }

        return make_response(jsonify(result), 200)

    @auth_token_required
    @roles_required("candidate")
    def put(self):
        current_candidate_id = _current_candidate_id()
        if not current_candidate_id:
            return make_response(jsonify({"message": "Forbidden"}), 403)

        candidate = Candidate.query.filter_by(id=current_candidate_id).first()

        if not candidate:
            return make_response(
                jsonify(
                    {
                        "message": f"Candidate with id {current_candidate_id} does not exist"
                    }
                ),
                404,
            )

        payload = request.get_json()

        if not payload:
            return make_response(jsonify({"message": "Invalid Operation"}), 400)

        candidate.qualification = payload.get("qualification")
        candidate.skills = payload.get("skills")
        candidate.resume_path = payload.get("resume_path")

        try:
            db.session.commit()
        except Exception as ex:
            return make_response(jsonify({"message": str(ex)}), 400)

        return make_response(jsonify({"message": "Profile updated successfully"}), 200)


class CandidateEmployerListResource(Resource):
    # GET: list approved employers for student dashboard.
    @auth_token_required
    @roles_required("candidate")
    def get(self):
        employers = (
            Employer.query.filter_by(approval_status="approved")
            .order_by(Employer.id.desc())
            .all()
        )

        result = []
        for employer in employers:
            if employer.user and not employer.user.active:
                continue
            result.append(
                {
                    "employer_id": employer.id,
                    "name": employer.name,
                    "industry": employer.industry,
                    "location": employer.location,
                }
            )
        return make_response(jsonify(result), 200)


class CandidateEmployerItemResource(Resource):
    # GET: employer overview + current drives.
    @auth_token_required
    @roles_required("candidate")
    def get(self, employer_id):
        employer = Employer.query.filter_by(id=employer_id).first()
        if not employer:
            return make_response(
                jsonify({"message": f"Employer with id {employer_id} does not exist"}),
                404,
            )

        current_drives = (
            PlacementDrive.query.filter_by(
                employer_id=employer_id, status=DRIVE_STATUS_MAP["ongoing"]
            )
            .order_by(PlacementDrive.id.desc())
            .all()
        )

        drives = []
        for drive in current_drives:
            drives.append(
                {
                    "drive_id": drive.id,
                    "name": drive.name,
                    "job_title": drive.job_title,
                    "application_deadline": to_date_only(drive.application_deadline),
                }
            )

        return make_response(
            jsonify(
                {
                    "employer_id": employer.id,
                    "name": employer.name,
                    "about": employer.about,
                    "industry": employer.industry,
                    "location": employer.location,
                    "website": employer.website,
                    "current_drives": drives,
                }
            ),
            200,
        )


class CandidateDriveItemResource(Resource):
    # GET: drive details for "view details"
    @auth_token_required
    @roles_required("candidate")
    def get(self, drive_id):
        drive = PlacementDrive.query.filter_by(id=drive_id).first()
        if not drive:
            return make_response(
                jsonify({"message": f"Drive with id {drive_id} does not exist"}), 404
            )

        employer = drive.employer
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
                    "employer": {
                        "employer_id": employer.id if employer else None,
                        "name": employer.name if employer else None,
                    },
                }
            ),
            200,
        )


class CandidateDriveApplicationResource(Resource):
    @auth_token_required
    @roles_required("candidate")
    def get(self, drive_id):
        current_candidate_id = _current_candidate_id()
        if not current_candidate_id:
            return make_response(jsonify({"message": "Forbidden"}), 403)

        candidate: Candidate = Candidate.query.filter_by(
            id=current_candidate_id
        ).first()

        if not candidate:
            return make_response(
                jsonify(
                    {
                        "message": f"Candidate with {current_candidate_id} does not exist."
                    }
                ),
                400,
            )

        drive: PlacementDrive = PlacementDrive.query.filter_by(id=drive_id).first()

        if not drive:
            return make_response(
                jsonify({"message": f"Candidate with {drive_id} does not exist."}), 400
            )

        application: Application = Application.query.filter(
            Application.candidate_id == current_candidate_id,
            Application.placement_drive_id == drive_id,
        ).first()

        if not application:
            return make_response(jsonify({"exists": False}), 200)

        return make_response(jsonify({"exists": True}), 200)

    # POST: apply to a drive
    # POST body: {"candidate_id": <id>}
    @auth_token_required
    @roles_required("candidate")
    def post(self, drive_id):
        payload = request.get_json() or {}
        current_candidate_id = _current_candidate_id()
        candidate_id = payload.get("candidate_id")
        if not current_candidate_id:
            return make_response(jsonify({"message": "Forbidden"}), 403)
        if candidate_id and int(candidate_id) != current_candidate_id:
            return make_response(jsonify({"message": "Forbidden"}), 403)
        candidate_id = current_candidate_id

        if not candidate_id:
            return make_response(
                jsonify({"message": "Valid candidate_id required"}), 400
            )

        candidate = Candidate.query.filter_by(id=candidate_id).first()
        if not candidate:
            return make_response(
                jsonify(
                    {"message": f"Candidate with id {candidate_id} does not exist"}
                ),
                404,
            )
        if candidate.user and not candidate.user.active:
            return make_response(
                jsonify({"message": "Candidate account is inactive"}), 403
            )

        drive = PlacementDrive.query.filter_by(id=drive_id).first()
        if not drive:
            return make_response(
                jsonify({"message": f"Drive with id {drive_id} does not exist"}), 404
            )

        if drive.status != DRIVE_STATUS_MAP["ongoing"]:
            return make_response(
                jsonify({"message": "Only ongoing drives accept applications"}), 400
            )
        if (
            drive.application_deadline
            and drive.application_deadline < datetime.utcnow()
        ):
            return make_response(
                jsonify({"message": "Application deadline has passed"}), 400
            )

        existing = Application.query.filter_by(
            candidate_id=candidate_id, placement_drive_id=drive_id
        ).first()
        if existing:
            return make_response(
                jsonify({"message": "Application already exists for this drive"}), 409
            )

        application = Application(
            candidate_id=candidate_id,
            placement_drive_id=drive_id,
            status=APP_STATUS_MAP["applied"],
        )
        db.session.add(application)

        try:
            db.session.commit()
        except Exception as ex:
            return make_response(jsonify({"message": str(ex)}), 400)

        return make_response(
            jsonify(
                {
                    "message": "Applied successfully",
                    "details": {
                        "application_id": application.id,
                        "candidate_id": candidate_id,
                        "drive_id": drive_id,
                        "status": REV_APP_STATUS_MAP[application.status],
                    },
                }
            ),
            201,
        )


class CandidateAppliedDriveListResource(Resource):
    # GET: list applied drives shown on student dashboard.
    @auth_token_required
    @roles_required("candidate")
    def get(self):
        current_candidate_id = _current_candidate_id()
        if not current_candidate_id:
            return make_response(jsonify({"message": "Forbidden"}), 403)

        candidate = Candidate.query.filter_by(id=current_candidate_id).first()
        if not candidate:
            return make_response(
                jsonify(
                    {
                        "message": f"Candidate with id {current_candidate_id} does not exist"
                    }
                ),
                404,
            )

        applications = (
            Application.query.filter_by(candidate_id=current_candidate_id)
            .order_by(Application.id.desc())
            .all()
        )

        result = []
        for app in applications:
            drive = app.placement_drive
            employer = drive.employer if drive else None
            result.append(
                {
                    "application_id": app.id,
                    "drive_id": drive.id if drive else None,
                    "drive_name": drive.name if drive else None,
                    "employer_name": employer.name if employer else None,
                    "applied_at": to_date_only(app.applied_at),
                    "status": REV_APP_STATUS_MAP.get(app.status, "unknown"),
                }
            )

        return make_response(jsonify(result), 200)


class CandidateApplicationHistoryResource(Resource):
    # GET: application history table for student.
    @auth_token_required
    @roles_required("candidate")
    def get(self):
        current_candidate_id = _current_candidate_id()
        if not current_candidate_id:
            return make_response(jsonify({"message": "Forbidden"}), 403)

        candidate = Candidate.query.filter_by(id=current_candidate_id).first()
        if not candidate:
            return make_response(
                jsonify(
                    {
                        "message": f"Candidate with id {current_candidate_id} does not exist"
                    }
                ),
                404,
            )

        applications = (
            Application.query.filter_by(candidate_id=current_candidate_id)
            .order_by(Application.id.asc())
            .all()
        )

        history = []
        for index, app in enumerate(applications, start=1):
            drive = app.placement_drive
            history.append(
                {
                    "sr_no": index,
                    "drive_no": drive.id if drive else None,
                    "interview": None,
                    "job_title": drive.job_title if drive else None,
                    "result": REV_APP_STATUS_MAP.get(
                        app.status, "unknown"
                    ).capitalize(),
                    "remark": None,
                }
            )

        return make_response(
            jsonify(
                {
                    "candidate_id": candidate.id,
                    "candidate_name": candidate.full_name,
                    "department": candidate.qualification,
                    "history": history,
                }
            ),
            200,
        )
