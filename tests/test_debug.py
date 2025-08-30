"""
Debug tests to identify import and route registration issues.
"""


class TestDebugRoutes:
    """Debug tests for route registration."""

    def test_app_routes_registered(self, client):
        """Test that routes are properly registered."""
        with client.application.app_context():
            # Get all registered routes
            rules = list(client.application.url_map.iter_rules())
            rule_strings = [str(rule) for rule in rules]

            print(f"Registered routes: {rule_strings}")

            # Check for our expected routes
            login_routes = [rule for rule in rules if "/login" in str(rule)]
            print(f"Login routes found: {login_routes}")

            assert (
                len(login_routes) > 0
            ), f"No login routes found. All routes: {rule_strings}"

    def test_direct_route_access(self, client):
        """Test direct route access."""
        # Test if we can access any route
        try:
            response = client.get("/")
            print(f"Root route status: {response.status_code}")
        except Exception as e:
            print(f"Root route error: {e}")

        try:
            response = client.get("/login")
            print(f"Login route status: {response.status_code}")
            if response.status_code == 404:
                # Print available routes for debugging
                with client.application.app_context():
                    rules = [
                        str(rule) for rule in client.application.url_map.iter_rules()
                    ]
                    print(f"Available routes: {rules}")
        except Exception as e:
            print(f"Login route error: {e}")

        # This test is just for debugging
        assert True
