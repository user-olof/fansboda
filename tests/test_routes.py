import re
from datetime import date, timedelta
from decimal import Decimal

from src.models.market_metrics import MarketMetric
from src.models.metrics import Metric
from src.models.swe_metrics import SweMetric
from src.models.swe_ticker import SweTicker
from src.models.ticker import Ticker
from src.models.user import User
from src import db


def _assert_signal_after_trend_before_bolag(html):
    thead = html.split("<thead", 1)[1].split("</thead>", 1)[0]
    trend_pos = thead.find("Trend")
    signal_pos = thead.find("Signal")
    bolag_pos = thead.find("Bolag")
    assert trend_pos != -1 and signal_pos != -1 and bolag_pos != -1
    assert trend_pos < signal_pos < bolag_pos
    assert "Kors" not in thead


# Back-compat alias used during SPEC 013→014 transition in older diffs
_assert_kors_after_trend_before_bolag = _assert_signal_after_trend_before_bolag


def _week(n: int, origin: date | None = None) -> date:
    base = origin or date.today()
    return base + timedelta(weeks=n)


def _seed_kors_ticker(
    app,
    *,
    symbol: str,
    company: str,
    series: list[tuple[int, str | None, str | None]],
    exchange_name: str = "NASDAQ",
    origin: date | None = None,
):
    """Seed ticker + weekly Metric SMA history for Kors fixtures."""
    with app.app_context():
        db.session.add(
            Ticker(
                symbol=symbol,
                company=company,
                market="us_market",
                sector="Technology",
                exchange_name=exchange_name,
            )
        )
        for week, sma_50, sma_200 in series:
            db.session.add(
                Metric(
                    ticker=symbol,
                    company=company,
                    trading_date=_week(week, origin),
                    current_price=100.0,
                    sma_50=None if sma_50 is None else Decimal(sma_50),
                    sma_200=None if sma_200 is None else Decimal(sma_200),
                    currency="USD",
                    z_score=0,
                )
            )
        db.session.commit()


def _golden_sma_series():
    return [
        (0, "90", "100"),
        (1, "92", "100"),
        (2, "94", "100"),
        (3, "96", "100"),
        (4, "105", "100"),
    ]


def _death_sma_series():
    return [
        (0, "110", "100"),
        (1, "108", "100"),
        (2, "106", "100"),
        (3, "104", "100"),
        (4, "95", "100"),
    ]


