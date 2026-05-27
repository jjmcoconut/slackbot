import threading
from slack_sdk import WebClient
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from config import SLACK_BOT_TOKEN, SLACK_APP_TOKEN
from slack_handlers import register_handlers
from scheduler import run_scheduler, job_check_task, paper_check_task

def main():
    print("Starting bot (jobs + papers)...")
    
    # Initialize App and Client
    app = App(token=SLACK_BOT_TOKEN)
    client = WebClient(token=SLACK_BOT_TOKEN)

    # Register slack command handlers
    register_handlers(app, client)

    # Run initial checks before starting the scheduler loop
    print("Running initial job & paper checks...")
    job_check_task(client)
    paper_check_task(client)

    # Start the scheduler in a background thread
    scheduler_thread = threading.Thread(target=run_scheduler, args=(client,), daemon=True)
    scheduler_thread.start()

    # Start Socket Mode
    print("Starting SocketModeHandler...")
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()

if __name__ == "__main__":
    main()
