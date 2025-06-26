import os
import sys
import logging
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import time

# Add the Backend directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, "../.."))
sys.path.insert(0, backend_dir)

import requests
import pandas as pd
import lancedb
from app.config import Config
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class JiraIssueType(Enum):
    STORY = "Story"
    EPIC = "Epic"
    BUG = "Bug"
    TASK = "Task"

class JiraStatus(Enum):
    SELECTED_FOR_DEV = "Selected for Development"
    IN_PROGRESS = "In Progress"
    DONE = "Done"
    TO_DO = "To Do"

@dataclass
class JiraConfig:
    """Configuration class for Jira integration"""
    base_url: str
    email: str
    api_token: str
    project_key: str = ""  # Optional for backward compatibility
    max_results: int = 100
    batch_size: int = 50
    rate_limit_delay: float = 1.0
    retry_attempts: int = 3
    retry_backoff_factor: float = 2.0
    
    @classmethod
    def from_env(cls) -> 'JiraConfig':
        """Create config from environment variables"""
        return cls(
            base_url=os.getenv('JIRA_BASE_URL', ''),
            email=os.getenv('JIRA_EMAIL', ''),
            api_token=os.getenv('JIRA_API_TOKEN', ''),
            project_key=os.getenv('JIRA_PROJECT_KEY', ''),  # Optional
            max_results=int(os.getenv('JIRA_MAX_RESULTS', '100')),
            batch_size=int(os.getenv('JIRA_BATCH_SIZE', '50')),
            rate_limit_delay=float(os.getenv('JIRA_RATE_LIMIT_DELAY', '1.0')),
            retry_attempts=int(os.getenv('JIRA_RETRY_ATTEMPTS', '3')),
            retry_backoff_factor=float(os.getenv('JIRA_RETRY_BACKOFF_FACTOR', '2.0'))
        )
    
    def validate(self) -> bool:
        """Validate configuration"""
        required_fields = ['base_url', 'email', 'api_token']
        for field in required_fields:
            if not getattr(self, field):
                logger.error(f"Missing required Jira configuration: {field}")
                return False
        return True

class JiraRateLimiter:
    """Rate limiter for Jira API calls"""
    
    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.last_request = 0
    
    async def wait(self):
        """Wait if necessary to respect rate limits"""
        now = time.time()
        time_since_last = now - self.last_request
        if time_since_last < self.delay:
            await asyncio.sleep(self.delay - time_since_last)
        self.last_request = time.time()

