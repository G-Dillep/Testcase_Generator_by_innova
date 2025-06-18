import os
import time
from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from app.datapipeline.embedding_generator import generate_embeddings
from app.LLM.Test_case_generator import generate_test_cases_for_all_stories

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NEXT_RELOAD_FILE = os.path.join(BASE_DIR, 'next_reload.txt')

def write_next_reload_time(next_time: datetime):
    print(f"[Scheduler] Writing next reload time: {next_time.isoformat()} to {NEXT_RELOAD_FILE}")
    with open(NEXT_RELOAD_FILE, 'w') as f:
        f.write(next_time.isoformat())

def scheduled_job():
    print("🔄 [Scheduler] Running data pipeline...")
    generate_embeddings()
    
    # Add a small delay to ensure LanceDB is properly updated
    print("⏳ [Scheduler] Waiting 2 seconds for LanceDB to update...")
    time.sleep(10)
    
    print("🔄 [Scheduler] Generating test cases...")
    generate_test_cases_for_all_stories()
    
    # Calculate and store next reload time
    next_time = datetime.now() + timedelta(minutes=5)
    write_next_reload_time(next_time)

if __name__ == '__main__':
    # Run once at startup
    scheduled_job()

    # Set up scheduler to run every 5 minutes
    scheduler = BlockingScheduler()
    scheduler.add_job(scheduled_job, 'interval', minutes=5)
    scheduler.start() 