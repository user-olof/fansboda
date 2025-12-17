# src/routes/home.py
from flask import Blueprint, render_template, request, jsonify
from src.access_control import allowed_user_required, admin_required
from src.models.user import User
from src.route_protection import dev_only
from src.services.gmail_service import send_email
from datetime import datetime
import os

home_bp = Blueprint("home", __name__)

# Map service identifiers to company information
COMPANY_INFO = {
    "telekom": {
        "name": "Telekom",
        "email": os.getenv("TELECOM_EMAIL"),
    },
    "johanOchEmilBilservice": {
        "name": "Johan och Emil's Bilservice",
        "email": os.getenv("JOHAN_AND_EMIL_BILSERVICE_EMAIL"),
    },
    "jaBilservice": {
        "name": "JA Bilservice",
        "email": os.getenv("JA_BILSERVICE_EMAIL"),
    },
    "tkMatservice": {
        "name": "TK Mätservice",
        "email": os.getenv("TK_MATSERVICE_EMAIL"),
    },
}

# Swedish month names
SWEDISH_MONTHS = [
    "januari",
    "februari",
    "mars",
    "april",
    "maj",
    "juni",
    "juli",
    "augusti",
    "september",
    "oktober",
    "november",
    "december",
]


def get_last_month_swedish():
    """Get last month's name in Swedish."""
    today = datetime.now()
    # Get last month
    if today.month == 1:
        last_month = 12
    else:
        last_month = today.month - 1

    return SWEDISH_MONTHS[last_month - 1]


@home_bp.route("/health")
def health():
    return "OK", 200


@home_bp.route("/")
@home_bp.route("/index")
@allowed_user_required  # Basic authentication required
def index():
    return render_template("index.html", title="Dashboard", status_code=200)


@home_bp.route("/send-email", methods=["POST"])
@allowed_user_required
def send_electricity_email():
    """Endpoint to send electricity bill email via Gmail API."""
    try:
        data = request.get_json()
        service_key = data.get("service")
        amount = data.get("amount")

        if not service_key or not amount:
            return (
                jsonify({"success": False, "error": "Missing service or amount"}),
                400,
            )

        # Get company info
        company_info = COMPANY_INFO.get(service_key)
        if not company_info:
            return jsonify({"success": False, "error": "Invalid service"}), 400

        # Validate email is set
        if not company_info["email"]:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Email address not configured for {service_key}",
                    }
                ),
                500,
            )

        # Get last month in Swedish
        last_month = get_last_month_swedish()

        # Compose email
        subject = f"Elräkning för {last_month}"
        body = (
            f"Hej {company_info['name']},\n\n"
            f"Er elräkning för {last_month} var {amount}.\n\n"
            f"Bästa hälsningar\n"
            f"Metallen AB"
        )

        # Send email
        result = send_email(
            to_email=company_info["email"], subject=subject, body_text=body
        )

        if result["success"]:
            return jsonify({"success": True, "message": "Email sent successfully"}), 200
        else:
            return (
                jsonify(
                    {"success": False, "error": result.get("error", "Unknown error")}
                ),
                500,
            )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@home_bp.route("/users")
@admin_required  # Only admins can see all users
def users():
    users_list = User.query.all()
    return render_template("users.html", title="Users", users=users_list)


@home_bp.route("/admin")
@admin_required  # Admin-only dashboard
def admin_dashboard():
    return render_template("admin.html", title="Admin Dashboard")


@home_bp.route("/users/<int:user_id>")
@allowed_user_required  # Regular users can view profiles
def user(user_id):
    user = User.query.get_or_404(user_id)
    return render_template("user_profile.html", title=f"User {user.email}", user=user)


@home_bp.route("/users/<string:email>")
@allowed_user_required
def user_by_email(email):
    user = User.query.filter_by(email=email).first_or_404()
    return render_template("user_profile.html", title=f"User {user.email}", user=user)
