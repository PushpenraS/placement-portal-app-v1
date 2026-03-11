from flask import Blueprint, redirect, render_template, request, url_for
from flask_security import current_user, roles_required
from sqlalchemy import exc

from extensions import db, to_date_only
from models import Application, Candidate, Employer, PlacementDrive

admin_bp = Blueprint("admin_bp", __name__, url_prefix="/admin")

DRIVE_STATUS = {0: "cancelled", 1: "ongoing", 2: "closed", 3: "pending", 4: "rejected"}
APP_STATUS = {0: "cancelled", 1: "applied", 2: "shortlisted", 3: "selected", 4: "rejected"}

@admin_bp.route("/dashboard")
@roles_required("admin")
def dashboard():
    search_query = request.args.get("q", "").strip()
    search_scope = request.args.get("scope", "all").strip().lower()
    if search_scope not in {"all", "candidate", "employer"}:
        search_scope = "all"
    employers = Employer.query.order_by(Employer.id.desc()).all()
    candidates = Candidate.query.order_by(Candidate.id.desc()).all()
    drives = PlacementDrive.query.order_by(PlacementDrive.id.desc()).all()
    applications = Application.query.order_by(Application.id.desc()).all()
    all_applications = applications

    if search_query:
        search_value = search_query.lower()
        is_numeric_search = search_query.isdigit()

        if search_scope in {"all", "employer"}:
            employers = [
                item
                for item in employers
                if search_value in (item.name or "").lower()
                or search_value in (item.industry or "").lower()
                or (is_numeric_search and item.id == int(search_query))
            ]
            drives = [
                item
                for item in drives
                if search_value in (item.name or "").lower()
                or search_value in (item.job_title or "").lower()
                or search_value in ((item.employer.name if item.employer else "") or "").lower()
                or search_value in ((item.employer.industry if item.employer else "") or "").lower()
                or (is_numeric_search and item.employer and item.employer.id == int(search_query))
            ]
            applications = [
                item
                for item in applications
                if search_value in (
                    ((item.placement_drive.employer.name if item.placement_drive and item.placement_drive.employer else "") or "").lower()
                )
                or search_value in (
                    ((item.placement_drive.employer.industry if item.placement_drive and item.placement_drive.employer else "") or "").lower()
                )
                or (is_numeric_search and item.placement_drive and item.placement_drive.employer and item.placement_drive.employer.id == int(search_query))
            ]
        else:
            employers = []

        if search_scope in {"all", "candidate"}:
            candidates = [
                item
                for item in candidates
                if search_value in (item.full_name or "").lower()
                or search_value in ((item.user.email if item.user else "") or "").lower()
                or (is_numeric_search and item.id == int(search_query))
            ]
            candidate_applications = [
                item
                for item in all_applications
                if search_value in ((item.candidate.full_name if item.candidate else "") or "").lower()
                or search_value in ((item.candidate.user.email if item.candidate and item.candidate.user else "") or "").lower()
                or (is_numeric_search and item.candidate and item.candidate.id == int(search_query))
            ]
            if search_scope == "candidate":
                drives = []
                applications = candidate_applications
            elif search_scope == "all":
                application_ids = {item.id for item in applications} | {
                    item.id for item in candidate_applications
                }
                applications = [
                    item for item in all_applications if item.id in application_ids
                ]
        else:
            candidates = []

    approved_employers = [item for item in employers if item.approval_status == "approved"]
    pending_employers = [item for item in employers if item.approval_status == "pending"]
    pending_drives = [item for item in drives if item.status == 3]
    ongoing_drives = [item for item in drives if item.status == 1]

    return render_template(
        "admin/dashboard.html",
        approved_employers=approved_employers,
        pending_employers=pending_employers,
        candidates=candidates,
        pending_drives=pending_drives,
        ongoing_drives=ongoing_drives,
        applications=applications,
        drive_status=DRIVE_STATUS,
        app_status=APP_STATUS,
        search_query=search_query,
        search_scope=search_scope,
        date_only=to_date_only,
    )


@admin_bp.route("/employer/<int:employer_id>/action", methods=["POST"])
@roles_required("admin")
def employer_action(employer_id):
    employer = Employer.query.filter_by(id=employer_id).first()
    if not employer:
        return redirect(url_for("admin_bp.dashboard"))

    action = request.form.get("action", "").strip().lower()
    if action == "approve":
        employer.approval_status = "approved"
        if employer.user:
            employer.user.active = True
    elif action == "reject":
        if employer.approval_status == "pending":
            if employer.user:
                db.session.delete(employer.user)
            else:
                db.session.delete(employer)
    elif action == "deactivate":
        if employer.user:
            employer.user.active = False
        for drive in employer.placement_drives:
            if drive.status == 1:
                drive.status = 0
    elif action == "activate":
        if employer.user and employer.approval_status == "approved":
            employer.user.active = True

    try:
        db.session.commit()
    except exc.DatabaseError:
        db.session.rollback()

    return redirect(url_for("admin_bp.dashboard"))


@admin_bp.route("/candidate/<int:candidate_id>/action", methods=["POST"])
@roles_required("admin")
def candidate_action(candidate_id):
    candidate = Candidate.query.filter_by(id=candidate_id).first()
    if not candidate or not candidate.user:
        return redirect(url_for("admin_bp.dashboard"))

    action = request.form.get("action", "").strip().lower()
    if action == "deactivate":
        candidate.user.active = False
        for application in candidate.applications:
            if application.status in {1, 2}:
                application.status = 0
    elif action == "activate":
        candidate.user.active = True

    try:
        db.session.commit()
    except exc.DatabaseError:
        db.session.rollback()

    return redirect(url_for("admin_bp.dashboard"))


@admin_bp.route("/drive/<int:drive_id>/action", methods=["POST"])
@roles_required("admin")
def drive_action(drive_id):
    drive = PlacementDrive.query.filter_by(id=drive_id).first()
    if not drive:
        return redirect(url_for("admin_bp.dashboard"))

    action = request.form.get("action", "").strip().lower()
    if action == "approve" and drive.status == 3:
        drive.status = 1
    elif action == "reject" and drive.status == 3:
        drive.status = 4

    try:
        db.session.commit()
    except exc.DatabaseError:
        db.session.rollback()

    return redirect(url_for("admin_bp.dashboard"))


@admin_bp.route("/drive/<int:drive_id>/complete", methods=["POST"])
@roles_required("admin")
def close_drive(drive_id):
    drive = PlacementDrive.query.filter_by(id=drive_id).first()
    if not drive:
        return redirect(url_for("admin_bp.dashboard"))

    drive.status = 2
    for application in drive.applications:
        if application.status in {1, 2}:
            application.status = 4

    try:
        db.session.commit()
    except exc.DatabaseError:
        db.session.rollback()

    return redirect(url_for("admin_bp.dashboard"))


@admin_bp.route("/drive/<int:drive_id>")
@roles_required("admin")
def view_drive(drive_id):
    drive = PlacementDrive.query.filter_by(id=drive_id).first()
    return render_template(
        "admin/placement_drive.html",
        drive=drive,
        drive_status=DRIVE_STATUS,
        date_only=to_date_only,
    )


@admin_bp.route("/application/<int:application_id>")
@roles_required("admin")
def view_application(application_id):
    application = Application.query.filter_by(id=application_id).first()
    return render_template(
        "admin/view_application.html",
        application=application,
        app_status=APP_STATUS,
        drive_status=DRIVE_STATUS,
        date_only=to_date_only,
    )
