
import asyncio
import os
import sys
from typing import List

# Add the Backend directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from app.services.jira_integration_improved import JiraIntegration, JiraStatus, JiraIssueType

async def sync_specific_projects():
    """Sync stories from specific project keys"""
    print("🔄 Syncing stories from specific projects...")
    
    # Define your project keys here
    project_keys = ["TIS", "PROJ2", "PROJ3"]  # Replace with your actual project keys
    
    try:
        integration = JiraIntegration()
        
        # Sync stories from specific projects
        stats = await integration.sync_stories_from_multiple_projects(
            project_keys=project_keys,
            statuses=[JiraStatus.SELECTED_FOR_DEV, JiraStatus.IN_PROGRESS],
            issue_types=[JiraIssueType.STORY]
        )
        
        print(f"✅ Sync completed: {stats}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

async def sync_all_available_projects():
    """Sync stories from all projects the user has access to"""
    print("🔄 Syncing stories from all available projects...")
    
    try:
        integration = JiraIntegration()
        
        # Sync stories from all available projects
        stats = await integration.sync_all_available_projects(
            statuses=[JiraStatus.SELECTED_FOR_DEV, JiraStatus.IN_PROGRESS],
            issue_types=[JiraIssueType.STORY]
        )
        
        print(f"✅ Sync completed: {stats}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

async def sync_single_project():
    """Sync stories from a single project (original functionality)"""
    print("🔄 Syncing stories from a single project...")
    
    try:
        integration = JiraIntegration()
        
        # Sync stories from a single project
        stats = await integration.sync_stories(
            statuses=[JiraStatus.SELECTED_FOR_DEV, JiraStatus.IN_PROGRESS],
            issue_types=[JiraIssueType.STORY],
            project_keys=["PROJ1"]  # Replace with your project key
        )
        
        print(f"✅ Sync completed: {stats}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

async def discover_projects():
    """Discover and list all available projects"""
    print("🔍 Discovering available projects...")
    
    try:
        integration = JiraIntegration()
        
        # Get available projects
        projects = await integration.client.get_available_projects()
        
        if projects:
            print(f"✅ Found {len(projects)} projects:")
            for project in projects:
                print(f"  - {project['key']}: {project['name']}")
        else:
            print("⚠️ No projects found or user doesn't have access")
            
    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    """Main function with menu options"""
    print("🚀 Jira Multi-Project Story Sync")
    print("=" * 40)
    
    while True:
        print("\nChoose an option:")
        print("1. Discover available projects")
        print("2. Sync specific projects (edit script to set project keys)")
        print("3. Sync all available projects")
        print("4. Sync single project (edit script to set project key)")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == "1":
            await discover_projects()
        elif choice == "2":
            await sync_specific_projects()
        elif choice == "3":
            await sync_all_available_projects()
        elif choice == "4":
            await sync_single_project()
        elif choice == "5":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please try again.")

if __name__ == "__main__":
    asyncio.run(main()) 