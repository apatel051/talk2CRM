import asyncio
import random
from openai import OpenAI
import numpy as np
import os
from dotenv import load_dotenv
import requests

from agents import Agent, function_tool
from agents.extensions.handoff_prompt import prompt_with_handoff_instructions
from agents.voice import (
    AudioInput,
    SingleAgentVoiceWorkflow,
    SingleAgentWorkflowCallbacks,
    VoicePipeline,
)

from util import AudioPlayer, record_audio

load_dotenv()

client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
)

# Load environment variables
access_token = os.getenv("ACCESS_TOKEN")
api_domain = os.getenv("API_DOMAIN") or "https://www.zohoapis.com"
openai_api_key = os.getenv("OPENAI_API_KEY")

headers = {
    "Authorization": f"Zoho-oauthtoken {access_token}",
    "Content-Type": "application/json"
}


# Step 1: Get Account ID for the given account name
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

# Function to process the deal stage
@function_tool
def process_deal_stage(account_name: str, deal_name: str, deal_stage: str):
    print(f"Processing deal stage update for '{deal_name}' under account '{account_name}' to '{deal_stage}'")
    account_id = get_account_id(account_name)
    if account_id:
        deal = find_deal_by_name_and_account(deal_name, account_id)
        if deal:
            update_deal_stage(deal["id"], deal_stage)
        else:
            print(f"❌ Deal '{deal_name}' not found under '{account_name}'")
    else:
        print(f"❌ Account '{account_name}' not found")



@function_tool
def get_weather(city: str) -> str:
    """Get the weather for a given city."""
    print(f"[debug] get_weather called with city: {city}")
    choices = ["sunny", "cloudy", "rainy", "snowy"]
    return f"The weather in {city} is {random.choice(choices)}."



crm_agent = Agent(
    name="CRM agent",
    handoff_description="Specialist agent for creating, reading, updating and deleting accounts and deals in Zoho CRM",
    instructions="You are integrated with a CRM system. Retrieve the account name, deal name and deal stage from the conversation and pass it to the tool.",
    tools=[process_deal_stage],
)

agent = Agent(
    name="Assistant",
    instructions=prompt_with_handoff_instructions(
        "You're speaking to a human, so be polite and concise. If the user talks about updating a sales deal, handoff to the crm agent.",
    ),
    model="gpt-4o-mini",
    handoffs=[crm_agent],
    tools=[get_weather],
)


class WorkflowCallbacks(SingleAgentWorkflowCallbacks):
    def on_run(self, workflow: SingleAgentVoiceWorkflow, transcription: str) -> None:
        print(f"[debug] on_run called with transcription: {transcription}")


async def main():
    pipeline = VoicePipeline(
        workflow=SingleAgentVoiceWorkflow(agent, callbacks=WorkflowCallbacks())
    )

    audio_input = AudioInput(buffer=record_audio())

    result = await pipeline.run(audio_input)

    with AudioPlayer() as player:
        async for event in result.stream():
            if event.type == "voice_stream_event_audio":
                player.add_audio(event.data)
                print("Received audio")
            elif event.type == "voice_stream_event_lifecycle":
                print(f"Received lifecycle event: {event.event}")

        # Add 1 second of silence to the end of the stream to avoid cutting off the last audio.
        player.add_audio(np.zeros(24000 * 1, dtype=np.int16))


if __name__ == "__main__":
    asyncio.run(main())
