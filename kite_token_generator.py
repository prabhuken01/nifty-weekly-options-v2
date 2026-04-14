#!/usr/bin/env python3
"""
Kite API Token Generator
========================
Fixes: "Kite rejected the session - Incorrect api_key or access_token"

This script:
1. Takes your Kite API credentials (api_key, api_secret, request_token)
2. Exchanges request_token for a valid access_token via KiteConnect
3. Validates the token by calling kite.profile()
4. Generates .streamlit/secrets.toml [kite] section
5. Optionally auto-saves to .streamlit/secrets.toml

Author: Claude (Anthropic)
Date: 2026-04-12
"""

import sys
import os
import json
from pathlib import Path
from getpass import getpass

# Try to import KiteConnect; install if missing
try:
    from kiteconnect import KiteConnect
except ImportError:
    print("\n❌ KiteConnect library not found.")
    print("Install it with: pip install kiteconnect")
    sys.exit(1)


def print_header():
    """Print welcome header."""
    print("\n" + "=" * 70)
    print("🔑 KITE API TOKEN GENERATOR")
    print("=" * 70)
    print("\nThis script will:")
    print("  1. Verify your Kite API credentials")
    print("  2. Exchange request_token for access_token")
    print("  3. Validate the token by fetching your profile")
    print("  4. Generate secrets.toml [kite] section")
    print("\n" + "=" * 70 + "\n")


def get_credentials():
    """Prompt user for Kite credentials with instructions."""
    print("📍 STEP 1: GATHER YOUR KITE CREDENTIALS\n")
    print("Where to find these:")
    print("  • API Key & Secret: https://developers.kite.trade/apps")
    print("    (Log in → Your App → Tokens section)")
    print("  • request_token: From Streamlit login URL after redirect")
    print("    (URL format: http://...?request_token=xxxxx&status=success)")
    print()

    credentials = {}

    # API Key
    while True:
        credentials['api_key'] = input("Enter your Kite API Key: ").strip()
        if len(credentials['api_key']) >= 10:
            break
        print("  ❌ API Key seems too short. Try again.\n")

    # API Secret (hidden input)
    while True:
        credentials['api_secret'] = getpass("Enter your Kite API Secret (hidden): ").strip()
        if len(credentials['api_secret']) >= 10:
            break
        print("  ❌ API Secret seems too short. Try again.\n")

    # Request Token
    while True:
        credentials['request_token'] = input("Enter your request_token (from login URL): ").strip()
        if len(credentials['request_token']) >= 10:
            break
        print("  ❌ request_token seems too short. Try again.\n")

    print("\n✅ Credentials received.\n")
    return credentials


def generate_access_token(api_key, api_secret, request_token):
    """
    Exchange request_token for access_token using KiteConnect.

    Returns:
        dict: {access_token, public_token, user_id}

    Raises:
        Exception: If token generation fails
    """
    print("📍 STEP 2: EXCHANGING REQUEST_TOKEN FOR ACCESS_TOKEN\n")

    try:
        # Create KiteConnect instance with api_key
        kite = KiteConnect(api_key=api_key)

        # Exchange request_token for access_token
        print(f"  • Attempting session generation...")
        session_data = kite.generate_session(
            request_token=request_token,
            api_secret=api_secret
        )

        print(f"  ✅ Session generated successfully!\n")
        return session_data, kite

    except Exception as e:
        print(f"  ❌ Failed to generate session: {str(e)}\n")
        print("Common causes:")
        print("  1. request_token is expired (valid for ~10 minutes)")
        print("  2. api_secret is incorrect")
        print("  3. api_key and api_secret don't match")
        print("  4. Network issue or Kite API is down")
        raise


def validate_token(kite, api_key, access_token):
    """
    Validate the access_token by calling kite.profile().

    Returns:
        dict: Profile data if valid

    Raises:
        Exception: If token is invalid
    """
    print("📍 STEP 3: VALIDATING TOKEN\n")

    try:
        # Set the access token
        kite.access_token = access_token

        # Fetch profile to verify token works
        print(f"  • Calling kite.profile() to verify token...")
        profile = kite.profile()

        print(f"  ✅ Token is valid!\n")
        print(f"User Details:")
        print(f"  • User ID: {profile.get('user_id', 'N/A')}")
        print(f"  • Name: {profile.get('user_name', 'N/A')}")
        print(f"  • Email: {profile.get('email', 'N/A')}")
        print(f"  • Broker: {profile.get('broker', 'N/A')}\n")

        return profile

    except Exception as e:
        print(f"  ❌ Token validation failed: {str(e)}\n")
        print("This token may be invalid or expired.")
        raise


def generate_secrets_section(api_key, access_token):
    """
    Generate the [kite] section for .streamlit/secrets.toml

    Returns:
        str: Formatted TOML section
    """
    print("📍 STEP 4: GENERATING SECRETS.TOML SECTION\n")

    toml_section = f'''[kite]
api_key = "{api_key}"
access_token = "{access_token}"
'''

    print("Add this to your .streamlit/secrets.toml file:\n")
    print("─" * 70)
    print(toml_section)
    print("─" * 70 + "\n")

    return toml_section


