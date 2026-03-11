from .auth import auth_bp
from .register import register_bp
from .admin import admin_bp
from .employer import employer_bp
from .candidate import candidate_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(register_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(employer_bp)
    app.register_blueprint(candidate_bp)
