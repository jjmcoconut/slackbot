from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
import os

load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")

def verify():
    client = WebClient(token=SLACK_BOT_TOKEN)
    try:
        print("Attempting to list channels...")
        response = client.conversations_list(limit=5)
        if response['ok']:
            print("SUCCESS: Token has 'channels:read' scope.")
            channels = response['channels']
            print(f"Found {len(channels)} channels.")
            for ch in channels:
                print(f"- {ch['name']} (ID: {ch['id']})")
        else:
            print(f"FAILED: {response['error']}")
    except SlackApiError as e:
        print(f"ERROR: {e.response['error']}")

if __name__ == "__main__":
    verify()
