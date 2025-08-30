#!/usr/bin/env python3
"""
Test runner script for the Flask application.
Run this script to execute all tests with coverage reporting.
"""

import subprocess
import sys
import os


def run_tests():
    """Run all tests with coverage reporting."""
    print("🧪 Running Flask Application Tests")
    print("=" * 50)

    # Ensure we're in the correct directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Install test requirements
    print("📦 Installing test dependencies...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", "test_requirements.txt"],
        check=True,
    )

    # Run tests with coverage
    test_commands = [
        # Run all tests with coverage
        [
            sys.executable,
            "-m",
            "pytest",
            "--cov=.",
            "--cov-report=html",
            "--cov-report=term-missing",
            "-v",
        ],
        # Run only unit tests
        # [sys.executable, "-m", "pytest", "-m", "unit", "-v"],
        # Run only integration tests
        # [sys.executable, "-m", "pytest", "-m", "integration", "-v"],
    ]

    for cmd in test_commands:
        print(f"\n🏃 Running: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True)
            print("✅ Tests passed!")
        except subprocess.CalledProcessError as e:
            print(f"❌ Tests failed with exit code {e.returncode}")
            return False

    print("\n📊 Coverage report generated in htmlcov/index.html")
    print("🎉 All tests completed successfully!")
    return True


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
