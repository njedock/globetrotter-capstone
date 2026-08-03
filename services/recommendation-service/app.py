"""
Recommendation Service — with Redis caching and resilience features.
"""
import os
import json
import time
import uuid

import jwt
import requests
import redis
from flask import Flask, request as flask_request, jsonify

from models import get_all_destinations

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")

USER_SERVICE_URL = os.environ.get("USER_SERVICE_URL", "http://localhost:5001")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Connect to Redis (graceful fallback if unavailable)
try:
    cache = redis.from_url(REDIS_URL, decode_responses=True)
    cache.ping()
    print("[CACHE] Redis connected")
except Exception:
    cache = None
    print("[CACHE] Redis unavailable — running without cache")

# ---- Circuit Breaker ----
circuit = {
    "failures": 0,
    "state": "closed",      # closed = normal, open = blocking calls
    "last_failure": 0,
    "threshold": 3,          # open after 3 consecutive failures
    "timeout": 30,           # try again after 30 seconds
}


def circuit_allows():
    """Check if the circuit breaker allows a call to User Service."""
    if circuit["state"] == "closed":
        return True
    if circuit["state"] == "open":
        if time.time() - circuit["last_failure"] > circuit["timeout"]:
            circuit["state"] = "half-open"
            return True
        return False
    return True  # half-open: allow one test call


def circuit_success():
    """Record a successful call — reset the breaker."""
    circuit["failures"] = 0
    circuit["state"] = "closed"


def circuit_failure():
    """Record a failed call — open the breaker if threshold reached."""
    circuit["failures"] += 1
    circuit["last_failure"] = time.time()
    if circuit["failures"] >= circuit["threshold"]:
        circuit["state"] = "open"
        print(f"[CIRCUIT BREAKER] OPEN — User Service unreachable after {circuit['threshold']} failures")


