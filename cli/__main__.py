"""Entry point for running CLI as a module with subcommand selection."""

import sys

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m cli <subcommand>")
        print("")
        print("Available subcommands:")
        print("  analyze          - Analyze issues with AI")
        print("  duplicate_check  - Check for duplicate issues (AI-powered)")
        print("  cosine_check     - Check for duplicate issues (cosine similarity)")
        print("  pr_review        - Review pull requests with AI")
        print("")
        print("Examples:")
        print("  python -m cli.analyze --title 'Bug' --description 'Details'")
        print("  python -m cli.duplicate_check --title '...' --issues issues.json")
        print("  python -m cli.cosine_check --title '...' --issues issues.json")
        print("  python -m cli.pr_review --pr-file pr_data.json")
        sys.exit(1)

    # Default to analyze if no subcommand given
    print("Please specify a subcommand: analyze, duplicate_check, cosine_check, or pr_review")
    sys.exit(1)
