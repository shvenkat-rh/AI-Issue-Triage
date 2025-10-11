#!/usr/bin/env python3
"""Quick setup and run script for the Gemini Issue Analyzer."""

import os
import subprocess
import sys
from pathlib import Path


def check_requirements():
    """Check if all requirements are met."""
    print("Checking system requirements...")

    # Check Python version
    if sys.version_info < (3, 8):
        print("Python 3.8+ required")
        return False
    print(f"Python {sys.version_info.major}.{sys.version_info.minor}")

    # Check API key
    if not os.getenv("GEMINI_API_KEY"):
        print("GEMINI_API_KEY environment variable not found")
        print("   Please set it with: export GEMINI_API_KEY=your_key_here")
        return False
    print("Gemini API key found")

    # Check repomix file
    if not Path("repomix-output.txt").exists():
        print("repomix-output.txt not found")
        print("   Please ensure this file exists in the current directory")
        return False
    print("repomix-output.txt found")

    return True


def install_dependencies():
    """Install required dependencies."""
    print("Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install dependencies: {e}")
        return False


def run_streamlit():
    """Run the Streamlit application."""
    print("Starting Gemini Issue Analyzer...")
    print("The web interface will open in your browser")
    print("URL: http://localhost:8501")
    print("\n" + "=" * 50)
    print("Ready to analyze issues!")
    print("=" * 50)

    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"])
    except KeyboardInterrupt:
        print("\nApplication stopped by user")
    except Exception as e:
        print(f"Error running application: {e}")


def main():
    """Main function."""
    print("Gemini Issue Analyzer Setup")
    print("=" * 40)

    if not check_requirements():
        print("\nRequirements check failed. Please fix the issues above.")
        sys.exit(1)

    print("\nInstalling dependencies...")
    if not install_dependencies():
        print("\nFailed to install dependencies.")
        sys.exit(1)

    print("\nAll checks passed! Starting application...")
    run_streamlit()


if __name__ == "__main__":
    main()
