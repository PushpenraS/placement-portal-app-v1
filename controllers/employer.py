import datetime

from flask import Blueprint, redirect, render_template, request, url_for
from flask_security import current_user, roles_required
from sqlalchemy import exc

from extensions import db, to_date_only
from models import Application, PlacementDrive

employer_bp = Blueprint("employer_bp", __name__, url_prefix="/employer")

APP_STATUS = {0: "cancelled", 1: "applied", 2: "shortlisted", 3: "selected", 4: "rejected"}

def _is_profile_complete(employer):
    if not employer:
        return False

    required_fields = [
        employer.name,
        employer.industry,
        employer.location,
        employer.website,
        employer.about,
    ]
    return all(value and str(value).strip() for value in required_fields)


@employer_bp.route("/dashboard")
@roles_required("employer")
def dashboard():
    employer = current_user.employer_profile
    profile_complete = _is_profile_complete(employer)
    drives = employer.placement_drives if employer else []
    pending_drives = [drive for drive in drives if drive.status == 3]
    ongoing_drives = [drive for drive in drives if drive.status == 1]
    closed_drives = [drive for drive in drives if drive.status in {0, 2, 4}]

    return render_template(
        "employer/dashboard.html",
        employer=employer,
        profile_complete=profile_complete,
        pending_drives=pending_drives,
        ongoing_drives=ongoing_drives,
        closed_drives=closed_drives,
        drive_status={0: "cancelled", 1: "ongoing", 2: "closed", 3: "pending", 4: "rejected"},
        date_only=to_date_only,
    )


@employer_bp.route("/profile", methods=["GET", "POST"])
@roles_required("employer")
def profile():
    employer = current_user.employer_profile
    if request.method == "GET":
        return render_template("employer/profile.html", employer=employer)

    employer.industry = request.form.get("industry", "").strip() or None
    employer.location = request.form.get("location", "").strip() or None
    employer.website = request.form.get("website", "").strip() or None
    employer.about = request.form.get("about", "").strip() or None

    try:
        db.session.commit()
    except exc.DatabaseError:
        db.session.rollback()

    return redirect(url_for("employer_bp.dashboard"))


@employer_bp.route("/drive/create", methods=["GET", "POST"])
@roles_required("employer")
def create_drive():
    employer = current_user.employer_profile
    if not _is_profile_complete(employer):
        return redirect(url_for("employer_bp.dashboard"))

    if request.method == "GET":
        return render_template("employer/create.html")

    new_drive = PlacementDrive(
        name=request.form.get("name", "").strip(),
        job_title=request.form.get("job_title", "").strip(),
        job_description=request.form.get("job_description", "").strip(),
        salary=int(request.form.get("salary", "0") or 0),
        location=request.form.get("location", "").strip(),
        eligibility_criteria=request.form.get("eligibility_criteria", "").strip(),
        application_deadline=datetime.datetime.fromisoformat(
            request.form.get("application_deadline", "")
        ),
        employer_id=employer.id,
        status=3,
    )

    db.session.add(new_drive)
    try:
        db.session.commit()
    except (ValueError, exc.DatabaseError):
        db.session.rollback()
        return render_template(
            "employer/create.html",
            error="Could not create drive. Fill all fields with valid values.",
        )

    return redirect(url_for("employer_bp.dashboard"))


@employer_bp.route("/drive/<int:drive_id>/applications")
@roles_required("employer")
def get_applicants(drive_id):
    drive = PlacementDrive.query.filter_by(id=drive_id).first()
    if not drive or drive.employer_id != current_user.employer_profile.id:
        return redirect(url_for("employer_bp.dashboard"))

    return render_template(
        "employer/applicants.html",
        drive=drive,
        app_status=APP_STATUS,
        date_only=to_date_only,
    )


@employer_bp.route("/application/<int:application_id>", methods=["GET", "POST"])
@roles_required("employer")
def review_application(application_id):
    application = Application.query.filter_by(id=application_id).first()
    if (
        not application
        or not application.placement_drive
        or application.placement_drive.employer_id != current_user.employer_profile.id
    ):
        return redirect(url_for("employer_bp.dashboard"))

    if request.method == "GET":
        return render_template(
            "employer/review_application.html",
            application=application,
            app_status=APP_STATUS,
        )

    next_status = int(request.form.get("app_status", application.status))
    application.status = next_status

    try:
        db.session.commit()
    except exc.DatabaseError:
        db.session.rollback()

    return redirect(
        url_for("employer_bp.get_applicants", drive_id=application.placement_drive_id)
    )


@employer_bp.route("/drive/<int:drive_id>/complete", methods=["POST"])
@roles_required("employer")
def close_drive(drive_id):
    drive = PlacementDrive.query.filter_by(id=drive_id).first()
    if not drive or drive.employer_id != current_user.employer_profile.id:
        return redirect(url_for("employer_bp.dashboard"))

    drive.status = 2
    for application in drive.applications:
        if application.status in {1, 2}:
            application.status = 4

    try:
        db.session.commit()
    except exc.DatabaseError:
        db.session.rollback()

    return redirect(url_for("employer_bp.dashboard"))
