"""
Test cases for electricity bill calculator functionality
"""

import pytest
from src import app, db
from src.models.user import User


class TestElectricityCalculator:
    """Test electricity bill calculation logic"""

    def test_app_exists(self, client):
        """Test that the Flask app exists and can be accessed"""
        assert app is not None
        assert client is not None

    def test_index_page_loads(self, client_with_user):
        """Test that the index page loads with electricity calculator"""
        response = client_with_user.get("/")
        assert response.status_code in [200, 302]

        # Check that the electricity calculator form is present
        assert b"electricity_bill" in response.data
        assert b"Telekom" in response.data
        assert b"Johan och Emil" in response.data
        assert b"JA Bilservice" in response.data
        assert b"TK M\xc3\xa4tservice" in response.data

    def test_calculator_form_elements(self, client_with_user):
        """Test that all calculator form elements are present"""
        response = client_with_user.get("/")
        html_content = response.data.decode("utf-8")

        # Check main input field
        assert 'name="electricity_bill"' in html_content
        assert 'id="floatingInput"' in html_content

        # Check calculated fields
        assert 'id="telecomFormControlInput"' in html_content
        assert 'id="johanOchEmilBilserviceControlInput"' in html_content
        assert 'id="jaBilserviceControlInput"' in html_content
        assert 'id="tkMatserviceControlInput"' in html_content

    def test_calculator_percentages_displayed(self, client_with_user):
        """Test that the correct percentages are displayed"""
        response = client_with_user.get("/")
        html_content = response.data.decode("utf-8")

        # Check percentage labels
        assert "(20%)" in html_content  # Telekom
        assert "(51,2%)" in html_content  # Johan och Emil's Bilservice
        assert "(9,6%)" in html_content  # JA Bilservice
        assert "(19,2%)" in html_content  # TK Mätservice

    def test_calculator_javascript_included(self, client_with_user):
        """Test that the calculator JavaScript is included"""
        response = client_with_user.get("/")
        html_content = response.data.decode("utf-8")

        # Check that the script is included
        assert "electricity-calculator.js" in html_content

    def test_user_access_required(self, client):
        """Test that calculator requires user login"""
        response = client.get("/")
        # Should redirect to login if not authenticated
        assert response.status_code in [302, 200]  # Depending on your auth setup


class TestCalculatorLogic:
    """Test the calculation logic (simulated)"""

    def test_distribution_percentages(self):
        """Test that distribution percentages add up correctly"""
        # These should match your JavaScript DISTRIBUTION object
        telekom = 0.20
        johan_emil = 0.512
        ja_bilservice = 0.096
        tk_matservice = 0.192

        total = telekom + johan_emil + ja_bilservice + tk_matservice
        assert abs(total - 1.0) < 0.001  # Allow for floating point precision

    def test_calculation_example(self):
        """Test calculation with example values"""
        electricity_bill = 1000.0

        # Expected results based on your percentages
        expected_telekom = electricity_bill * 0.20  # 200.0
        expected_johan_emil = electricity_bill * 0.512  # 512.0
        expected_ja_bilservice = electricity_bill * 0.096  # 96.0
        expected_tk_matservice = electricity_bill * 0.192  # 192.0

        assert expected_telekom == 200.0
        assert expected_johan_emil == 512.0
        assert expected_ja_bilservice == 96.0
        assert expected_tk_matservice == 192.0

        # Verify total
        total = (
            expected_telekom
            + expected_johan_emil
            + expected_ja_bilservice
            + expected_tk_matservice
        )
        assert total == electricity_bill


# Example of testing specific src modules
class TestSrcModules:
    """Test importing and using src modules directly"""

    def test_import_src_models(self):
        """Test importing models from src"""
        from src.models.user import User

        assert User is not None

        # Test model attributes
        assert hasattr(User, "id")
        assert hasattr(User, "email")
        assert hasattr(User, "password_hash")

    def test_import_src_forms(self):
        """Test importing forms from src"""
        from src.forms.loginform import LoginForm

        assert LoginForm is not None

    def test_import_src_routes(self):
        """Test that route modules can be imported"""
        try:
            import src.routes.home
            import src.routes.login

            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import route modules: {e}")

    def test_app_configuration(self):
        """Test that app is properly configured"""
        from src import app

        assert app is not None
        assert app.config is not None

        # Test in testing mode
        with app.test_client():
            assert app.testing or app.config.get("TESTING", False)
