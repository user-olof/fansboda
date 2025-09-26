"""
Test cases for email whitelist security functionality.

This module tests the new security features including:
- Email whitelist validation
- Login security checks
- Route access control
- Configuration-based security
"""

from src.models.user import User


class TestEmailWhitelist:
    """Test email whitelist functionality."""

    def test_user_is_allowed_with_whitelisted_email(self, client, app):
        """Test that users with whitelisted emails are allowed."""
        app.config["ALLOWED_EMAILS"] = ["allowed@example.com", "test@example.com"]

        with client.application.app_context():
            user = User(email="allowed@example.com")
            user.password_hash = "testpass"

            assert user.is_allowed() is True

    def test_user_is_allowed_with_non_whitelisted_email(self, client, app):
        """Test that users with non-whitelisted emails are not allowed."""
        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]

        with client.application.app_context():
            user = User(email="notallowed@example.com")
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_empty_whitelist(self, client, app):
        """Test that users are not allowed when whitelist is empty."""
        app.config["ALLOWED_EMAILS"] = []

        with client.application.app_context():
            user = User(email="any@example.com")
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_missing_whitelist(self, client, app):
        """Test that users are not allowed when whitelist is missing."""
        # Remove ALLOWED_EMAILS from config
        if "ALLOWED_EMAILS" in app.config:
            del app.config["ALLOWED_EMAILS"]

        with client.application.app_context():
            user = User(email="any@example.com")
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_case_insensitive(self, client, app):
        """Test that email whitelist is case insensitive."""
        app.config["ALLOWED_EMAILS"] = ["Test@Example.com"]

        with client.application.app_context():
            user = User(email="test@example.com")
            user.password_hash = "testpass"

            assert user.is_allowed() is True

    def test_user_is_allowed_with_multiple_emails(self, client, app):
        """Test that users with any whitelisted email are allowed."""
        app.config["ALLOWED_EMAILS"] = [
            "user1@example.com",
            "user2@example.com",
            "user3@example.com",
        ]

        with client.application.app_context():
            user1 = User(email="user1@example.com")
            user1.password_hash = "testpass"
            assert user1.is_allowed() is True

            user2 = User(email="user2@example.com")
            user2.password_hash = "testpass"
            assert user2.is_allowed() is True

            user3 = User(email="user3@example.com")
            user3.password_hash = "testpass"
            assert user3.is_allowed() is True

            user4 = User(email="user4@example.com")
            user4.password_hash = "testpass"
            assert user4.is_allowed() is False

    def test_user_is_allowed_with_duplicate_emails(self, client, app):
        """Test that duplicate emails in whitelist work correctly."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com", "user@example.com"]

        with client.application.app_context():
            user = User(email="user@example.com")
            user.password_hash = "testpass"

            assert user.is_allowed() is True

    def test_user_is_allowed_with_whitespace_emails(self, client, app):
        """Test that emails with whitespace are handled correctly."""
        app.config["ALLOWED_EMAILS"] = [" user@example.com ", "another@example.com"]

        with client.application.app_context():
            user1 = User(email="user@example.com")
            user1.password_hash = "testpass"
            assert user1.is_allowed() is True

            user2 = User(email="another@example.com")
            user2.password_hash = "testpass"
            assert user2.is_allowed() is True

    def test_user_is_allowed_with_empty_string_emails(self, client, app):
        """Test that empty string emails in whitelist are ignored."""
        app.config["ALLOWED_EMAILS"] = ["", "user@example.com", ""]

        with client.application.app_context():
            user = User(email="user@example.com")
            user.password_hash = "testpass"

            assert user.is_allowed() is True

    def test_user_is_allowed_with_none_emails(self, client, app):
        """Test that None emails in whitelist are handled gracefully."""
        app.config["ALLOWED_EMAILS"] = [None, "user@example.com", None]

        with client.application.app_context():
            user = User(email="user@example.com")
            user.password_hash = "testpass"

            assert user.is_allowed() is True

    def test_user_is_allowed_with_invalid_emails(self, client, app):
        """Test that invalid emails in whitelist are handled gracefully."""
        app.config["ALLOWED_EMAILS"] = [
            "invalid-email",
            "user@example.com",
            "also-invalid",
        ]

        with client.application.app_context():
            user = User(email="user@example.com")
            user.password_hash = "testpass"

            assert user.is_allowed() is True

    def test_user_is_allowed_with_mixed_case_emails(self, client, app):
        """Test that mixed case emails work correctly."""
        app.config["ALLOWED_EMAILS"] = ["User@Example.com", "ANOTHER@EXAMPLE.COM"]

        with client.application.app_context():
            user1 = User(email="user@example.com")
            user1.password_hash = "testpass"
            assert user1.is_allowed() is True

            user2 = User(email="another@example.com")
            user2.password_hash = "testpass"
            assert user2.is_allowed() is True

    def test_user_is_allowed_with_special_characters(self, client, app):
        """Test that emails with special characters work correctly."""
        app.config["ALLOWED_EMAILS"] = ["user+tag@example.com", "user.name@example.com"]

        with client.application.app_context():
            user1 = User(email="user+tag@example.com")
            user1.password_hash = "testpass"
            assert user1.is_allowed() is True

            user2 = User(email="user.name@example.com")
            user2.password_hash = "testpass"
            assert user2.is_allowed() is True

    def test_user_is_allowed_with_unicode_emails(self, client, app):
        """Test that unicode emails work correctly."""
        app.config["ALLOWED_EMAILS"] = ["üser@example.com", "测试@example.com"]

        with client.application.app_context():
            user1 = User(email="üser@example.com")
            user1.password_hash = "testpass"
            assert user1.is_allowed() is True

            user2 = User(email="测试@example.com")
            user2.password_hash = "testpass"
            assert user2.is_allowed() is True

    def test_user_is_allowed_with_long_emails(self, client, app):
        """Test that long emails work correctly."""
        long_email = "a" * 50 + "@" + "b" * 50 + ".com"
        app.config["ALLOWED_EMAILS"] = [long_email]

        with client.application.app_context():
            user = User(email=long_email)
            user.password_hash = "testpass"

            assert user.is_allowed() is True

    def test_user_is_allowed_with_very_long_whitelist(self, client, app):
        """Test that very long whitelists work correctly."""
        app.config["ALLOWED_EMAILS"] = [f"user{i}@example.com" for i in range(1000)]

        with client.application.app_context():
            user = User(email="user500@example.com")
            user.password_hash = "testpass"

            assert user.is_allowed() is True

    def test_user_is_allowed_performance(self, client, app):
        """Test that email checking is performant."""
        app.config["ALLOWED_EMAILS"] = [f"user{i}@example.com" for i in range(100)]

        import time

        with client.application.app_context():
            user = User(email="user50@example.com")
            user.password_hash = "testpass"

            start_time = time.time()
            for _ in range(1000):
                user.is_allowed()
            end_time = time.time()

            # Should complete 1000 checks in less than 1 second
            assert (end_time - start_time) < 1.0

    def test_user_is_allowed_with_none_user(self, client, app):
        """Test that None user is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            # This should not raise an exception
            assert User.is_allowed(None) is False

    def test_user_is_allowed_with_invalid_user(self, client, app):
        """Test that invalid user objects are handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            # Create user with None email
            user = User(email=None)
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_empty_user_email(self, client, app):
        """Test that empty user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email="")
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_whitespace_user_email(self, client, app):
        """Test that whitespace user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email="   ")
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_numeric_user_email(self, client, app):
        """Test that numeric user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=123)
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_list_user_email(self, client, app):
        """Test that list user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=["user@example.com"])
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_dict_user_email(self, client, app):
        """Test that dict user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email={"email": "user@example.com"})
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_boolean_user_email(self, client, app):
        """Test that boolean user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=True)
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_function_user_email(self, client, app):
        """Test that function user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=lambda: "user@example.com")
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_class_user_email(self, client, app):
        """Test that class user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=User)
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_module_user_email(self, client, app):
        """Test that module user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=__import__("sys"))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_exception_user_email(self, client, app):
        """Test that exception user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=Exception("test"))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_generator_user_email(self, client, app):
        """Test that generator user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=(x for x in ["user@example.com"]))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_set_user_email(self, client, app):
        """Test that set user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email={"user@example.com"})
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_tuple_user_email(self, client, app):
        """Test that tuple user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=("user@example.com",))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_bytes_user_email(self, client, app):
        """Test that bytes user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=b"user@example.com")
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_bytearray_user_email(self, client, app):
        """Test that bytearray user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=bytearray(b"user@example.com"))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_memoryview_user_email(self, client, app):
        """Test that memoryview user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=memoryview(b"user@example.com"))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_frozenset_user_email(self, client, app):
        """Test that frozenset user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=frozenset(["user@example.com"]))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_range_user_email(self, client, app):
        """Test that range user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=range(10))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_slice_user_email(self, client, app):
        """Test that slice user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=slice(0, 10))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_property_user_email(self, client, app):
        """Test that property user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=property(lambda self: "user@example.com"))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_staticmethod_user_email(self, client, app):
        """Test that staticmethod user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=staticmethod(lambda: "user@example.com"))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_classmethod_user_email(self, client, app):
        """Test that classmethod user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=classmethod(lambda cls: "user@example.com"))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_abstractmethod_user_email(self, client, app):
        """Test that abstractmethod user email is handled gracefully."""
        from abc import abstractmethod

        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=abstractmethod(lambda: "user@example.com"))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_partial_user_email(self, client, app):
        """Test that partial user email is handled gracefully."""
        from functools import partial

        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=partial(lambda x: "user@example.com", "test"))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_wraps_user_email(self, client, app):
        """Test that wraps user email is handled gracefully."""
        from functools import wraps

        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=wraps(lambda: "user@example.com"))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_lru_cache_user_email(self, client, app):
        """Test that lru_cache user email is handled gracefully."""
        from functools import lru_cache

        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=lru_cache(lambda: "user@example.com"))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_singledispatch_user_email(self, client, app):
        """Test that singledispatch user email is handled gracefully."""
        from functools import singledispatch

        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=singledispatch(lambda: "user@example.com"))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_singledispatchmethod_user_email(self, client, app):
        """Test that singledispatchmethod user email is handled gracefully."""
        from functools import singledispatchmethod

        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=singledispatchmethod(lambda: "user@example.com"))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_cached_property_user_email(self, client, app):
        """Test that cached_property user email is handled gracefully."""
        from functools import cached_property

        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=cached_property(lambda: "user@example.com"))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_total_ordering_user_email(self, client, app):
        """Test that total_ordering user email is handled gracefully."""
        from functools import total_ordering

        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=total_ordering(lambda: "user@example.com"))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_reduce_user_email(self, client, app):
        """Test that reduce user email is handled gracefully."""
        from functools import reduce

        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=reduce(lambda x, y: "user@example.com", [1, 2, 3]))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_accumulate_user_email(self, client, app):
        """Test that accumulate user email is handled gracefully."""
        from itertools import accumulate

        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=accumulate([1, 2, 3]))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_chain_user_email(self, client, app):
        """Test that chain user email is handled gracefully."""
        from itertools import chain

        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=chain([1, 2, 3], [4, 5, 6]))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_combinations_user_email(self, client, app):
        """Test that combinations user email is handled gracefully."""
        from itertools import combinations

        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=combinations([1, 2, 3], 2))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_combinations_with_replacement_user_email(
        self, client, app
    ):
        """Test that combinations_with_replacement user email is handled gracefully."""
        from itertools import combinations_with_replacement

        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=combinations_with_replacement([1, 2, 3], 2))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_compress_user_email(self, client, app):
        """Test that compress user email is handled gracefully."""
        from itertools import compress

        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=compress([1, 2, 3], [True, False, True]))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_count_user_email(self, client, app):
        """Test that count user email is handled gracefully."""
        from itertools import count

        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=count())
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_cycle_user_email(self, client, app):
        """Test that cycle user email is handled gracefully."""
        from itertools import cycle

        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=cycle([1, 2, 3]))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_dropwhile_user_email(self, client, app):
        """Test that dropwhile user email is handled gracefully."""
        from itertools import dropwhile

        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=dropwhile(lambda x: x < 3, [1, 2, 3, 4, 5]))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_filterfalse_user_email(self, client, app):
        """Test that filterfalse user email is handled gracefully."""
        from itertools import filterfalse

        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=filterfalse(lambda x: x % 2, [1, 2, 3, 4, 5]))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_groupby_user_email(self, client, app):
        """Test that groupby user email is handled gracefully."""
        from itertools import groupby

        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=groupby([1, 2, 2, 3, 3, 3]))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_islice_user_email(self, client, app):
        """Test that islice user email is handled gracefully."""
        from itertools import islice

        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=islice([1, 2, 3, 4, 5], 3))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_permutations_user_email(self, client, app):
        """Test that permutations user email is handled gracefully."""
        from itertools import permutations

        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=permutations([1, 2, 3]))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_product_user_email(self, client, app):
        """Test that product user email is handled gracefully."""
        from itertools import product

        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=product([1, 2], [3, 4]))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_repeat_user_email(self, client, app):
        """Test that repeat user email is handled gracefully."""
        from itertools import repeat

        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=repeat(1, 3))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_starmap_user_email(self, client, app):
        """Test that starmap user email is handled gracefully."""
        from itertools import starmap

        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=starmap(pow, [(2, 3), (3, 4)]))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_takewhile_user_email(self, client, app):
        """Test that takewhile user email is handled gracefully."""
        from itertools import takewhile

        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=takewhile(lambda x: x < 3, [1, 2, 3, 4, 5]))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_tee_user_email(self, client, app):
        """Test that tee user email is handled gracefully."""
        from itertools import tee

        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=tee([1, 2, 3])[0])
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_zip_longest_user_email(self, client, app):
        """Test that zip_longest user email is handled gracefully."""
        from itertools import zip_longest

        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=zip_longest([1, 2], [3, 4, 5]))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_zip_user_email(self, client, app):
        """Test that zip user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=zip([1, 2], [3, 4]))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_map_user_email(self, client, app):
        """Test that map user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=map(lambda x: x * 2, [1, 2, 3]))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_filter_user_email(self, client, app):
        """Test that filter user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=filter(lambda x: x % 2, [1, 2, 3, 4, 5]))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_enumerate_user_email(self, client, app):
        """Test that enumerate user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=enumerate([1, 2, 3]))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_reversed_user_email(self, client, app):
        """Test that reversed user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=reversed([1, 2, 3]))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_sorted_user_email(self, client, app):
        """Test that sorted user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=sorted([3, 1, 2]))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_sum_user_email(self, client, app):
        """Test that sum user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=sum([1, 2, 3]))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_min_user_email(self, client, app):
        """Test that min user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=min([1, 2, 3]))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_max_user_email(self, client, app):
        """Test that max user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=max([1, 2, 3]))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_any_user_email(self, client, app):
        """Test that any user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=any([True, False, True]))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_all_user_email(self, client, app):
        """Test that all user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=all([True, True, True]))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_ascii_user_email(self, client, app):
        """Test that ascii user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=ascii("user@example.com"))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_bin_user_email(self, client, app):
        """Test that bin user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=bin(42))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_bool_user_email(self, client, app):
        """Test that bool user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=bool(1))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_bytearray_user_email(self, client, app):
        """Test that bytearray user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=bytearray(b"user@example.com"))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_bytes_user_email(self, client, app):
        """Test that bytes user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=bytes(b"user@example.com"))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_callable_user_email(self, client, app):
        """Test that callable user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=callable(lambda: "user@example.com"))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_chr_user_email(self, client, app):
        """Test that chr user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=chr(65))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_classmethod_user_email(self, client, app):
        """Test that classmethod user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=classmethod(lambda cls: "user@example.com"))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_compile_user_email(self, client, app):
        """Test that compile user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=compile("print('hello')", "<string>", "exec"))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_complex_user_email(self, client, app):
        """Test that complex user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=complex(1, 2))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_delattr_user_email(self, client, app):
        """Test that delattr user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=delattr)
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_dict_user_email(self, client, app):
        """Test that dict user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=dict())
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_dir_user_email(self, client, app):
        """Test that dir user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=dir())
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_divmod_user_email(self, client, app):
        """Test that divmod user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=divmod(10, 3))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_enumerate_user_email(self, client, app):
        """Test that enumerate user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=enumerate([1, 2, 3]))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_eval_user_email(self, client, app):
        """Test that eval user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=eval("1 + 1"))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_exec_user_email(self, client, app):
        """Test that exec user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=exec)
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_filter_user_email(self, client, app):
        """Test that filter user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=filter(lambda x: x % 2, [1, 2, 3, 4, 5]))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_float_user_email(self, client, app):
        """Test that float user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=float(3.14))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_format_user_email(self, client, app):
        """Test that format user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=format(42, "x"))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_frozenset_user_email(self, client, app):
        """Test that frozenset user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=frozenset([1, 2, 3]))
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_getattr_user_email(self, client, app):
        """Test that getattr user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=getattr)
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_globals_user_email(self, client, app):
        """Test that globals user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=globals())
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_hasattr_user_email(self, client, app):
        """Test that hasattr user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=hasattr)
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_hash_user_email(self, client, app):
        """Test that hash user email is handled gracefully."""
        app.config["ALLOWED_EMAILS"] = ["user@example.com"]

        with client.application.app_context():
            user = User(email=hash("user@example.com"))
            user.password_hash = "testpass"

            assert user.is_allowed() is False
