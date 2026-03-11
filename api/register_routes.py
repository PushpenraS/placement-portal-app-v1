from flask_restful import Resource, request
from flask import jsonify, make_response
from user_datastore import user_datastore
from models import Candidate, Employer
from extensions import db


class RegisterCandidate(Resource):
    def post(self):
        new_user_cred = request.get_json()

        if not new_user_cred:
            return make_response(
                jsonify(
                    {
                        "Email, Password, Full Name is required for Candidate registration."
                    }
                ),
                400,
            )

        email = new_user_cred.get("email", "").strip().lower()
        password = new_user_cred.get("password")
        full_name = new_user_cred.get("full_name", "")
        if not email or not password or not full_name:
            return make_response(
                jsonify(
                    {
                        "message": "Email, Password, Full Name is required for Candidate registration."
                    }
                ),
                400,
            )

        if len(password) < 2:
            return make_response(
                jsonify(
                    {"message": "Password length has to be greater than 2 characters."}
                ),
                400,
            )

        existing_user = user_datastore.find_user(email=email)

        if existing_user:
            return make_response(jsonify({"message": "User already exists."}), 400)

        role = user_datastore.find_role("candidate")
        new_user = user_datastore.create_user(
            email=email, password=password, roles=[role]
        )

        db.session.flush()

        new_candidate = Candidate(full_name=full_name, user_id=new_user.id)

        db.session.add(new_candidate)

        try:
            db.session.commit()
        except Exception as ex:
            return make_response(jsonify({"message": str(ex)}), 400)

        return make_response(
            jsonify({"message": "Candidate has been created successfully"}), 201
        )


class RegisterEmployer(Resource):
    def post(self):
        new_user_cred = request.get_json()

        if not new_user_cred:
            return make_response(
                jsonify(
                    {
                        "Email, Password, Organization Name is required for Employer registration."
                    }
                ),
                400,
            )

        email = new_user_cred.get("email", "").strip().lower()
        password = new_user_cred.get("password")
        employer_name = new_user_cred.get("name", "")
        if not email or not password or not employer_name:
            return make_response(
                jsonify(
                    {
                        "message": "Email, Password, Organization Name is required for Employer registration."
                    }
                ),
                400,
            )

        if len(password) < 2:
            return make_response(
                jsonify(
                    {"message": "Password length has to be greater than 2 characters."}
                ),
                400,
            )

        existing_user = user_datastore.find_user(email=email)

        if existing_user:
            return make_response(jsonify({"message": "User already exists."}), 400)

        role = user_datastore.find_role("employer")
        new_user = user_datastore.create_user(
            email=email, password=password, roles=[role], active=False
        )

        db.session.flush()

        new_employer = Employer(name=employer_name, user_id=new_user.id)

        db.session.add(new_employer)

        try:
            db.session.commit()
        except Exception as ex:
            return make_response(jsonify({"message": str(ex)}), 400)

        return make_response(
            jsonify({"message": "Employer has been created successfully"}), 201
        )
