"""
app/__init__.py

Flask application factory.
"""
import os
from flask import Flask, jsonify
from flasgger import Swagger


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Secret key for JWT signing
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

    # Swagger API documentation
    app.config["SWAGGER"] = {
        "title": "GlobeTrotter API",
        "description": "Phase 1 Monolith - Travel Assistant REST API",
        "version": "1.0.0",
        "uiversion": 3
    }
    Swagger(app)

    # Centralized error handlers
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