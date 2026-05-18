"""Route definitions for the monitoring web application.

This module contains all Flask routes for:

- Amazon OAuth login
- logout
- receiving secure monitoring data from agents
- dashboard pages
- graph pages
- dashboard JSON API

Security-sensitive agent validation is not implemented directly in this file.
Instead, encrypted agent data is passed to app.agent_security.
"""

from datetime import datetime
from functools import wraps
import logging

import requests
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session

from app import oauth
from app.agent_security import AgentSecurityError, security_verifier
from app.db import metrics_db
from app.utils import validator
from config import MAX_ROWS_PER_AGENT, REFRESH_INTERVAL_MS, AMAZON_REDIRECT_URI

main = Blueprint("main", __name__)


def login_required(view_func):
    """Protect a Flask view so only logged-in users can access it.

    Args:
        view_func:
            Flask view function that should require authentication.

    Returns:
        function:
            Wrapped Flask view function.

    Notes:
        The login itself is handled by Amazon OAuth. This decorator only checks
        whether user information is available in the session.
    """
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("main.amazon_login"))
        return view_func(*args, **kwargs)

    return wrapped_view


@main.route("/login")
def amazon_login():
    """Start the Amazon OAuth login flow.

    Returns:
        Response:
            Redirect response to Amazon OAuth authorization page.
    """
    return oauth.amazon.authorize_redirect(
        AMAZON_REDIRECT_URI,
        response_type="code"
    )


@main.route("/auth/amazon/callback")
def amazon_callback():
    """Handle the Amazon OAuth callback.

    Returns:
        Response:
            Redirect response back to the dashboard after successful login.

    Notes:
        The access token is used to request the Amazon user profile. The
        profile is stored in the Flask session.
    """
    token = oauth.amazon.authorize_access_token()

    profile_response = requests.get(
        "https://api.amazon.com/user/profile",
        headers={"Authorization": f"Bearer {token['access_token']}"},
        timeout=10,
        verify=False
    )

    profile_response.raise_for_status()
    profile = profile_response.json()

    session["user"] = {
        "name": profile.get("name"),
        "email": profile.get("email"),
        "user_id": profile.get("user_id"),
    }

    return redirect(url_for("main.dashboard"))


@main.route("/logout")
def logout():
    """Clear the current user session and return to login.

    Returns:
        Response:
            Redirect response to the login route.
    """
    session.clear()
    return redirect(url_for("main.amazon_login"))


@main.route("/api/monitor", methods=["POST"])
def api_monitor():
    """Receive encrypted and signed monitoring data from agents.

    Returns:
        Response:
            JSON response with status information.

    Security:
        The request body must be a secure envelope. Plain JSON metrics are no
        longer accepted. The envelope is verified and decrypted by
        decode_secure_agent_request().

    Possible responses:
        - 200: data accepted and stored
        - 400: decrypted data is missing required fields
        - 403: signature, timestamp or decryption failed
        - 500: unexpected server error
    """
    try:
        envelope = request.get_json(force=True)

        data = security_verifier.decode_secure_agent_request(envelope)

        is_valid, message = validator.validate(data)
        if not is_valid:
            logging.warning("Ongeldige agentdata ontvangen: %s", message)
            return jsonify({
                "status": "error",
                "message": message
            }), 400

        metrics_db.insert_metric(data)
        logging.info("Versleutelde agentdata opgeslagen van: %s", data.get("hostname"))

        return jsonify({
            "status": "success",
            "message": "Versleutelde data ontvangen en opgeslagen"
        }), 200

    except AgentSecurityError as e:
        logging.warning("Agent security fout: %s", str(e))
        return jsonify({
            "status": "error",
            "message": "Agent authenticatie mislukt"
        }), 403

    except Exception as e:
        logging.exception("Fout in /api/monitor")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@main.route("/api/dashboard-data", methods=["GET"])
@login_required
def dashboard_data():
    """Return dashboard data as JSON for live refresh.

    Returns:
        Response:
            JSON object containing the current timestamp, grouped table data and
            graph data.
    """
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        agents = metrics_db.get_grouped_metrics(MAX_ROWS_PER_AGENT)
        graph_data = metrics_db.get_graph_data()

        return jsonify({
            "now": now,
            "agents": agents,
            "graph_data": graph_data
        })

    except Exception as e:
        logging.exception("Fout in /api/dashboard-data")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@main.route("/")
@login_required
def dashboard():
    """Render the monitoring data dashboard.

    Returns:
        Response:
            Rendered HTML dashboard page.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    agents = metrics_db.get_grouped_metrics(MAX_ROWS_PER_AGENT)

    return render_template(
        "index.html",
        now=now,
        agents=agents,
        user=session.get("user"),
        refresh_interval_ms=REFRESH_INTERVAL_MS
    )


@main.route("/cpu")
@login_required
def cpu_page():
    """Render the CPU graph page.

    Returns:
        Response:
            Rendered HTML page containing CPU graphs per agent.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    graph_data = metrics_db.get_graph_data()

    return render_template(
        "cpu.html",
        now=now,
        graph_data=graph_data,
        user=session.get("user"),
        refresh_interval_ms=REFRESH_INTERVAL_MS
    )


@main.route("/ram")
@login_required
def ram_page():
    """Render the RAM graph page.

    Returns:
        Response:
            Rendered HTML page containing RAM graphs per agent.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    graph_data = metrics_db.get_graph_data()

    return render_template(
        "ram.html",
        now=now,
        graph_data=graph_data,
        user=session.get("user"),
        refresh_interval_ms=REFRESH_INTERVAL_MS
    )


@main.route("/storage")
@login_required
def storage_page():
    """Render the storage graph page.

    Returns:
        Response:
            Rendered HTML page containing storage pie charts per agent.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    graph_data = metrics_db.get_graph_data()

    return render_template(
        "storage.html",
        now=now,
        graph_data=graph_data,
        user=session.get("user"),
        refresh_interval_ms=REFRESH_INTERVAL_MS
    )