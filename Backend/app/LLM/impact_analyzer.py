import json
import uuid
from datetime import datetime, timedelta
import lancedb
import numpy as np
from ..config import Config
from ..models.db_service import DatabaseService
from ..models.postgress_writer import get_test_case_json_by_story_id
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
import time
import logging
from typing import Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create handlers
console_handler = logging.StreamHandler()
file_handler = logging.FileHandler('impact_analysis.log')

# Create formatters and add it to handlers
log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(log_format)
file_handler.setFormatter(log_format)

# Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Load the LLM prompt for impact analysis
with open("Backend/app/LLM/impact_analysis_prompt.txt", "r", encoding="utf-8") as f:
    IMPACT_INSTRUCTIONS = f.read()

# Constants for rate limiting and retries
MAX_RETRIES = 3
MAX_CONCURRENT_ANALYSES = 3
MIN_WAIT_BETWEEN_CALLS = 1  # seconds
MAX_STORIES_TO_ANALYZE = 5
API_TIMEOUT = 30  # seconds

class RateLimiter:
    def __init__(self, calls_per_minute: int = 50):
        self.calls_per_minute = calls_per_minute
        self.calls = []
        
    def can_make_call(self) -> bool:
        now = time.time()
        # Remove calls older than 1 minute
        self.calls = [call_time for call_time in self.calls if now - call_time < 60]
        return len(self.calls) < self.calls_per_minute
        
    def record_call(self):
        self.calls.append(time.time())
        
    async def wait_if_needed(self):
        while not self.can_make_call():
            await asyncio.sleep(1)
        self.record_call()

# Global rate limiter instance
rate_limiter = RateLimiter()

class ImpactAnalysisError(Exception):
    """Base class for Impact Analysis errors"""
    pass

class StoryNotFoundError(ImpactAnalysisError):
    """Raised when a story cannot be found"""
    pass

class TestCasesNotFoundError(ImpactAnalysisError):
    """Raised when test cases cannot be found"""
    pass

class LLMError(ImpactAnalysisError):
    """Raised when there's an error with LLM processing"""
    pass

class DatabaseError(ImpactAnalysisError):
    """Raised when there's a database error"""
    pass

def get_db_service() -> DatabaseService:
    """
    Create and return a database service instance with proper error handling
    """
    try:
        db_service = DatabaseService(
            postgres_config=Config.postgres_config(),
            lance_db_path=Config.LANCE_DB_PATH
        )
        return db_service
    except Exception as e:
        logger.error(f"Failed to initialize database service: {str(e)}")
        raise DatabaseError(f"Database initialization failed: {str(e)}")

@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry_error_cls=LLMError
)
async def get_llm_analysis(prompt: str, llm_ref) -> Dict:
    """
    Get analysis from LLM with retry logic and error handling
    """
    try:
        await rate_limiter.wait_if_needed()
        logger.debug("Making LLM API call")
        
        # Add explicit JSON formatting instructions
        structured_prompt = f"""
{prompt}

CRITICAL: Your response MUST be a valid JSON object with this exact structure:
{{
    "has_impact": boolean,
    "impact_type": "MODIFY" | "NO_IMPACT",
    "impacted_test_cases": [
        {{
            "original_test_case_id": "string",
            "modification_reason": "string",
            "modified_test_case": {{
                "id": "string",
                "title": "string",
                "steps": ["string"],
                "expected_result": "string",
                "priority": "High" | "Medium" | "Low"
            }}
        }}
    ]
}}

Do not include any explanatory text before or after the JSON.
Do not use markdown code blocks.
Just return the raw JSON object.
"""
        
        # Get response from LLM
        response = llm_ref.invoke(structured_prompt)
        content = response.content.strip()
        
        # Clean up the response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()
            
        # Try to find JSON object if there's any text before it
        if not content.startswith("{"):
            start_idx = content.find("{")
            if start_idx != -1:
                content = content[start_idx:]
                
        # Try to find JSON object if there's any text after it
        if not content.endswith("}"):
            end_idx = content.rfind("}") + 1
            if end_idx != 0:
                content = content[:end_idx]
        
        try:
            result = json.loads(content)
            
            # Validate required fields
            if not isinstance(result.get("has_impact"), bool):
                raise ValueError("has_impact must be a boolean")
                
            if result.get("impact_type") not in ["MODIFY", "NO_IMPACT"]:
                raise ValueError("impact_type must be either 'MODIFY' or 'NO_IMPACT'")
                
            if not isinstance(result.get("impacted_test_cases", []), list):
                raise ValueError("impacted_test_cases must be a list")
                
            # If we have impacts, validate each test case
            if result["has_impact"] and result["impact_type"] == "MODIFY":
                for test_case in result["impacted_test_cases"]:
                    if not isinstance(test_case.get("original_test_case_id"), str):
                        raise ValueError("original_test_case_id must be a string")
                    if not isinstance(test_case.get("modification_reason"), str):
                        raise ValueError("modification_reason must be a string")
                    if not isinstance(test_case.get("modified_test_case"), dict):
                        raise ValueError("modified_test_case must be an object")
                        
                    modified = test_case["modified_test_case"]
                    if not all(isinstance(modified.get(field), str) for field in ["id", "title", "expected_result"]):
                        raise ValueError("modified_test_case fields must be strings")
                    if not isinstance(modified.get("steps"), list):
                        raise ValueError("steps must be a list")
                    if modified.get("priority") not in ["High", "Medium", "Low"]:
                        raise ValueError("priority must be High, Medium, or Low")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON structure: {str(e)}")
            logger.error(f"Raw content: {content[:500]}")  # Log first 500 chars of content
            raise LLMError("Invalid JSON response from LLM")
        except ValueError as e:
            logger.error(f"Invalid response format: {str(e)}")
            logger.error(f"Parsed content: {json.dumps(result, indent=2)}")
            raise LLMError(f"Invalid response format: {str(e)}")
            
    except Exception as e:
        logger.error(f"LLM processing error: {str(e)}")
        raise LLMError(f"LLM processing error: {str(e)}")

