"""Setup configuration for AI Issue Triage."""

from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="ai-issue-triage",
    version="1.0.0",
    author="shvenkat-rh",
    description="AI-powered issue analysis tool using Google's Gemini AI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/shvenkat-rh/AI-Issue-Triage",
    packages=find_packages(exclude=["tests", "tests.*", "cutlery", "cutlery.*", "ai_issue_triage", "ai_issue_triage.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Quality Assurance",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "ai-triage=cli.analyze:main",
            "ai-triage-duplicate=cli.duplicate_check:main",
            "ai-triage-cosine=cli.cosine_check:main",
            "ai-triage-pr=cli.pr_review:main",
        ],
    },
    include_package_data=True,
    package_data={
        "utils": ["*.txt", "*.md"],
    },
)
