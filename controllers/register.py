from flask import (
    Blueprint,
    current_app as app,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy import exc

from extensions import db
from models import Candidate, Employer

register_bp = Blueprint("register_bp", __name__, url_prefix="/register")


def default_form(role="candidate", username="", display_name="", resume_path=""):
    return {
        "role": role,
        "username": username,
        "display_name": display_name,
        "resume_path": resume_path,
    }


@register_bp.route("/", methods=["GET", "POST"])
@register_bp.route("", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("auth/register.html", form=default_form())

    role = request.form.get("role", "candidate").strip().lower()
    email = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "")
    display_name = request.form.get("display_name", "").strip()
    resume_path = request.form.get("resume_path", "").strip()
    form = default_form(role, email, display_name, resume_path)

    if role not in {"candidate", "employer"}:
        return render_template(
            "auth/register.html", form=form, error="Select a valid role."
        )

    if not email or not password or not display_name:
        return render_template(
            "auth/register.html", form=form, error="All fields are required."
        )

    new_user, error_message = create_new_user(db, email, password, role)
    if error_message:
        return render_template("auth/register.html", form=form, error=error_message)

    if role == "candidate":
        db.session.add(
            Candidate(
                full_name=display_name,
                user_id=new_user.id,
                resume_path=resume_path or None,
            )
        )
        success_message = "Candidate account created successfully."
    else:
        db.session.add(
            Employer(
                name=display_name,
                user_id=new_user.id,
                approval_status="pending",
            )
        )
        success_message = "Employer registration submitted. Await admin approval."

    error_message = try_commit(db)
    if error_message:
        return render_template("auth/register.html", form=form, error=error_message), 500

    return render_template("auth/login.html", message=success_message)

def try_commit(db):
    try:
        db.session.commit()
    except exc.DatabaseError:
        db.session.rollback()
        return "Could not register. Please try again."
    return None


def create_new_user(db, email, password, role_name):
    user_datastore = app.extensions["security"].datastore
    if user_datastore.find_user(email=email):
        return (None, f"Email {email} already exists.")

    user_role = user_datastore.find_role(role_name)

    new_user = user_datastore.create_user(
        email=email,
        password=password,
        roles=[user_role],
        active=(role_name != "employer"),
    )

    db.session.flush()

    return (new_user, None)
