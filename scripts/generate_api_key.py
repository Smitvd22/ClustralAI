#!/usr/bin/env python3
# =============================================================================
# Generate Secure API Keys
# =============================================================================
"""
Generates cryptographically secure API keys for the application.

Usage:
    python scripts/generate_api_key.py
    python scripts/generate_api_key.py --count 3
"""
import argparse
import json
import secrets


def generate_api_key(length: int = 32) -> str:
    """Generate a URL-safe, cryptographically random API key."""
    return secrets.token_urlsafe(length)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate secure API keys for the Security-First RAG system."
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of API keys to generate (default: 1).",
    )
    parser.add_argument(
        "--length",
        type=int,
        default=32,
        help="Key length in bytes before base64 encoding (default: 32).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as a JSON array (for APP_API_KEYS env var).",
    )
    args = parser.parse_args()

    keys = [generate_api_key(args.length) for _ in range(args.count)]

    if args.json:
        print(json.dumps(keys))
    else:
        for i, key in enumerate(keys, 1):
            print(f"API Key {i}: {key}")

    print()
    print("Add to .env file:")
    print(f'APP_API_KEYS={json.dumps(keys)}')
    print()
    print("Or store in Azure Key Vault:")
    print(f"az keyvault secret set --vault-name <vault> --name app-api-keys --value '{json.dumps(keys)}'")


if __name__ == "__main__":
    main()