async def store_impact_analysis(
    db_service: DatabaseService,
    impact_data: Dict,
    project_id: str,
    new_story_id: str,
    existing_story_id: str,
    similarity_score: float
) -> int:
    """
    Store impact analysis results in database
    Returns number of impacts stored
    """
    try:
        logger.info(f"Storing impact analysis for story {existing_story_id}")
        
        # Use Config's connection method instead of direct access
        with Config.get_postgres_connection() as conn:
            with conn.cursor() as cursor:
                # Get the run_id for this story
                cursor.execute(
                    "SELECT run_id FROM test_cases WHERE story_id = %s AND project_id = %s",
                    (existing_story_id, project_id)
                )
                result = cursor.fetchone()
                original_run_id = result[0] if result else None
                
                if not original_run_id:
                    logger.error(f"Could not find run_id for story {existing_story_id}")
                    raise DatabaseError(f"Could not find run_id for story {existing_story_id}")
                
                impact_count = 0
                for impacted_test_case in impact_data.get("impacted_test_cases", []):
                    impact_id = str(uuid.uuid4())
                    logger.debug(f"Storing impact {impact_id} for test case {impacted_test_case['original_test_case_id']}")
                    
                    # Insert impact record
                    cursor.execute("""
                        INSERT INTO test_case_impacts (
                            impact_id,
                            project_id,
                            new_story_id,
                            original_story_id,
                            original_test_case_id,
                            modified_test_case_id,
                            original_run_id,
                            impact_created_on,
                            source,
                            similarity_score,
                            impact_analysis_json
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """, (
                        impact_id,
                        project_id,
                        new_story_id,
                        existing_story_id,
                        impacted_test_case["original_test_case_id"],
                        f"{impacted_test_case['original_test_case_id']}-MOD1",
                        original_run_id,
                        datetime.now(),
                        'llm',
                        similarity_score,
                        json.dumps(impacted_test_case)
                    ))
                    
                    # Update the test_cases table
                    cursor.execute("""
                        UPDATE test_cases 
                        SET 
                            impacted_test_case_generated = TRUE,
                            has_impacts = TRUE,
                            latest_impact_id = %s
                        WHERE story_id = %s AND project_id = %s
                    """, (impact_id, existing_story_id, project_id))
                    
                    impact_count += 1
                
                conn.commit()
                logger.info(f"Successfully stored {impact_count} impacts for story {existing_story_id}")
                return impact_count
                
    except Exception as e:
        logger.error(f"Database error while storing impacts: {str(e)}")
        raise DatabaseError(f"Database error while storing impacts: {str(e)}")

