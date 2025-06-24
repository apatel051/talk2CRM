import requests
import os
from dotenv import load_dotenv

# Load variables from .env file
if not load_dotenv():
    print("⚠️  .env file not found or failed to load")

# Retrieve environment variables
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
authorization_code = os.getenv("AUTHORIZATION_CODE")
redirect_uri = os.getenv("REDIRECT_URI")
accounts_url = os.getenv("ACCOUNTS_URL")
grant_type = os.getenv("GRANT_TYPE")


# Prepare data for token request
data = {
    "grant_type": grant_type,
    "client_id": client_id,
    "client_secret": client_secret,
    "code": authorization_code,
    "redirect_uri": redirect_uri
}

# Uncomment the following lines to make the POST request
response = requests.post(accounts_url, data=data)

# Process the response
if response.status_code == 200:
    tokens = response.json()
    print("✅ Access Token:", tokens.get("access_token"))
    print("🔁 Refresh Token:", tokens.get("refresh_token"))
    print("🕒 Expires In:", tokens.get("expires_in"), "seconds")
else:
    print("❌ Failed to retrieve access token")
    print("Status Code:", response.status_code)
    print("Response:", response.text)