class JiraClient:
    """Enhanced Jira API client with retry logic and rate limiting"""
    
    def __init__(self, config: JiraConfig):
        self.config = config
        self.rate_limiter = JiraRateLimiter(config.rate_limit_delay)
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create session with retry logic"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=self.config.retry_attempts,
            backoff_factor=self.config.retry_backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _get_auth(self) -> tuple:
        """Get authentication credentials"""
        return (self.config.email, self.config.api_token)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "TestCaseGenerator/1.0"
        }
    
    async def test_connection(self) -> bool:
        """Test Jira connection and credentials"""
        try:
            url = f"{self.config.base_url}/rest/api/2/myself"
            response = self.session.get(
                url, 
                auth=self._get_auth(), 
                headers=self._get_headers()
            )
            response.raise_for_status()
            user_data = response.json()
            logger.info(f"✅ Connected to Jira as: {user_data.get('displayName', 'Unknown')}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to Jira: {e}")
            return False
    
    async def get_issues(self, jql: str, start_at: int = 0) -> Optional[Dict[str, Any]]:
        """Get issues from Jira with pagination"""
        try:
            await self.rate_limiter.wait()
            
            url = f"{self.config.base_url}/rest/api/2/search"
            params = {
                "jql": jql,
                "maxResults": self.config.batch_size,
                "startAt": start_at,
                "fields": "summary,description,status,priority,created,updated,reporter,creator,project,issuetype,assignee,labels,components"
            }
            
            # Log the request for debugging
            logger.debug(f"🔍 Making request to: {url}")
            logger.debug(f"🔍 Parameters: {params}")
            
            response = self.session.get(
                url,
                auth=self._get_auth(),
                headers=self._get_headers(),
                params=params
            )
            
            # Log response details for debugging
            logger.debug(f"🔍 Response status: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"🔍 Response content: {response.text}")
            
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"❌ Response content: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            return None

    async def test_simple_query(self) -> bool:
        """Test a simple JQL query to verify API access"""
        try:
            await self.rate_limiter.wait()
            
            url = f"{self.config.base_url}/rest/api/2/search"
            params = {
                "jql": 'status = "Selected for Development" AND issuetype = Story',
                "maxResults": 1,
                "fields": "summary"
            }
            
            logger.info(f"🔍 Testing simple query: {params['jql']}")
            
            response = self.session.get(
                url,
                auth=self._get_auth(),
                headers=self._get_headers(),
                params=params
            )
            
            logger.info(f"🔍 Test response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                total = data.get("total", 0)
                logger.info(f"✅ Simple query successful. Found {total} issues")
                return True
            else:
                logger.error(f"❌ Test query failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Test query error: {e}")
            return False

    async def get_available_projects(self) -> List[Dict[str, Any]]:
        """Get list of available projects in Jira"""
        try:
            await self.rate_limiter.wait()
            
            url = f"{self.config.base_url}/rest/api/2/project"
            response = self.session.get(
                url,
                auth=self._get_auth(),
                headers=self._get_headers()
            )
            response.raise_for_status()
            
            projects = response.json()
            logger.info(f"✅ Found {len(projects)} projects in Jira")
            
            # Log project details
            for project in projects:
                logger.info(f"📋 Project: {project.get('key')} - {project.get('name')}")
            
            return projects
            
        except Exception as e:
            logger.error(f"❌ Failed to get projects: {e}")
            return []

class JiraDataProcessor:
    """Process and transform Jira data"""
    
    @staticmethod
    def extract_issue_data(issue: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant data from Jira issue with proper null handling"""
        fields = issue.get("fields", {}) or {}
        
        # Helper function to safely get nested values
        def safe_get(obj, key, default=""):
            if obj is None:
                return default
            return obj.get(key, default)
        
        def safe_get_name(obj, default=""):
            if obj is None:
                return default
            return obj.get("name", default)
        
        def safe_get_display_name(obj, default=""):
            if obj is None:
                return default
            return obj.get("displayName", default)
        
        return {
            "key": issue.get("key", ""),
            "summary": safe_get(fields, "summary", ""),
            "status": safe_get_name(safe_get(fields, "status"), ""),
            "priority": safe_get_name(safe_get(fields, "priority"), ""),
            "created": safe_get(fields, "created"),
            "updated": safe_get(fields, "updated"),
            "description": safe_get(fields, "description", ""),
            "reporter": safe_get_display_name(safe_get(fields, "reporter"), ""),
            "creator": safe_get_display_name(safe_get(fields, "creator"), ""),
            "project": safe_get_name(safe_get(fields, "project"), ""),
            "issuetype": safe_get_name(safe_get(fields, "issuetype"), ""),
            "assignee": safe_get_display_name(safe_get(fields, "assignee"), ""),
            "labels": safe_get(fields, "labels", []),
            "components": [safe_get_name(comp, "") for comp in safe_get(fields, "components", []) if comp is not None],
            "jira_url": f"{os.getenv('JIRA_BASE_URL', '')}/browse/{issue.get('key', '')}"
        }
    
    @staticmethod
    def validate_issue_data(data: Dict[str, Any]) -> bool:
        """Validate issue data before processing"""
        required_fields = ["key", "summary"]
        for field in required_fields:
            if not data.get(field):
                logger.warning(f"Missing required field: {field}")
                return False
        return True
    
    @staticmethod
    def prepare_content(data: Dict[str, Any]) -> str:
        """Prepare content for embedding"""
        content_parts = []
        
        if data.get("summary"):
            content_parts.append(data["summary"])
        
        if data.get("description"):
            content_parts.append(data["description"])
        
        if data.get("labels"):
            content_parts.append(f"Labels: {', '.join(data['labels'])}")
        
        if data.get("components"):
            content_parts.append(f"Components: {', '.join(data['components'])}")
        
        return "\n\n".join(content_parts)

class JiraIntegration:
    """Main Jira integration class"""
    
    def __init__(self):
        self.config = JiraConfig.from_env()
        if not self.config.validate():
            raise ValueError("Invalid Jira configuration")
        
        self.client = JiraClient(self.config)
        self.processor = JiraDataProcessor()
        
        # Connect to LanceDB
        self.db = lancedb.connect(Config.LANCE_DB_PATH)
        try:
            self.table = self.db.open_table(Config.TABLE_NAME_LANCE)
        except Exception as e:
            logger.error(f"❌ Error opening LanceDB table: {e}")
            raise
    
    async def sync_stories(self, statuses: List[JiraStatus] = None, issue_types: List[JiraIssueType] = None, project_keys: List[str] = None) -> Dict[str, int]:
        """Sync stories from Jira to LanceDB"""
        
        # Test connection first
        if not await self.client.test_connection():
            return {"processed": 0, "success": 0, "failed": 0, "skipped": 0}
        
        # Build JQL query
        jql = self._build_jql_query(statuses, issue_types, project_keys)
        logger.info(f"🔍 Using JQL query: {jql}")
        
        # Get existing story IDs
        existing_ids = self._get_existing_story_ids()
        logger.info(f"🔍 Found {len(existing_ids)} existing story IDs")
        
        # Process issues
        stats = {"processed": 0, "success": 0, "failed": 0, "skipped": 0}
        start_at = 0
        
        while True:
            logger.debug(f"🔍 Fetching issues starting at: {start_at}")
            issues_data = await self.client.get_issues(jql, start_at)
            if not issues_data:
                logger.warning("⚠️ No issues data returned from Jira API")
                break
            
            issues = issues_data.get("issues", [])
            if not issues:
                logger.info("✅ No more issues to process")
                break
            
            logger.info(f"🔍 Processing {len(issues)} issues (start_at: {start_at})")
            
            for issue in issues:
                stats["processed"] += 1
                result = await self._process_issue(issue, existing_ids)
                stats[result] += 1
            
            # Check if we've processed all issues
            total = issues_data.get("total", 0)
            start_at += len(issues)
            logger.info(f"🔍 Processed {start_at}/{total} issues")
            if start_at >= total:
                break
        
        logger.info(f"📊 Sync completed: {stats}")
        return stats

    async def sync_stories_from_multiple_projects(self, project_keys: List[str], statuses: List[JiraStatus] = None, issue_types: List[JiraIssueType] = None) -> Dict[str, int]:
        """Sync stories from multiple Jira projects"""
        
        if not project_keys:
            logger.warning("⚠️ No project keys provided")
            return {"processed": 0, "success": 0, "failed": 0, "skipped": 0}
        
        logger.info(f"🔄 Starting sync for {len(project_keys)} projects: {project_keys}")
        
        total_stats = {"processed": 0, "success": 0, "failed": 0, "skipped": 0}
        
        for project_key in project_keys:
            logger.info(f"🔄 Processing project: {project_key}")
            try:
                # Test connection for each project
                logger.debug(f"🔍 Testing connection for project: {project_key}")
                if not await self.client.test_connection():
                    logger.error(f"❌ Connection test failed for project: {project_key}")
                    total_stats["failed"] += 1
                    continue
                
                project_stats = await self.sync_stories(statuses, issue_types, [project_key])
                
                # Aggregate stats
                for key in total_stats:
                    total_stats[key] += project_stats.get(key, 0)
                    
                logger.info(f"✅ Completed project {project_key}: {project_stats}")
                
                # Add a small delay between projects to avoid rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Error processing project {project_key}: {e}")
                total_stats["failed"] += 1
        
        logger.info(f"📊 Multi-project sync completed: {total_stats}")
        return total_stats

    async def sync_all_available_projects(self, statuses: List[JiraStatus] = None, issue_types: List[JiraIssueType] = None) -> Dict[str, int]:
        """Sync stories from all available projects the user has access to"""
        
        logger.info("🔄 Discovering available projects...")
        
        try:
            projects = await self.client.get_available_projects()
            if not projects:
                logger.warning("⚠️ No projects found or user doesn't have access")
                return {"processed": 0, "success": 0, "failed": 0, "skipped": 0}
            
            project_keys = [project['key'] for project in projects]
            logger.info(f"🔄 Found {len(project_keys)} projects: {project_keys}")
            
            return await self.sync_stories_from_multiple_projects(project_keys, statuses, issue_types)
            
        except Exception as e:
            logger.error(f"❌ Error discovering projects: {e}")
            return {"processed": 0, "success": 0, "failed": 0, "skipped": 0}
    
    def _build_jql_query(self, statuses: List[JiraStatus] = None, issue_types: List[JiraIssueType] = None, project_keys: List[str] = None) -> str:
        """Build JQL query based on filters - now supports multiple projects"""
        conditions = []
        
        # Project filter (NEW - supports multiple projects)
        if project_keys:
            logger.debug(f"🔍 Building JQL for projects: {project_keys}")
            project_conditions = [f'project = "{key}"' for key in project_keys]
            if len(project_conditions) == 1:
                conditions.append(project_conditions[0])
                logger.debug(f"🔍 Single project condition: {project_conditions[0]}")
            else:
                combined_condition = f'({" OR ".join(project_conditions)})'
                conditions.append(combined_condition)
                logger.debug(f"🔍 Multiple project condition: {combined_condition}")
        else:
            logger.warning("⚠️ No project keys provided for JQL query")
        
        # Status filter (like the original working version)
        if statuses:
            status_names = [f'"{status.value}"' for status in statuses]
            status_condition = f'status IN ({", ".join(status_names)})'
            conditions.append(status_condition)
            logger.debug(f"🔍 Status condition: {status_condition}")
        else:
            # Default to the original working query
            conditions.append('status = "Selected for Development"')
            logger.debug('🔍 Default status condition: status = "Selected for Development"')
        
        # Issue type filter
        if issue_types:
            type_names = [f'"{issue_type.value}"' for issue_type in issue_types]
            type_condition = f'issuetype IN ({", ".join(type_names)})'
            conditions.append(type_condition)
            logger.debug(f"🔍 Issue type condition: {type_condition}")
        else:
            # Default to the original working query
            conditions.append('issuetype = Story')
            logger.debug('🔍 Default issue type condition: issuetype = Story')
        
        query = " AND ".join(conditions)
        logger.info(f"🔍 Built JQL query: {query}")
        return query
    
    def _get_existing_story_ids(self) -> set:
        """Get existing story IDs from LanceDB"""
        try:
            df = self.table.to_pandas()
            return set(df['storyID'].tolist())
        except Exception as e:
            logger.error(f"❌ Error getting existing story IDs: {e}")
            return set()
    
    async def _process_issue(self, issue: Dict[str, Any], existing_ids: set) -> str:
        """Process a single Jira issue"""
        try:
            story_id = issue.get('key', 'unknown')
            logger.debug(f"🔍 Processing issue: {story_id}")
            
            # Extract and validate data
            data = self.processor.extract_issue_data(issue)
            logger.debug(f"🔍 Extracted data for {story_id}: {data.get('summary', 'No summary')}")
            
            if not self.processor.validate_issue_data(data):
                logger.warning(f"❌ Validation failed for {story_id}")
                return "failed"
            
            # Check if already exists
            if story_id in existing_ids:
                logger.debug(f"⚠️ Skipping {story_id} — already exists")
                return "skipped"
            
            # Prepare content
            content = self.processor.prepare_content(data)
            if not content.strip():
                logger.warning(f"❌ Skipping {story_id} — no content")
                return "failed"
            
            logger.debug(f"🔍 Content length for {story_id}: {len(content)} characters")
            
            # Generate embedding and summary
            embedding = Config.EMBEDDING_MODEL.encode(content).tolist()
            summary = self._generate_summary(content)
            
            # Store in LanceDB
            self.table.add([{
                "project_id": data.get("project", ""),
                "vector": embedding,
                "storyID": story_id,
                "storyDescription": summary,
                "test_case_content": "",
                "filename": f"jira_{story_id}",
                "original_path": data.get("jira_url", f"jira://{story_id}"),
                "doc_content_text": content,
                "embedding_timestamp": datetime.now(),
                "source": "jira",
                "jira_metadata": json.dumps({
                    "status": data.get("status"),
                    "priority": data.get("priority"),
                    "assignee": data.get("assignee"),
                    "labels": data.get("labels"),
                    "components": data.get("components"),
                    "created": data.get("created"),
                    "updated": data.get("updated"),
                    "project_id": data.get("project", "")
                })
            }])
            
            logger.info(f"✅ Processed {story_id} (Project: {data.get('project', 'N/A')})")
            return "success"
            
        except Exception as e:
            logger.error(f"❌ Error processing issue {issue.get('key', 'unknown')}: {e}")
            logger.debug(f"🔍 Issue data: {issue}")
            return "failed"
    
    def _generate_summary(self, content: str) -> str:
        """Generate summary using LLM"""
        try:
            prompt = f"Summarize the following Jira story in 1-2 sentences:\n\n{content[:2000]}"
            response = Config.llm.invoke(prompt)
            return response.content.strip()
        except Exception as e:
            logger.error(f"❌ Summary generation failed: {e}")
            return "Summary could not be generated."

# Usage example
async def main():
    """Main function for testing"""
    try:
        integration = JiraIntegration()
        
        # Sync stories with specific filters (using original working approach)
        stats = await integration.sync_stories(
            statuses=[JiraStatus.SELECTED_FOR_DEV, JiraStatus.IN_PROGRESS],
            issue_types=[JiraIssueType.STORY]
        )
        
        print(f"Sync completed: {stats}")
        
    except Exception as e:
        logger.error(f"❌ Integration failed: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 