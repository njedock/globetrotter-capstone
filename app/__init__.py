"""
app/__init__.py

Flask application factory.
"""
import os
from flask import Flask, jsonify as flask_jsonify
from typing import Any, Dict, Optional


class jsonify:
    """Wrapper that provides JSON response construction helpers."""

    def __call__(self, *args: Any, **kwargs: Any):
        return flask_jsonify(*args, **kwargs)

    def response(
        self,
        payload: Any,
        status: int = 200,
        headers: Optional[Dict[str, str]] = None,
    ):
        response = flask_jsonify(payload)
        response.status_code = status
        if headers:
            response.headers.update(headers)
        return response

    def error(self, error: str, message: str, status: int):
        return self.response({"error": error, "message": message}, status=status)


jsonify = jsonify()


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Secret key used for JWT signing.  Set the SECRET_KEY environment variable
    # in production.  The fallback is intentionally weak and must never be used
    # outside of local development.
    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY", "globetrotter-secret-change-in-prod"
    )

    # Register all route blueprints
    from app.auth import auth_bp
    from app.destinations import destinations_bp
    from app.recommendations import recommendations_bp
    from app.itineraries import itineraries_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(destinations_bp)
    app.register_blueprint(recommendations_bp)
    app.register_blueprint(itineraries_bp)

# Centralized error handlers — consistent JSON for every error
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "Bad request", "message": str(e)}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({"error": "Unauthorized", "message": str(e)}), 401

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found", "message": str(e)}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Method not allowed", "message": str(e)}), 405

    @app.errorhandler(409)
    def conflict(e):
        return jsonify({"error": "Conflict", "message": str(e)}), 409

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"error": "Internal server error", "message": "Something went wrong"}), 500
    return app
