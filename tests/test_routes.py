import re
from datetime import date, timedelta

from src.models.market_metrics import MarketMetric
from src.models.metrics import Metric
from src.models.swe_metrics import SweMetric
from src.models.swe_ticker import SweTicker
from src.models.ticker import Ticker
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
        filtered = client.get("/stocks?exchange=nasdaq")
        assert filtered.status_code == 302
        assert "/login" in filtered.location

    def test_stocks_empty_table_when_logged_in(self, client_with_user):
        response = client_with_user.get("/stocks")
        html = response.get_data(as_text=True)
        assert response.status_code == 200
        assert "NASDAQ" in html
        assert "NYSE" in html
        assert "OMX Stockholm" in html
        assert "Välj en börs" in html or "V&auml;lj en b&ouml;rs" in html
        assert "Inga aktier" not in html
        assert "Industri" in html
        assert "Beskrivning" not in html
        thead = html.split("<thead", 1)[1].split("</thead>", 1)[0]
        assert "Trend" in thead
        assert "Heat" not in thead

    def test_stocks_trend_header_with_exchange_selected(self, client_with_user):
        html = client_with_user.get("/stocks?exchange=nasdaq").get_data(as_text=True)
        thead = html.split("<thead", 1)[1].split("</thead>", 1)[0]
        assert "Trend" in thead
        assert "Heat" not in thead
        assert "Bolag" in thead
        assert "Industri" in thead

    def test_stocks_heatmap_uses_z_score_vs_market(self, client_with_user, app):
        trading_day = date.today() - timedelta(days=7)
        with app.app_context():
            db.session.add(
                Ticker(
                    symbol="AAPL",
                    company="Apple Inc.",
                    market="us_market",
                    sector="Technology",
                    exchange_name="NASDAQ",
                )
            )
            db.session.add(
                Metric(
                    ticker="AAPL",
                    company="Apple Inc.",
                    trading_date=trading_day,
                    current_price=100.0,
                    sma_50=90.0,
                    sma_200=80.0,
                    currency="USD",
                    raw_50=0.85,
                    raw_200=0.85,
                )
            )
            db.session.add(
                MarketMetric(
                    market="us_market",
                    trading_date=trading_day,
                    raw_mean_50=0.95,
                    raw_mean_200=0.95,
                    raw_std_50=0.05,
                    raw_std_200=0.05,
                )
            )
            db.session.add(
                Metric(
                    ticker="MSFT",
                    company="Microsoft",
                    trading_date=trading_day,
                    current_price=200.0,
                    sma_50=190.0,
                    sma_200=180.0,
                    currency="USD",
                    raw_50=0.95,
                    raw_200=0.95,
                )
            )
            db.session.add(
                Ticker(
                    symbol="MSFT",
                    company="Microsoft",
                    market="us_market",
                    sector="   ",
                    exchange_name="NASDAQ",
                )
            )
            db.session.commit()

        response = client_with_user.get("/stocks?exchange=nasdaq")
        html = response.get_data(as_text=True)
        assert response.status_code == 200
        assert "background-color: #991b1b" in html
        assert "z50=-2.00" in html
        assert "z200=-2.00" in html
        assert re.search(r'class="heat-cell[^"]*"[^>]*>\s*</td>', html)
        visible_heat = html.replace("z50=-2.00", "").replace("z200=-2.00", "")
        assert "-2.00" not in visible_heat
        assert "Industri" in html
        thead = html.split("<thead", 1)[1].split("</thead>", 1)[0]
        assert "Trend" in thead
        assert "Heat" not in thead
        assert "Technology" in html
        assert "Beskrivning" not in html
        assert "industri-cell" in html
        assert re.search(r'class="industri-cell">\s*</td>', html)

    def test_stocks_industri_replaces_dashes_with_spaces(self, client_with_user, app):
        trading_day = date.today() - timedelta(days=7)
        with app.app_context():
            db.session.add(
                Ticker(
                    symbol="GOOGL",
                    company="Alphabet Inc.",
                    market="us_market",
                    sector="communication-services",
                    exchange_name="NASDAQ",
                )
            )
            db.session.add(
                Metric(
                    ticker="GOOGL",
                    company="Alphabet Inc.",
                    trading_date=trading_day,
                    current_price=100.0,
                    sma_50=90.0,
                    sma_200=80.0,
                    currency="USD",
                )
            )
            db.session.commit()

        html = client_with_user.get("/stocks?exchange=nasdaq").get_data(as_text=True)
        assert "communication services" in html
        assert "communication-services" not in html
        assert "Industri" in html

    def test_stocks_filters_by_exchange_name(self, client_with_user, app):
        trading_day = date.today() - timedelta(days=7)
        with app.app_context():
            db.session.add(
                Ticker(
                    symbol="AAPL",
                    company="Apple Inc.",
                    market="us_market",
                    exchange_name="NASDAQ",
                )
            )
            db.session.add(
                Ticker(
                    symbol="IBM",
                    company="IBM",
                    market="us_market",
                    exchange_name="NYSE",
                )
            )
            db.session.add(
                Ticker(
                    symbol="ORCL",
                    company="Oracle",
                    market="us_market",
                    exchange_name="",
                )
            )
            db.session.add(
                SweTicker(
                    symbol="VOLV-B.ST",
                    company="Volvo AB",
                    market="se_market",
                    exchange_name="OMX Stockholm",
                )
            )
            for ticker, company, currency, model in (
                ("AAPL", "Apple Inc.", "USD", Metric),
                ("IBM", "IBM", "USD", Metric),
                ("ORCL", "Oracle", "USD", Metric),
                ("VOLV-B.ST", "Volvo AB", "SEK", SweMetric),
            ):
                db.session.add(
                    model(
                        ticker=ticker,
                        company=company,
                        trading_date=trading_day,
                        current_price=100.0,
                        currency=currency,
                    )
                )
            db.session.commit()

        nasdaq = client_with_user.get("/stocks?exchange=nasdaq").get_data(as_text=True)
        assert "Apple Inc." in nasdaq
        assert "IBM" not in nasdaq
        assert "Oracle" not in nasdaq
        assert "Volvo AB" not in nasdaq
        assert "exchange-btn--selected" in nasdaq

        nyse = client_with_user.get("/stocks?exchange=nyse").get_data(as_text=True)
        assert "IBM" in nyse
        assert "Apple Inc." not in nyse
        assert "Volvo AB" not in nyse

        omx = client_with_user.get("/stocks?exchange=omx_stockholm").get_data(
            as_text=True
        )
        assert "Volvo AB" in omx
        assert "Apple Inc." not in omx
        assert "IBM" not in omx

    def test_stocks_nasdaq_matches_nasdaqgs(self, client_with_user, app):
        trading_day = date.today() - timedelta(days=7)
        with app.app_context():
            db.session.add(
                Ticker(
                    symbol="AAPL",
                    company="Apple Inc.",
                    market="us_market",
                    exchange_name="NasdaqGS",
                )
            )
            db.session.add(
                Metric(
                    ticker="AAPL",
                    company="Apple Inc.",
                    trading_date=trading_day,
                    current_price=100.0,
                    currency="USD",
                )
            )
            db.session.commit()

        html = client_with_user.get("/stocks?exchange=nasdaq").get_data(as_text=True)
        assert "Apple Inc." in html

    def test_stocks_first_visit_does_not_list_mixed_rows(self, client_with_user, app):
        trading_day = date.today() - timedelta(days=7)
        with app.app_context():
            db.session.add(
                Ticker(
                    symbol="AAPL",
                    company="Apple Inc.",
                    market="us_market",
                    exchange_name="NASDAQ",
                )
            )
            db.session.add(
                Metric(
                    ticker="AAPL",
                    company="Apple Inc.",
                    trading_date=trading_day,
                    current_price=100.0,
                    currency="USD",
                )
            )
            db.session.commit()

        html = client_with_user.get("/stocks").get_data(as_text=True)
        assert "Apple Inc." not in html
        assert "exchange-btn--selected" not in html
        assert "V&auml;lj en b&ouml;rs" in html or "Välj en börs" in html

        unknown = client_with_user.get("/stocks?exchange=tokyo").get_data(as_text=True)
        assert "Apple Inc." not in unknown
        assert "exchange-btn--selected" not in unknown

        empty = client_with_user.get("/stocks?exchange=nyse")
        empty_html = empty.get_data(as_text=True)
        assert empty.status_code == 200
        assert "Inga aktier" in empty_html
        assert "Apple Inc." not in empty_html

    def test_chart_unknown_ticker_does_not_500(self, client_with_user):
        response = client_with_user.get("/stocks/chart/NOT-A-TICKER")
        assert response.status_code == 200
        assert "Ingen kursdata" in response.get_data(as_text=True)

    def test_latest_prices_require_login(self, client):
        response = client.get("/stocks/latest")
        assert response.status_code == 302
        assert "/login" in response.location

    def test_chart_redirect_when_not_logged_in(self, client):
        response = client.get("/stocks/chart/VOLV-B.ST")
        assert response.status_code == 302
        assert "/login" in response.location

    def test_chart_shows_stock_series_without_market_sma(self, client_with_user, app):
        trading_day = date.today() - timedelta(days=7)
        with app.app_context():
            db.session.add(
                Metric(
                    ticker="VOLV-B.ST",
                    company="Volvo AB",
                    trading_date=trading_day,
                    current_price=265.5,
                    sma_50=250.0,
                    sma_200=230.0,
                    currency="SEK",
                )
            )
            db.session.add(
                MarketMetric(
                    market="se_market", trading_date=trading_day, raw_mean_200=2400.25
                )
            )
            db.session.commit()

        response = client_with_user.get("/stocks/chart/VOLV-B.ST")
        html = response.get_data(as_text=True)
        assert response.status_code == 200
        assert "Volvo AB" in html
        assert "label: 'Kurs'" in html
        assert "label: 'SMA 50'" in html
        assert "label: 'SMA 200'" in html
        assert "Market SMA-200" not in html
        assert "2400.25" not in html
        assert "yAxisID: 'y1'" not in html


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
