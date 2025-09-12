from src import app
from src.access_control import allowed_user_required
from flask_login import login_required
from src.route_protection import dev_only

"""Set up test routes for access control testing."""


@dev_only
@app.route("/test-blocked")
@allowed_user_required
def test_blocked():
    return "This should not be accessible"


@dev_only
@app.route("/test-protected")
@allowed_user_required
def test_protected():
    return "Access granted"


@dev_only
@app.route("/test-auth-required")
@allowed_user_required
def test_auth_required():
    return "Access granted"


@dev_only
@app.route("/test-logout-redirect")
@allowed_user_required
def test_logout_redirect():
    return "Access granted"


# Create a test route
@dev_only
@app.route("/test-config-error")
@allowed_user_required
def test_config_error():
    return "Should not reach here"


# Create a test route
@dev_only
@app.route("/test-no-user")
@allowed_user_required
def test_no_user():
    return "Should not reach here"


# Create a test route with both decorators
@dev_only
@app.route("/test-double-protection")
@login_required
@allowed_user_required
def test_double_protection():
    return "Double protected"


# Create routes with different decorator orders
@dev_only
@app.route("/test-order-1")
@allowed_user_required  # This includes @login_required
def test_order_1():
    return "Order 1"


@dev_only
@app.route("/test-order-2")
@login_required
@allowed_user_required
def test_order_2():
    return "Order 2"


# Create protected and unprotected routes
@dev_only
@app.route("/test-protected-perf")
@allowed_user_required
def test_protected_perf():
    return "Protected"


@dev_only
@app.route("/test-unprotected-perf")
def test_unprotected_perf():
    return "Unprotected"


# Create a route that will be called multiple times
@dev_only
@app.route("/test-config-access")
@allowed_user_required
def test_config_access():
    return "Config test"
