import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
access_token = os.getenv("ACCESS_TOKEN")
api_domain = os.getenv("API_DOMAIN") or "https://www.zohoapis.com"

headers = {
    "Authorization": f"Zoho-oauthtoken {access_token}",
    "Content-Type": "application/json"
}

# Step 1: Get Account ID for "Ford"
def get_account_id(account_name):
    search_url = f"{api_domain}/crm/v2/Accounts/search"
    params = {
        "criteria": f"(Account_Name:equals:{account_name})"
    }
    response = requests.get(search_url, headers=headers, params=params)
    if response.status_code == 200:
        accounts = response.json().get("data", [])
        if accounts:
            return accounts[0]["id"]
    print("❌ Account not found:", response.text)
    return None

# Step 2: Find the Deal by Name and Account ID
def find_deal_by_name_and_account(deal_name, account_id):
    search_url = f"{api_domain}/crm/v2/Deals/search"
    params = {
        "criteria": f"(Deal_Name:equals:{deal_name})"
    }
    response = requests.get(search_url, headers=headers, params=params)
    if response.status_code == 200:
        deals = response.json().get("data", [])
        for deal in deals:
            related_account_id = deal.get("Account_Name", {}).get("id")
            if related_account_id == account_id:
                return deal
    print("❌ Deal not found:", response.text)
    return None

# Step 3: Update the Deal Stage
def update_deal_stage(deal_id, new_stage="Closed (Won)"):
    update_url = f"{api_domain}/crm/v2/Deals"
    payload = {
        "data": [
            {
                "id": deal_id,
                "Stage": new_stage
            }
        ]
    }
    response = requests.put(update_url, headers=headers, json=payload)
    if response.status_code == 200:
        print("✅ Deal stage updated to:", new_stage)
    else:
        print("❌ Failed to update deal:", response.status_code, response.text)

# ---- Main Logic ----
account_id = get_account_id("Ford")
if account_id:
    deal = find_deal_by_name_and_account("C# Developer", account_id)
    if deal:
        update_deal_stage(deal["id"], "Closed (Won)")
    else:
        print("❌ Deal not found under 'Ford'")
else:
    print("❌ 'Ford' account not found")