def save_to_secrets_file(toml_section, project_root=None):
    """
    Optionally save the [kite] section to .streamlit/secrets.toml

    Args:
        toml_section (str): The TOML section to save
        project_root (str): Root directory of the project (auto-detected if None)

    Returns:
        bool: True if saved, False if user skipped
    """
    print("📍 STEP 5: SAVE TO SECRETS.TOML (OPTIONAL)\n")

    # Auto-detect project root
    if project_root is None:
        project_root = Path.cwd()
    else:
        project_root = Path(project_root)

    secrets_path = project_root / ".streamlit" / "secrets.toml"

    print(f"Target file: {secrets_path}\n")

    # Check if file exists
    if secrets_path.exists():
        print(f"⚠️  File already exists.\n")
        print("Options:")
        print("  1. Append to existing file (RECOMMENDED if [kite] not present)")
        print("  2. Overwrite entire file (CAUTION: other secrets will be lost)")
        print("  3. Skip (I'll save manually)")
        choice = input("\nChoose [1/2/3]: ").strip()

        if choice == "1":
            # Check if [kite] already exists
            content = secrets_path.read_text()
            if "[kite]" in content:
                print("\n⚠️  [kite] section already exists in secrets.toml")
                overwrite_kite = input("Overwrite [kite] section? [y/n]: ").strip().lower()
                if overwrite_kite == "y":
                    # Remove old [kite] section and append new one
                    lines = content.split('\n')
                    new_lines = []
                    skip_kite = False
                    for line in lines:
                        if line.strip().startswith("[kite]"):
                            skip_kite = True
                            continue
                        if skip_kite and line.strip().startswith("["):
                            skip_kite = False
                        if not skip_kite:
                            new_lines.append(line)
                    content = '\n'.join(new_lines).rstrip() + '\n' + toml_section
                else:
                    print("\n⏭️  Skipping save.\n")
                    return False
            else:
                content = content.rstrip() + '\n\n' + toml_section

            secrets_path.write_text(content)
            print(f"✅ Appended to {secrets_path}\n")
            return True

        elif choice == "2":
            secrets_path.write_text(toml_section)
            print(f"✅ Overwrote {secrets_path}\n")
            return True

        else:
            print("\n⏭️  Skipping save.\n")
            return False

    else:
        # File doesn't exist; create it
        print(f"File does not exist. Create it?\n")
        create = input("Create .streamlit/secrets.toml? [y/n]: ").strip().lower()

        if create == "y":
            # Ensure directory exists
            secrets_path.parent.mkdir(parents=True, exist_ok=True)
            secrets_path.write_text(toml_section)
            print(f"✅ Created {secrets_path}\n")
            return True
        else:
            print("\n⏭️  Skipping save.\n")
            return False


def main():
    """Main workflow."""
    print_header()

    try:
        # Step 1: Get credentials
        credentials = get_credentials()

        # Step 2: Generate access_token
        session_data, kite = generate_access_token(
            api_key=credentials['api_key'],
            api_secret=credentials['api_secret'],
            request_token=credentials['request_token']
        )

        access_token = session_data['access_token']
        public_token = session_data.get('public_token', 'N/A')

        # Step 3: Validate token
        profile = validate_token(kite, credentials['api_key'], access_token)

        # Step 4: Generate secrets section
        toml_section = generate_secrets_section(credentials['api_key'], access_token)

        # Step 5: Optional save
        saved = save_to_secrets_file(toml_section)

        # Final summary
        print("=" * 70)
        print("✅ SUCCESS!")
        print("=" * 70 + "\n")
        print("Your new access_token:")
        print(f"  {access_token}\n")

        if saved:
            print("✅ Token has been saved to .streamlit/secrets.toml")
            print("\nNext steps:")
            print("  1. Restart your Streamlit app")
            print("  2. The app will now use the new access_token\n")
        else:
            print("⚠️  Token NOT saved to file.")
            print("   Manually add the [kite] section above to .streamlit/secrets.toml\n")
            print("Next steps:")
            print("  1. Copy the [kite] section from above")
            print("  2. Open .streamlit/secrets.toml in your editor")
            print("  3. Paste the [kite] section")
            print("  4. Save the file")
            print("  5. Restart your Streamlit app\n")

        print("=" * 70)

    except KeyboardInterrupt:
        print("\n\n⏹️  Cancelled by user.\n")
        sys.exit(0)

    except Exception as e:
        print("\n" + "=" * 70)
        print("❌ ERROR")
        print("=" * 70)
        print(f"\n{str(e)}\n")
        print("Troubleshooting:")
        print("  1. Verify request_token is fresh (valid for ~10 minutes)")
        print("  2. Double-check api_key and api_secret from dashboard")
        print("  3. Ensure your Kite app has Broker permission enabled")
        print("  4. Check your network connection")
        print("  5. Visit https://developers.kite.trade/apps for help\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
