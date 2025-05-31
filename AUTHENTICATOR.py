# Copyright (c) 2025 Shriyansh Singh Rathore
# Licensed under the MIT License

import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# Google OAuth scopes
SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]

# File to store user tokens
TOKEN_FILE = 'token.json'
# File to store user data
USER_DB_FILE = 'users.json'

def save_user_info(user_info):
    # Load existing users
    if os.path.exists(USER_DB_FILE):
        with open(USER_DB_FILE, 'r') as f:
            users = json.load(f)
    else:
        users = []

    # Avoid duplicates
    if not any(user['email'] == user_info['email'] for user in users):
        users.append(user_info)
        with open(USER_DB_FILE, 'w') as f:
            json.dump(users, f, indent=2)
        print(f"✅ User saved to {USER_DB_FILE}")
    else:
        print("ℹ️ User already exists in database.")

def clear_existing_tokens():
    """Clear existing token to force re-authentication with new scopes"""
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
        print("🔄 Cleared existing authentication token due to scope changes")

def main():
    creds = None
    
    # Check if token file exists and load credentials
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            print(f"⚠️ Error loading existing credentials: {e}")
            print("🔄 Clearing token and re-authenticating...")
            clear_existing_tokens()
            creds = None

    # Handle authentication
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("🔄 Refreshing expired credentials...")
                creds.refresh(Request())
            except Exception as e:
                print(f"⚠️ Failed to refresh credentials: {e}")
                print("🔄 Starting new authentication flow...")
                clear_existing_tokens()
                creds = None
        
        if not creds:
            print("🔐 Starting OAuth authentication flow...")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the new credentials
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
        print("💾 Authentication credentials saved")

    try:
        # Build OAuth2 service
        service = build('oauth2', 'v2', credentials=creds)
        user_info = service.userinfo().get().execute()

        # Display user info
        print("\n✅ Login successful!")
        print("👤 Name :", user_info.get('name'))
        print("📧 Email:", user_info.get('email'))
        print("🖼️ Picture URL:", user_info.get('picture'))

        # Save to local DB
        save_user_info({
            "name": user_info.get('name'),
            "email": user_info.get('email'),
            "picture": user_info.get('picture')
        })

    except Exception as e:
        print(f"❌ Error during authentication or API call: {e}")
        print("🔄 Try deleting token.json and running again")

if __name__ == '__main__':
    main()
