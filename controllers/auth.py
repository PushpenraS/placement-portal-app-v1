from flask import Blueprint, current_app as app, redirect, render_template, request, url_for
from flask_login import login_user, logout_user
from flask_security import utils

auth_bp = Blueprint("auth_bp", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
@auth_bp.route("/", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("auth/login.html")

    datastore = app.extensions["security"].datastore

    email = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        return render_template(
            "auth/login.html", error="Email and password are required."
        )

    user = datastore.find_user(email=email)

    if not user:
        return render_template("auth/login.html", error="User does not exist.")

    if not utils.verify_password(password, user.password):
        return render_template("auth/login.html", error="Invalid email or password.")

    if not user.active:
        return render_template(
            "auth/login.html",
            error="Your account is inactive or still waiting for approval.",
        )

    login_user(user)

    role_name = user.roles[0].name if user.roles else ""
    if role_name == "admin":
        return redirect(url_for("admin_bp.dashboard"))
    if role_name == "employer":
        return redirect(url_for("employer_bp.dashboard"))
    return redirect(url_for("candidate_bp.dashboard"))


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    logout_user()
    return redirect(url_for("auth_bp.login"))