async def analyze_test_case_impacts(new_story_id: str, project_id: str, llm_ref=None):
    """
    Analyze how a new story's test cases might impact existing test cases.
    Uses dedicated Gemini API key for impact analysis.
    """
    if llm_ref is None:
        llm_ref = Config.llm_impact
    db_service = None
    try:
        logger.info(f"Starting impact analysis for story: {new_story_id} in project: {project_id}")
        
        if not project_id:
            logger.error("Project ID is required for impact analysis")
            raise ValueError("Project ID is required for impact analysis")
        
        # Initialize database service
        db_service = get_db_service()
        
        # 1. Get the new story's test cases
        new_story_test_cases = get_test_case_json_by_story_id(new_story_id)
        if not new_story_test_cases:
            logger.error(f"No test cases found for story {new_story_id}")
            raise TestCasesNotFoundError(f"No test cases found for story {new_story_id}")
            
        # 2. Find potentially impacted stories using vector similarity
        db = lancedb.connect(Config.LANCE_DB_PATH)
        table = db.open_table(Config.TABLE_NAME_LANCE)
        
        # Get all stories from the same project
        project_data = table.to_pandas()
        project_data = project_data[project_data['project_id'] == project_id]
        
        if project_data.empty:
            logger.error(f"No stories found for project {project_id}")
            raise StoryNotFoundError(f"No stories found for project {project_id}")
        
        # Get the new story's vector and description
        new_story_data = project_data[project_data['storyID'] == new_story_id]
        if new_story_data.empty:
            logger.error(f"Story {new_story_id} not found in project {project_id}")
            raise StoryNotFoundError(f"Story {new_story_id} not found in project {project_id}")
            
        vector = np.array(new_story_data.iloc[0]["vector"])
        new_story_desc = new_story_data.iloc[0]["storyDescription"]
        
        # Search for similar stories ONLY within the same project
        similar_stories = (
            table.search(vector)
            .metric("cosine")
            .where(f"project_id = '{project_id}'")
            .limit(MAX_STORIES_TO_ANALYZE)
            .to_list()
        )
        
        logger.info(f"Found {len(similar_stories)} similar stories in project {project_id}")
        
        # 3. Analyze each similar story individually with concurrency control
        total_impact_count = 0
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_ANALYSES)
        
        async def analyze_story(story):
            async with semaphore:
                if story["storyID"] == new_story_id:  # Skip the new story itself
                    return 0
                    
                existing_story_id = story["storyID"]
                logger.info(f"Analyzing potential impact on story: {existing_story_id}")
                
                try:
                    # Get test cases for this story
                    existing_test_cases = get_test_case_json_by_story_id(existing_story_id)
                    if not existing_test_cases:
                        logger.info(f"Skipping {existing_story_id} - no test cases found")
                        return 0
                    
                    # Generate focused impact analysis prompt for this story
                    prompt = f"{IMPACT_INSTRUCTIONS}\n\n"
                    prompt += f"Project ID: {project_id}\n\n"
                    prompt += f"New Story (ID: {new_story_id}):\n"
                    prompt += f"Description: {new_story_desc}\n"
                    prompt += f"Test Cases: {json.dumps(new_story_test_cases, indent=2)}\n\n"
                    prompt += f"Existing Story to Analyze (ID: {existing_story_id}):\n"
                    prompt += f"Description: {story['storyDescription']}\n"
                    prompt += f"Test Cases: {json.dumps(existing_test_cases, indent=2)}\n"
                    
                    # Get impact analysis for this story
                    impact_analysis = await get_llm_analysis(prompt, llm_ref)
                    
                    # If no impacts found, skip storage
                    if not impact_analysis.get("has_impact", False):
                        logger.info(f"No impact found on story {existing_story_id}")
                        return 0
                    
                    # Store the impacts
                    story_impact_count = await store_impact_analysis(
                        db_service,
                        impact_analysis,
                        project_id,
                        new_story_id,
                        existing_story_id,
                        story["_distance"]
                    )
                    
                    logger.info(f"Stored {story_impact_count} impacts for {existing_story_id}")
                    return story_impact_count
                    
                except (LLMError, DatabaseError) as e:
                    logger.error(f"Error processing story {existing_story_id}: {str(e)}")
                    return 0
                except Exception as e:
                    logger.error(f"Unexpected error for story {existing_story_id}: {str(e)}")
                    return 0
        
        # Process stories concurrently with rate limiting
        tasks = [analyze_story(story) for story in similar_stories]
        impact_counts = await asyncio.gather(*tasks)
        total_impact_count = sum(impact_counts)
        
        logger.info(f"Completed impact analysis for {new_story_id}")
        logger.info(f"Total impacts found across all stories: {total_impact_count}")
        
        return {
            "status": "success",
            "total_impacts": total_impact_count,
            "stories_analyzed": len(similar_stories),
            "timestamp": datetime.now().isoformat()
        }
        
    except ImpactAnalysisError as e:
        logger.error(f"Impact analysis error: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "error_type": e.__class__.__name__,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Unexpected error in impact analysis: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "error_type": "UnexpectedError",
            "timestamp": datetime.now().isoformat()
        }
    finally:
        # Cleanup database service if needed
        if db_service:
            try:
                # No need to close connection as DatabaseService uses context managers
                pass
            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)}") 