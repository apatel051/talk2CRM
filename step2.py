import requests
import os
from dotenv import load_dotenv

# Load access token and domain from .env
load_dotenv()
access_token = os.getenv("ACCESS_TOKEN")  # Save this token in your .env
api_domain = os.getenv("API_DOMAIN") 

headers = {
    "Authorization": f"Zoho-oauthtoken {access_token}"
}

# Step 1: Get Account ID for "Ford"
def get_account_id(account_name):
    search_url = f"{api_domain}/crm/v2/Accounts/search"
    params = {
        "criteria": f"(Account_Name:equals:{account_name})"
    }
    response = requests.get(search_url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        accounts = data.get("data", [])
        if accounts:
            return accounts[0]["id"]
    print("❌ Account not found:", response.text)
    return None

# Step 2: Search Deals under that Account and filter for "C# Developer"
def find_deal_by_name_and_account(deal_name, account_id):
    search_url = f"{api_domain}/crm/v2/Deals/search"
    params = {
        "criteria": f"(Deal_Name:equals:{deal_name})"
    }
    response = requests.get(search_url, headers=headers, params=params)
    if response.status_code == 200:
        deals = response.json().get("data", [])
        for deal in deals:
            related_account = deal.get("Account_Name", {}).get("id")
            if related_account == account_id:
                return deal
    print("❌ Deal not found:", response.text)
    return None

# Run search
account_id = get_account_id("Ford")
if account_id:
    deal = find_deal_by_name_and_account("C# Developer", account_id)
    if deal:
        print("✅ Deal Found:")
        print("Deal Name:", deal.get("Deal_Name"))
        print("Amount:", deal.get("Amount"))
        print("Stage:", deal.get("Stage"))
        print("Account Name:", deal.get("Account_Name", {}).get("name"))
    else:
        print("❌ Deal not found under 'Ford'")
else:
    print("❌ 'Ford' account not found")
