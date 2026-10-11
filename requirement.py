#!/usr/bin/env python3
"""
Dependency installer and verification script.
Installs required packages and sets up Playwright Firefox browser binary.
"""

import subprocess
import sys

PACKAGES = [
    "requests>=2.31.0",
    "playwright>=1.40.0",
]


def install():
    print("=== Installing Python Dependencies ===")
    subprocess.check_call([sys.executable, "-m", "pip", "install", *PACKAGES])

    print("\n=== Installing Playwright Firefox Browser ===")
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "firefox"])

    print("\n=== Verifying Installation ===")
    try:
        import requests
        from playwright.sync_api import sync_playwright
        import importlib.metadata
        print(f"✓ requests: {requests.__version__}")
        print(f"✓ playwright: {importlib.metadata.version('playwright')}")
        print("\nAll dependencies installed and verified successfully!")
    except ImportError as e:
        print(f"Verification error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    install()