# ---- Retry with Exponential Backoff ----
def call_with_retry(url, max_retries=3):
    """Call a URL with retries and exponential backoff."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return response
            return response
        except requests.exceptions.RequestException:
            wait = 2 ** attempt  # 1s, 2s, 4s
            print(f"[RETRY] Attempt {attempt + 1} failed, waiting {wait}s...")
            time.sleep(wait)
    return None


def get_current_user():
    auth_header = flask_request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


@app.route("/destinations", methods=["GET"])
def search_destinations():
    """Search destinations — cached for 60 seconds."""
    # Build a cache key from the query parameters
    cache_key = f"destinations:{flask_request.query_string.decode()}"

    # Try cache first
    if cache:
        try:
            cached = cache.get(cache_key)
            if cached:
                print(f"[CACHE] HIT for {cache_key}")
                return jsonify(json.loads(cached)), 200
        except Exception:
            pass  # Redis down — fall through to normal path

    print(f"[CACHE] MISS for {cache_key}")

    q = flask_request.args.get("q", "").strip().lower()
    tag = flask_request.args.get("tag", "").strip().lower()
    continent = flask_request.args.get("continent", "").strip().lower()
    max_cost_str = flask_request.args.get("max_cost", "").strip()

    max_cost = None
    if max_cost_str:
        try:
            max_cost = int(max_cost_str)
        except ValueError:
            return jsonify({"error": "max_cost must be an integer"}), 400

    destinations = get_all_destinations()
    results = []

    for dest in destinations:
        if q:
            searchable = " ".join([
                dest.get("name", ""),
                dest.get("country", ""),
                dest.get("description", ""),
            ]).lower()
            if q not in searchable:
                continue
        if tag and tag not in [t.lower() for t in dest.get("tags", [])]:
            continue
        if continent and continent != dest.get("continent", "").lower():
            continue
        if max_cost is not None:
            cost = dest.get("avg_cost_per_day")
            if cost is None or cost > max_cost:
                continue
        results.append(dest)

    # Store in cache for 60 seconds
    if cache:
        try:
            cache.setex(cache_key, 60, json.dumps(results))
        except Exception:
            pass

    return jsonify(results), 200


@app.route("/recommendations", methods=["GET"])
def get_recommendations():
    """Get recommendations — with circuit breaker and retry on User Service call."""
    username = get_current_user()
    if not username:
        return jsonify({"error": "authentication required"}), 401

    # ---- Check circuit breaker ----
    if not circuit_allows():
        return jsonify({
            "error": "user service temporarily unavailable",
            "circuit_state": "open"
        }), 503

    # ---- Call User Service with retry + backoff ----
    response = call_with_retry(f"{USER_SERVICE_URL}/users/{username}")

    if response is None:
        circuit_failure()
        return jsonify({"error": "user service unavailable after retries"}), 503

    if response.status_code != 200:
        circuit_failure()
        return jsonify({"error": "could not fetch user preferences"}), 502

    circuit_success()
    user_data = response.json()
    preferences = [p.lower() for p in user_data.get("preferences", [])]

    # ---- Check cache for recommendations ----
    cache_key = f"recommendations:{username}"
    if cache:
        try:
            cached = cache.get(cache_key)
            if cached:
                print(f"[CACHE] HIT for {cache_key}")
                return jsonify(json.loads(cached)), 200
        except Exception:
            pass

    try:
        limit = int(flask_request.args.get("limit", 5))
    except ValueError:
        return jsonify({"error": "limit must be an integer"}), 400

    destinations = get_all_destinations()

    scored = []
    for dest in destinations:
        dest_tags = [t.lower() for t in dest.get("tags", [])]
        score = sum(1 for pref in preferences if pref in dest_tags)
        scored.append((score, dest))

    scored.sort(key=lambda x: (-x[0], x[1].get("name", "")))

    results = []
    for score, dest in scored[:limit]:
        entry = dict(dest)
        entry["match_score"] = score
        results.append(entry)

    # Cache for 120 seconds
    if cache:
        try:
            cache.setex(cache_key, 120, json.dumps(results))
        except Exception:
            pass

    return jsonify(results), 200


# ---- Distributed Tracing ----
@app.before_request
def add_trace_id():
    """Attach a trace ID to every request for cross-service tracking."""
    trace_id = flask_request.headers.get("X-Trace-ID", str(uuid.uuid4()))
    flask_request.trace_id = trace_id


@app.after_request
def return_trace_id(response):
    """Include the trace ID in the response headers."""
    trace_id = getattr(flask_request, "trace_id", "unknown")
    response.headers["X-Trace-ID"] = trace_id
    print(f"[TRACE] {flask_request.method} {flask_request.path} → {response.status_code} | trace={trace_id}")
    return response


@app.route("/health", methods=["GET"])
def health():
    redis_status = "connected"
    if cache:
        try:
            cache.ping()
        except Exception:
            redis_status = "disconnected"
    else:
        redis_status = "not configured"

    return jsonify({
        "status": "healthy",
        "service": "recommendation-service",
        "redis": redis_status,
        "circuit_breaker": circuit["state"],
    }), 200
    
# Also fetch user's past itineraries for "past trips" scoring
    past_destinations = []
    try:
        itin_response = requests.get(
            f"{os.environ.get('ITINERARY_SERVICE_URL', 'http://localhost:5002')}/itineraries",
            headers={"Authorization": flask_request.headers.get("Authorization", "")},
            timeout=5
        )
        if itin_response.status_code == 200:
            for itin in itin_response.json():
                past_destinations.extend(itin.get("destinations", []))
    except Exception:
        pass  # Graceful fallback — recommendations still work without past trips

    try:
        limit = int(flask_request.args.get("limit", 5))
    except ValueError:
        return jsonify({"error": "limit must be an integer"}), 400

    destinations = get_all_destinations()

    scored = []
    for dest in destinations:
        dest_tags = [t.lower() for t in dest.get("tags", [])]
        score = 0

        # Preference match (original)
        score += sum(1 for pref in preferences if pref in dest_tags)

        # Past trip bonus — recommend similar to where they've been
        if dest.get("name") in past_destinations:
            score += 1

        # Popularity bonus — cheaper destinations are more "popular"
        cost = dest.get("avg_cost_per_day", 100)
        if cost < 80:
            score += 1

        scored.append((score, dest))

    scored.sort(key=lambda x: (-x[0], x[1].get("name", "")))

    results = []
    for score, dest in scored[:limit]:
        entry = dict(dest)
        entry["match_score"] = score
        results.append(entry)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5003))
    app.run(host="0.0.0.0", port=port)