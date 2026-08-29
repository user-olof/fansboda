from src.models.user import User
from src import db


class TestRoutes:
    """Test cases for application routes."""

    def test_index_route_redirect_when_not_logged_in(self, client):
        """Test that index route redirects to login when not authenticated."""
        response = client.get("/")
        assert response.status_code == 302
        assert "/login" in response.location

    def test_index_route_with_login(self, client, auth):
        """Test index route when logged in."""
        with client.application.app_context():
            # Create a test user
            user = User(email="test@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Login and access index
            resp = auth.login(follow_redirects=False)
            assert resp.status_code == 302
            assert "/" in resp.location
            with client.session_transaction() as sess:
                flashes = sess.get("_flashes", [])
                messages = [m for _, m in flashes]
                assert any("Welcome back" in m for m in messages)

    def test_login_route_get(self, client):
        """Test login route GET request."""
        response = client.get("/login")
        assert response.status_code == 200
        # Note: This will fail without the login.html template
        # You'll need to create the template or mock the render_template

    def test_login_route_post_valid_credentials(self, client):
        """Test login with valid credentials."""
        with client.application.app_context():
            # Create a test user
            user = User(email="test@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

        response = client.post(
            "/login", data={"email": "test@example.com", "password": "testpass"}
        )
        assert response.status_code == 302
        assert "/" in response.location

    def test_login_route_post_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = client.post(
            "/login", data={"email": "nonexistent", "password": "wrongpass"}
        )
        assert response.status_code == 302
        assert "/login" in response.location

    def test_login_redirect_when_already_authenticated(self, client, auth):
        """Test that login redirects to index when already authenticated."""
        with client.application.app_context():
            # Create a test user
            user = User(email="test@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Try to access login page again

            # Login first
            auth.login()
            response = client.get("/login")
            assert response.status_code == 302
            assert "/" in response.location

    def test_logout_route(self, client, auth):
        """Test logout route."""
        with client.application.app_context():
            # Create a test user
            user = User(email="test@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Login first
            response = auth.login()
            assert response.status_code == 200

            # Then logout
            # response = client.get("/logout")
            response = auth.logout()
            assert response.status_code == 200

            # Verify we're logged out by trying to access protected route
            response = client.get("/")
            assert response.status_code == 302
            assert "/login" in response.location

    def test_signup_logs_user_in(self, client):
        """Test that successful signup logs the user in and grants dashboard access."""
        client.application.config["ALLOWED_EMAILS"] = ["newuser@example.com"]

        response = client.post(
            "/signup",
            data={
                "email": "newuser@example.com",
                "password": "newpass",
                "password_confirm": "newpass",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/" in response.location

        dashboard = client.get("/")
        assert dashboard.status_code == 200

    def test_login_uninvited_user_is_rejected(self, client, app):
        """Existing account not on ALLOWED_EMAILS cannot sign in."""
        original_allowed = list(app.config.get("ALLOWED_EMAILS") or [])
        app.config["ALLOWED_EMAILS"] = ["invited@example.com"]
        try:
            with client.application.app_context():
                user = User(email="other@example.com")
                user.password_hash = "testpass"
                db.session.add(user)
                db.session.commit()

            response = client.post(
                "/login",
                data={"email": "other@example.com", "password": "testpass"},
                follow_redirects=False,
            )
            assert response.status_code == 302
            assert "/login" in response.location
            assert client.get("/").status_code == 302
        finally:
            app.config["ALLOWED_EMAILS"] = original_allowed


class TestElectricityEmail:
    """Landing-page bill email endpoint."""

    def test_landing_has_aktier_link(self, client_with_user):
        response = client_with_user.get("/")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "Aktier" in html
        assert "/stocks" in html

    def test_send_email_requires_login(self, client):
        response = client.post(
            "/send-email",
            json={"service": "telekom", "amount": "200.00"},
        )
        assert response.status_code in (302, 401)

    def test_send_email_rejects_missing_payload(self, client_with_user):
        response = client_with_user.post("/send-email", json={})
        assert response.status_code == 400
        assert response.get_json()["success"] is False

    def test_send_email_rejects_non_positive_amount(self, client_with_user):
        response = client_with_user.post(
            "/send-email",
            json={"service": "telekom", "amount": "0"},
        )
        assert response.status_code == 400

        response = client_with_user.post(
            "/send-email",
            json={"service": "telekom", "amount": "-10"},
        )
        assert response.status_code == 400


class TestAktierRoutes:
    """Aktier table and 52-week chart."""

    def test_stocks_redirect_when_not_logged_in(self, client):
        response = client.get("/stocks")
        assert response.status_code == 302
        assert "/login" in response.location

    def test_stocks_empty_table_when_logged_in(self, client_with_user):
        response = client_with_user.get("/stocks")
        assert response.status_code == 200
        assert "Inga aktier" in response.get_data(as_text=True)

    def test_chart_unknown_ticker_does_not_500(self, client_with_user):
        response = client_with_user.get("/stocks/chart/NOT-A-TICKER")
        assert response.status_code == 200
        assert "Ingen kursdata" in response.get_data(as_text=True)

    def test_latest_prices_require_login(self, client):
        response = client.get("/stocks/latest")
        assert response.status_code == 302
        assert "/login" in response.location


class TestErrorHandlers:
    """Test cases for error handlers."""

    def test_404_error_handler(self, client):
        """Test 404 error handler."""
        response = client.get("/nonexistent-route")
        assert response.status_code == 404
        # Note: This will fail without the 404.html template properly configured

    def test_500_error_handler(self, mocker):
        """Unhandled exceptions return 500 with a generic message and are logged."""
        from src import create_app

        app = create_app("test")
        app.config["DEBUG"] = False
        app.debug = False
        mock_log = mocker.patch.object(app.logger, "exception")

        @app.route("/test-trigger-500")
        def trigger_500():
            raise RuntimeError("secret internal error detail")

        with app.test_client() as client:
            response = client.get("/test-trigger-500")

        assert response.status_code == 500
        assert b"secret internal error detail" not in response.data
        assert b"Something went wrong" in response.data
        assert b"An unexpected error occurred" in response.data
        mock_log.assert_called_once_with("Unhandled exception")

    def test_500_error_handler_debug_shows_detail(self):
        """In debug mode, the 500 page may include the exception message."""
        from src import create_app

        app = create_app("test")
        app.config["DEBUG"] = True
        app.debug = True

        @app.route("/test-trigger-500-debug")
        def trigger_500_debug():
            raise RuntimeError("debug error detail")

        with app.test_client() as client:
            response = client.get("/test-trigger-500-debug")

        assert response.status_code == 500
        assert b"debug error detail" in response.data