def _kors_series_origin():
    """Five-week series ending near today so it stays inside the 52-week lookback."""
    return date.today() - timedelta(weeks=4)


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
        paged = client.get("/stocks?exchange=omx_stockholm&page=2")
        assert paged.status_code == 302
        assert "/login" in paged.location
        warm = client.get("/stocks/warm?exchange=omx_stockholm")
        assert warm.status_code == 302
        assert "/login" in warm.location
        body = response.get_data(as_text=True)
        assert "Positivt momentum kan indikera" not in body
        assert "Bearish" not in body
        assert "Kors" not in body
        assert "Signal" not in body
        assert "Golden" not in body
        assert "Death" not in body

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
        assert "Signal" in thead
        assert "Kors" not in thead
        assert "Heat" not in thead
        _assert_signal_after_trend_before_bolag(html)
        _assert_trend_legend(html)

    def test_stocks_trend_header_with_exchange_selected(self, client_with_user):
        html = client_with_user.get("/stocks?exchange=nasdaq").get_data(as_text=True)
        thead = html.split("<thead", 1)[1].split("</thead>", 1)[0]
        assert "Trend" in thead
        assert "Signal" in thead
        assert "Kors" not in thead
        assert "Heat" not in thead
        assert "Bolag" in thead
        assert "Industri" in thead
        _assert_signal_after_trend_before_bolag(html)
        assert 'colspan="7"' in html or "colspan='7'" in html
        _assert_trend_legend(html)

    def test_stocks_admin_sees_kors_header(self, client_with_admin_user):
        html = client_with_admin_user.get("/stocks?exchange=nasdaq").get_data(
            as_text=True
        )
        assert "Signal" in html
        assert "Kors" not in html.split("<thead", 1)[1].split("</thead>", 1)[0]
        _assert_signal_after_trend_before_bolag(html)

    def test_stocks_kors_golden_death_and_empty(self, client_with_user, app):
        origin = _kors_series_origin()
        crossover_iso = _week(4, origin).isoformat()
        _seed_kors_ticker(
            app,
            symbol="GOLD",
            company="Golden Co",
            series=_golden_sma_series(),
            origin=origin,
        )
        _seed_kors_ticker(
            app,
            symbol="DEAD",
            company="Death Co",
            series=_death_sma_series(),
            origin=origin,
        )
        _seed_kors_ticker(
            app,
            symbol="NONE",
            company="None Co",
            series=[(0, "100", "100"), (1, "101", "100")],
            origin=origin,
        )
        html = client_with_user.get("/stocks?exchange=nasdaq").get_data(as_text=True)
        assert response_has_signal_cell(html, "Golden", title=crossover_iso)
        assert response_has_signal_cell(html, "Death", title=crossover_iso)
        assert "None Co" in html
        # Empty placeholder present for non-qualifying row
        assert re.search(
            r'class="kors-cell"[^>]*>\s*—\s*</td>|class="kors-cell"[^>]*>\s*&mdash;\s*</td>',
            html,
        )
        # Em dash cells must not imply a crossover via title
        for match in re.finditer(
            r'<td class="kors-cell"[^>]*>\s*(?:—|&mdash;)\s*</td>', html
        ):
            assert "title=" not in match.group(0)

    def test_stocks_kors_stale_golden_clears(self, client_with_user, app):
        origin = _kors_series_origin() - timedelta(weeks=1)
        # Golden completes at week 4; add a later week so latest != crossover.
        series = _golden_sma_series() + [(5, "106", "100")]
        _seed_kors_ticker(
            app,
            symbol="STALE",
            company="Stale Cross Co",
            series=series,
            origin=origin,
        )
        html = client_with_user.get("/stocks?exchange=nasdaq").get_data(as_text=True)
        assert "Stale Cross Co" in html
        assert not response_has_signal_cell(html, "Golden")
        assert response_has_signal_cell(html, "—") or response_has_signal_cell(
            html, "&mdash;"
        )


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
                    momentum=0.89,
                    z_score=-2,
                )
            )
            db.session.add(
                MarketMetric(
                    market="us_market",
                    trading_date=trading_day,
                    momentum_mean=0.95,
                    momentum_std=0.05,
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
                    momentum=1.05,
                    z_score=2,
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
        assert "background-color: #1d4ed8" in html
        assert "background-color: #991b1b" in html
        assert "z=-2.00" in html
        assert "z=2.00" in html
        assert "z50=" not in html
        assert "z200=" not in html
        assert re.search(r'class="heat-cell[^"]*"[^>]*>\s*</td>', html)
        visible_heat = html.replace("z=-2.00", "").replace("z=2.00", "")
        assert "-2.00" not in visible_heat
        assert "2.00" not in visible_heat
        assert "Industri" in html
        thead = html.split("<thead", 1)[1].split("</thead>", 1)[0]
        assert "Trend" in thead
        assert "Signal" in thead
        assert "Kors" not in thead
        assert "Heat" not in thead
        _assert_signal_after_trend_before_bolag(html)
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
                    market="se_market",
                    trading_date=trading_day,
                    momentum_mean=2400.25,
                    momentum_std=0.2,
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



def response_has_signal_cell(html, label, title=None):
    """Match Signal cell by aria-label (Death|Golden) or em dash empty."""
    if label in ("—", "&mdash;"):
        pattern = r'class="kors-cell"[^>]*>\s*(?:—|&mdash;)\s*</td>'
        match = re.search(pattern, html)
        if not match:
            return False
        return True
    # Icon cell: aria-label on SVG inside kors-cell
    cell_pattern = rf'<td class="kors-cell"([^>]*)>.*?aria-label="{re.escape(label)}".*?</td>'
    match = re.search(cell_pattern, html, flags=re.DOTALL)
    if not match:
        return False
    if title is None:
        return True
    attrs = match.group(1)
    return f'title="{title}"' in attrs or f"title='{title}'" in attrs


response_has_kors_cell = response_has_signal_cell

def _assert_trend_legend(html):
    assert (
        "Positivt momentum kan indikera en potentiell uppåtgående (bullish) trend, medan negativt momentum kan indikera en nedåtgående (bearish) trend."
        in html
    )
    assert (
        "I bred bemärkelse kan momentum mätas både mellan olika tillgångsslag och för enskilda värdepapper, där marknadsmomentum i synnerhet avser den övergripande marknaden."
        in html
    )
    assert (
        "Trend mäts här som 50-dagars genomsnittligt pris dividerat med 200-dagars genomsnittligt pris."
        in html
    )
    assert "Bearish" in html
    assert "Bullish" in html
    assert "min-height: 15rem" not in html


def _seed_paged_nyse(app, count=26, include_nasdaq=False):
    trading_day = date.today() - timedelta(days=7)
    with app.app_context():
        if include_nasdaq:
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
        for index in range(1, count + 1):
            symbol = f"P{index:02d}"
            company = f"Paged Co {index:02d}"
            db.session.add(
                Ticker(
                    symbol=symbol,
                    company=company,
                    market="us_market",
                    exchange_name="NYSE",
                )
            )
            db.session.add(
                Metric(
                    ticker=symbol,
                    company=company,
                    trading_date=trading_day,
                    current_price=float(index),
                    currency="USD",
                )
            )
        db.session.commit()


def _tbody_row_count(html):
    tbody = html.split("<tbody", 1)[1].split("</tbody>", 1)[0]
    return tbody.count("<tr>")


def _has_usable_paging_link(html, label):
    return re.search(rf"<a[^>]*class=\"[^\"]*paging-btn[^\"]*\"[^>]*>\s*{label}", html) is not None


class TestAktierPaging:
    """25-row Aktier pages, totals, warm cache, and chart return."""

    def test_first_page_caps_at_25_and_shows_total(self, client_with_user, app):
        _seed_paged_nyse(app, count=26)
        html = client_with_user.get("/stocks?exchange=nyse").get_data(as_text=True)
        assert "1–25 av 26" in html or "1&ndash;25 av 26" in html
        assert "Paged Co 01" in html
        assert "Paged Co 25" in html
        assert "Paged Co 26" not in html
        assert _tbody_row_count(html) == 25
        assert "stocks.js" in html

    def test_page_two_has_26th_not_first(self, client_with_user, app):
        _seed_paged_nyse(app, count=26)
        html = client_with_user.get("/stocks?exchange=nyse&page=2").get_data(as_text=True)
        assert "26–26 av 26" in html or "26&ndash;26 av 26" in html
        assert "Paged Co 26" in html
        assert "Paged Co 01" not in html
        assert _tbody_row_count(html) == 1

    def test_first_page_has_no_usable_previous(self, client_with_user, app):
        _seed_paged_nyse(app, count=26)
        html = client_with_user.get("/stocks?exchange=nyse").get_data(as_text=True)
        assert "Föregående" in html
        assert "Nästa" in html
        assert not _has_usable_paging_link(html, "Föregående")
        assert _has_usable_paging_link(html, "Nästa")
        assert "page=2" in html
        assert "page=0" not in html

    def test_last_page_has_no_usable_next(self, client_with_user, app):
        _seed_paged_nyse(app, count=26)
        html = client_with_user.get("/stocks?exchange=nyse&page=2").get_data(as_text=True)
        assert _has_usable_paging_link(html, "Föregående")
        assert not _has_usable_paging_link(html, "Nästa")

    def test_page_99_clamps_to_last_page(self, client_with_user, app):
        _seed_paged_nyse(app, count=26)
        html = client_with_user.get("/stocks?exchange=nyse&page=99").get_data(as_text=True)
        assert "Paged Co 26" in html
        assert "Paged Co 01" not in html
        assert "26–26 av 26" in html or "26&ndash;26 av 26" in html

    def test_chart_back_keeps_exchange_and_page(self, client_with_user, app):
        _seed_paged_nyse(app, count=26)
        client_with_user.get("/stocks?exchange=nyse&page=2")
        html = client_with_user.get("/stocks/chart/P26").get_data(as_text=True)
        assert "Tillbaka till Aktier" in html
        assert "exchange=nyse" in html
        assert "page=2" in html

    def test_warm_requires_login(self, client):
        response = client.get("/stocks/warm?exchange=nyse")
        assert response.status_code == 302
        assert "/login" in response.location

    def test_warm_unknown_exchange_is_not_ok(self, client_with_user):
        response = client_with_user.get("/stocks/warm?exchange=tokyo")
        assert response.status_code == 400
        assert response.get_json()["ok"] is False

    def test_warm_fills_pages_for_logged_in_user(self, client_with_user, app):
        _seed_paged_nyse(app, count=26)
        response = client_with_user.get("/stocks/warm?exchange=nyse")
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["ok"] is True
        assert payload["total"] == 26
        assert payload["pages_cached"] == 2
        page_two = client_with_user.get("/stocks?exchange=nyse&page=2").get_data(
            as_text=True
        )
        assert "kors-cell" in page_two
        assert "Paged Co 26" in page_two

    def test_switching_exchange_does_not_mix_venues(self, client_with_user, app):
        _seed_paged_nyse(app, count=26, include_nasdaq=True)
        page_two = client_with_user.get("/stocks?exchange=nyse&page=2").get_data(
            as_text=True
        )
        assert "Paged Co 26" in page_two
        assert "Apple Inc." not in page_two
        nasdaq = client_with_user.get("/stocks?exchange=nasdaq").get_data(as_text=True)
        assert "Apple Inc." in nasdaq
        assert "Paged Co 26" not in nasdaq
        assert "Paged Co 01" not in nasdaq


class TestAktierSort:
    """SPEC 014: full-exchange sort then paginate."""

    def test_sort_headers_and_aria(self, client_with_user, app):
        _seed_paged_nyse(app, count=3)
        html = client_with_user.get(
            "/stocks?exchange=nyse&sort=bolag&dir=asc"
        ).get_data(as_text=True)
        thead = html.split("<thead", 1)[1].split("</thead>", 1)[0]
        assert "Signal" in thead
        assert 'aria-sort="ascending"' in thead
        assert "sort=bolag" in html
        assert "dir=desc" in html  # next click toggles

    def test_bolag_sort_is_global_across_pages(self, client_with_user, app):
        trading_day = date.today() - timedelta(days=7)
        with app.app_context():
            # 26 rows: Z-company is alphabetically last → page 2 under bolag asc
            for index in range(1, 26):
                symbol = f"P{index:02d}"
                db.session.add(
                    Ticker(
                        symbol=symbol,
                        company=f"Paged Co {index:02d}",
                        market="us_market",
                        exchange_name="NYSE",
                    )
                )
                db.session.add(
                    Metric(
                        ticker=symbol,
                        company=f"Paged Co {index:02d}",
                        trading_date=trading_day,
                        current_price=float(index),
                        currency="USD",
                        z_score=0,
                    )
                )
            db.session.add(
                Ticker(
                    symbol="ZZZ",
                    company="Zeta Last",
                    market="us_market",
                    exchange_name="NYSE",
                )
            )
            db.session.add(
                Metric(
                    ticker="ZZZ",
                    company="Zeta Last",
                    trading_date=trading_day,
                    current_price=1.0,
                    currency="USD",
                    z_score=0,
                )
            )
            db.session.commit()

        page1 = client_with_user.get(
            "/stocks?exchange=nyse&sort=bolag&dir=asc&page=1"
        ).get_data(as_text=True)
        assert "Paged Co 01" in page1
        assert "Zeta Last" not in page1
        page2 = client_with_user.get(
            "/stocks?exchange=nyse&sort=bolag&dir=asc&page=2"
        ).get_data(as_text=True)
        assert "Zeta Last" in page2
        assert "Paged Co 01" not in page2
        assert "sort=bolag" in page2
        assert "dir=asc" in page2

    def test_trend_sort_brings_high_z_to_page_one(self, client_with_user, app):
        trading_day = date.today() - timedelta(days=7)
        with app.app_context():
            for index in range(1, 27):
                symbol = f"P{index:02d}"
                z = 5.0 if symbol == "P26" else float(index) / 100.0
                db.session.add(
                    Ticker(
                        symbol=symbol,
                        company=f"Paged Co {index:02d}",
                        market="us_market",
                        exchange_name="NYSE",
                    )
                )
                db.session.add(
                    Metric(
                        ticker=symbol,
                        company=f"Paged Co {index:02d}",
                        trading_date=trading_day,
                        current_price=float(index),
                        currency="USD",
                        z_score=z,
                    )
                )
            db.session.commit()

        html = client_with_user.get(
            "/stocks?exchange=nyse&sort=trend&dir=desc&page=1"
        ).get_data(as_text=True)
        assert "Paged Co 26" in html
        assert 'aria-sort="descending"' in html

    def test_invalid_sort_falls_back_to_symbol_order(self, client_with_user, app):
        _seed_paged_nyse(app, count=26)
        html = client_with_user.get(
            "/stocks?exchange=nyse&sort=nope&dir=asc&page=1"
        ).get_data(as_text=True)
        assert "Paged Co 01" in html
        assert "Paged Co 26" not in html
        assert "sort=nope" not in html

    def test_sort_change_resets_to_page_one_in_header_links(self, client_with_user, app):
        _seed_paged_nyse(app, count=26)
        html = client_with_user.get(
            "/stocks?exchange=nyse&page=2&sort=bolag&dir=asc"
        ).get_data(as_text=True)
        assert "page=1" in html
        assert "sort=trend" in html

    def test_chart_back_preserves_sort(self, client_with_user, app):
        _seed_paged_nyse(app, count=26)
        client_with_user.get("/stocks?exchange=nyse&page=2&sort=bolag&dir=asc")
        html = client_with_user.get("/stocks/chart/P26").get_data(as_text=True)
        assert "exchange=nyse" in html
        assert "page=2" in html
        assert "sort=bolag" in html
        assert "dir=asc" in html


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
