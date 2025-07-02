import os
import time
import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from app.datapipeline.embedding_generator import generate_embeddings
from app.LLM.Test_case_generator import generate_test_cases_for_all_stories

# Import Jira integration
try:
    from app.services.jira_integration_improved import JiraIntegration, JiraStatus, JiraIssueType
    JIRA_AVAILABLE = True
except ImportError:
    JIRA_AVAILABLE = False
    print("⚠️ [Scheduler] Jira integration not available")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NEXT_RELOAD_FILE = os.path.join(BASE_DIR, 'next_reload.txt')

def get_jira_config():
    """Get Jira configuration from environment variables - read fresh each time"""
    jira_sync_enabled = os.getenv('JIRA_SYNC_ENABLED', 'false').lower() == 'true'
    jira_project_keys = os.getenv('JIRA_PROJECT_KEYS', '').split(',') if os.getenv('JIRA_PROJECT_KEYS') else []
    jira_sync_all_projects = os.getenv('JIRA_SYNC_ALL_PROJECTS', 'false').lower() == 'true'
    
    # Clean up project keys (remove empty strings)
    jira_project_keys = [key.strip() for key in jira_project_keys if key.strip()]
    
    return {
        'sync_enabled': jira_sync_enabled,
        'project_keys': jira_project_keys,
        'sync_all_projects': jira_sync_all_projects
    }

def write_next_reload_time(next_time: datetime):
    print(f"[Scheduler] Writing next reload time: {next_time.isoformat()} to {NEXT_RELOAD_FILE}")
    try:
        with open(NEXT_RELOAD_FILE, 'w') as f:
            f.write(next_time.isoformat())
        print(f"[Scheduler] ✅ Successfully wrote next reload time")
    except Exception as e:
        print(f"[Scheduler] ❌ Error writing reload time: {e}")

def initialize_reload_time():
    """Initialize the reload time file on startup"""
    next_time = datetime.now() + timedelta(minutes=5)
    write_next_reload_time(next_time)
    print(f"[Scheduler] 🕐 Initialized next reload time: {next_time.strftime('%Y-%m-%d %H:%M:%S')}")

async def sync_jira_stories():
    """Sync stories from Jira projects - reads config fresh each time"""
    if not JIRA_AVAILABLE:
        print("📋 [Scheduler] Jira integration not available")
        return
    
    # Read Jira configuration fresh each time
    jira_config = get_jira_config()
    
    if not jira_config['sync_enabled']:
        print("📋 [Scheduler] Jira sync is disabled")
        return
    
    print("🔄 [Scheduler] Step 0: Syncing stories from Jira...")
    print(f"📋 [Scheduler] Current Jira config: {jira_config}")
    
    try:
        integration = JiraIntegration()
        
        if jira_config['sync_all_projects']:
            print("🔄 [Scheduler] Syncing from all available projects...")
            stats = await integration.sync_all_available_projects(
                statuses=[JiraStatus.SELECTED_FOR_DEV, JiraStatus.IN_PROGRESS],
                issue_types=[JiraIssueType.STORY]
            )
        elif jira_config['project_keys']:
            print(f"🔄 [Scheduler] Syncing from specific projects: {jira_config['project_keys']}")
            stats = await integration.sync_stories_from_multiple_projects(
                project_keys=jira_config['project_keys'],
                statuses=[JiraStatus.SELECTED_FOR_DEV, JiraStatus.IN_PROGRESS],
                issue_types=[JiraIssueType.STORY]
            )
        else:
            print("⚠️ [Scheduler] No Jira projects configured for sync")
            return
        
        print(f"✅ [Scheduler] Jira sync completed: {stats}")
        
    except Exception as e:
        print(f"❌ [Scheduler] Error syncing from Jira: {e}")

def scheduled_job():
    print("🔄 [Scheduler] Starting data pipeline...")
    print(f"⏰ [Scheduler] Job started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Step 0: Sync from Jira (if enabled) - config read fresh each time
        if JIRA_AVAILABLE:
            jira_config = get_jira_config()
            if jira_config['sync_enabled']:
                asyncio.run(sync_jira_stories())
                # Add a delay after Jira sync
                print("⏳ [Scheduler] Waiting 5 seconds after Jira sync...")
                time.sleep(5)
        
        # Step 1: Process project folders and generate embeddings
        print("📁 [Scheduler] Step 1: Processing project folders and generating embeddings...")
        generate_embeddings()
        
        # Add a delay to ensure LanceDB is properly updated
        print("⏳ [Scheduler] Waiting 2 seconds for LanceDB to update...")
        time.sleep(2)
        
        # Step 2: Generate test cases for all stories
        print("🧠 [Scheduler] Step 2: Generating test cases for all stories...")
        generate_test_cases_for_all_stories()
        
        # Calculate and store next reload time
        next_time = datetime.now() + timedelta(minutes=5)
        write_next_reload_time(next_time)
        
        print(f"✅ [Scheduler] Pipeline completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏰ [Scheduler] Next run scheduled for: {next_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"❌ [Scheduler] Error in scheduled job: {e}")
        # Still update the reload time even if there's an error
        next_time = datetime.now() + timedelta(minutes=5)
        write_next_reload_time(next_time)

def display_configuration():
    """Display current configuration"""
    print("📋 [Scheduler] Configuration:")
    print(f"   JIRA_AVAILABLE: {JIRA_AVAILABLE}")
    
    # Read config fresh for display
    jira_config = get_jira_config()
    print(f"   JIRA_SYNC_ENABLED: {jira_config['sync_enabled']}")
    if jira_config['sync_enabled']:
        if jira_config['sync_all_projects']:
            print("   JIRA_SYNC_ALL_PROJECTS: true (will sync all available projects)")
        elif jira_config['project_keys']:
            print(f"   JIRA_PROJECT_KEYS: {jira_config['project_keys']}")
        else:
            print("   ⚠️ No specific projects configured")
    print("")

if __name__ == '__main__':
    print("🚀 [Scheduler] Starting Enhanced Test Case Generator Scheduler...")
    
    # Display configuration
    display_configuration()
    
    # Initialize reload time file on startup
    initialize_reload_time()
    
    # Run once at startup
    print("🔄 [Scheduler] Running initial pipeline...")
    scheduled_job()

    # Set up scheduler to run every 5 minutes
    print("⏰ [Scheduler] Setting up scheduled job to run every 5 minutes...")
    scheduler = BlockingScheduler()
    scheduler.add_job(scheduled_job, 'interval', minutes=5)
    
    print("✅ [Scheduler] Scheduler started. Press Ctrl+C to stop.")
    print(f"📁 [Scheduler] Reload time file: {NEXT_RELOAD_FILE}")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("🛑 [Scheduler] Scheduler stopped by user.")
        scheduler.shutdown() 