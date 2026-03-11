from datetime import timedelta

from flask import Blueprint, jsonify, request, make_response
from user_datastore import user_datastore
from flask_security import utils, auth_token_required
from flask_restful import Resource

from extensions import db
from user_datastore import user_datastore
from models import User


class EmailAvailability(Resource):
    def post(self):
        payload = request.get_json()

        result = {"message": ""}

        if not payload:
            result["message"] = "Email is required."
            return make_response(jsonify(result), 400)

        email = payload.get("email", "").strip().lower()

        if not email:
            result["message"] = "Email is required."
            return make_response(jsonify(result), 400)

        user = user_datastore.find_user(email=email)

        if not user:
            return make_response(jsonify({"available": True}), 200)

        return make_response(jsonify({"available": False}), 200)


class LoginUser(Resource):
    def post(self):
        login_cred = request.get_json()
        if not login_cred:
            return make_response(
                jsonify({"message": "Email and password are required"}), 400
            )

        email = login_cred.get("email", "").strip().lower()
        password = login_cred.get("password", "")

        if not email or not password:
            return make_response(
                jsonify({"message": "Email and password are required"}), 400
            )

        user = user_datastore.find_user(email=email)

        if not user:
            return make_response(jsonify({"message": "User not found."}), 404)

        if not utils.verify_password(password, user.password):
            return make_response(jsonify({"message": "Invalid Password."}), 401)

        if not user.active:
            return make_response(
                jsonify(
                    {"message": "Your privileges has been revoked. Contact admin."}
                ),
                403,
            )

        token = user.get_auth_token()

        utils.login_user(user)

        role_name = user.roles[0].name if user.roles else None

        result = {
            "message": "Login Successful",
            "auth_token": token,
            "user": {"email": user.email, "role": role_name},
        }

        return make_response(jsonify(result), 200)


class LogoutUser(Resource):
    @auth_token_required
    def post(self):
        utils.logout_user()

        return make_response(jsonify({"message": "User logged out successfully"}, 200))
