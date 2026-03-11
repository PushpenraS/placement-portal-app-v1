from flask import Blueprint, redirect, render_template, request, url_for
from flask_security import current_user, roles_required
from sqlalchemy import exc

from extensions import db
from models import Application, Employer, PlacementDrive

candidate_bp = Blueprint("candidate_bp", __name__, url_prefix="/candidate")

APP_STATUS = {0: "cancelled", 1: "applied", 2: "shortlisted", 3: "selected", 4: "rejected"}


def _date_only(value):
    if not value:
        return "-"
    return value.date()


@candidate_bp.route("/dashboard")
@roles_required("candidate")
def dashboard():
    candidate = current_user.candidate_profile
    employers = Employer.query.filter_by(approval_status="approved").order_by(Employer.id.desc()).all()
    employers = [item for item in employers if item.user and item.user.active]

    return render_template(
        "candidate/dashboard.html",
        candidate=candidate,
        employers=employers,
        applications=candidate.applications if candidate else [],
        app_status=APP_STATUS,
        date_only=_date_only,
    )


@candidate_bp.route("/profile", methods=["GET", "POST"])
@roles_required("candidate")
def profile():
    candidate = current_user.candidate_profile
    if request.method == "GET":
        return render_template("candidate/profile.html", candidate=candidate)

    candidate.qualification = request.form.get("qualification", "").strip() or None
    candidate.skills = request.form.get("skills", "").strip() or None
    candidate.resume_path = request.form.get("resume_path", "").strip() or None

    try:
        db.session.commit()
    except exc.DatabaseError:
        db.session.rollback()

    return redirect(url_for("candidate_bp.dashboard"))


@candidate_bp.route("/history")
@roles_required("candidate")
def history():
    candidate = current_user.candidate_profile
    return render_template(
        "candidate/history.html",
        candidate=candidate,
        applications=candidate.applications if candidate else [],
        app_status=APP_STATUS,
        date_only=_date_only,
    )


@candidate_bp.route("/employer/<int:employer_id>")
@roles_required("candidate")
def employer_profile(employer_id):
    employer = Employer.query.filter_by(id=employer_id, approval_status="approved").first()
    if not employer:
        return redirect(url_for("candidate_bp.dashboard"))

    drives = (
        PlacementDrive.query.filter_by(employer_id=employer_id, status=1)
        .order_by(PlacementDrive.id.desc())
        .all()
    )

    existing_applications = {
        application.placement_drive_id for application in current_user.candidate_profile.applications
    }

    return render_template(
        "candidate/employer_profile.html",
        employer=employer,
        drives=drives,
        existing_applications=existing_applications,
        date_only=_date_only,
    )


@candidate_bp.route("/drive/<int:drive_id>", methods=["GET", "POST"])
@roles_required("candidate")
def placement_drive(drive_id):
    drive = PlacementDrive.query.filter_by(id=drive_id).first()
    if not drive:
        return redirect(url_for("candidate_bp.dashboard"))
    candidate = current_user.candidate_profile

    source = request.values.get("source", "dashboard").strip().lower()
    if source == "employer" and drive.employer_id:
        back_target = url_for("candidate_bp.employer_profile", employer_id=drive.employer_id)
    else:
        back_target = url_for("candidate_bp.dashboard")

    if request.method == "POST":
        existing = Application.query.filter_by(
            candidate_id=candidate.id, placement_drive_id=drive_id
        ).first()
        if not existing and drive.status == 1 and candidate.resume_path:
            db.session.add(
                Application(
                    candidate_id=candidate.id,
                    placement_drive_id=drive_id,
                    status=1,
                )
            )
            try:
                db.session.commit()
            except exc.DatabaseError:
                db.session.rollback()
        return redirect(back_target)

    existing = Application.query.filter_by(
        candidate_id=candidate.id, placement_drive_id=drive_id
    ).first()

    return render_template(
        "candidate/placement_drive.html",
        candidate=candidate,
        drive=drive,
        existing_application=existing,
        app_status=APP_STATUS,
        back_target=back_target,
        source=source,
        date_only=_date_only,
    )
