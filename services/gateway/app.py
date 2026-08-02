"""
API Gateway — single entry point for all client requests.
Routes each request to the appropriate microservice.
"""
import os
import requests
from flask import Flask, request as flask_request, jsonify, Response

app = Flask(__name__)

USER_SERVICE = os.environ.get("USER_SERVICE_URL", "http://localhost:5001")
ITINERARY_SERVICE = os.environ.get("ITINERARY_SERVICE_URL", "http://localhost:5002")
RECOMMENDATION_SERVICE = os.environ.get("RECOMMENDATION_SERVICE_URL", "http://localhost:5003")


def forward(service_url, path):
    url = f"{service_url}/{path}"
    headers = {
        key: value for key, value in flask_request.headers
        if key.lower() != "host"
    }
    try:
        response = requests.request(
            method=flask_request.method,
            url=url,
            headers=headers,
            params=flask_request.args,
            json=flask_request.get_json(silent=True),
            timeout=10,
        )
        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get("Content-Type", "application/json"),
        )
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "service unavailable", "details": str(e)}), 503


@app.route("/register", methods=["POST"])
def register():
    return forward(USER_SERVICE, "register")

@app.route("/login", methods=["POST"])
def login():
    return forward(USER_SERVICE, "login")

@app.route("/users/<username>", methods=["GET"])
def get_user(username):
    return forward(USER_SERVICE, f"users/{username}")

@app.route("/itineraries", methods=["GET", "POST"])
def itineraries():
    return forward(ITINERARY_SERVICE, "itineraries")

@app.route("/destinations", methods=["GET"])
def destinations():
    return forward(RECOMMENDATION_SERVICE, "destinations")

@app.route("/recommendations", methods=["GET"])
def recommendations():
    return forward(RECOMMENDATION_SERVICE, "recommendations")

@app.route("/health", methods=["GET"])
def health():
    statuses = {"gateway": "healthy"}
    for name, url in [("user-service", USER_SERVICE),
                      ("itinerary-service", ITINERARY_SERVICE),
                      ("recommendation-service", RECOMMENDATION_SERVICE)]:
        try:
            r = requests.get(f"{url}/health", timeout=3)
            statuses[name] = "healthy" if r.status_code == 200 else "unhealthy"
        except requests.exceptions.RequestException:
            statuses[name] = "unreachable"
    return jsonify(statuses), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)