import psycopg2
import lancedb
import json
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from app.config import Config
import psycopg2.extras

class DatabaseService:
    _instance = None
    
    def __init__(self, postgres_config: Dict[str, Any], lance_db_path: str):
        """Initialize database connections"""
        if DatabaseService._instance is not None:
            raise Exception("DatabaseService is a singleton!")
            
        self.postgres_config = postgres_config
        self.lance_db_path = lance_db_path
        self.lance_db = lancedb.connect(lance_db_path)
        self.postgres_config = {
            'dbname': Config.POSTGRES_DB,
            'user': Config.POSTGRES_USER,
            'password': Config.POSTGRES_PASSWORD,
            'host': Config.POSTGRES_HOST,
            'port': Config.POSTGRES_PORT
        }
        self.TABLE_NAME_LANCE = Config.TABLE_NAME_LANCE
        DatabaseService._instance = self
   
    def get_recent_stories(self, page: int = 1, per_page: int = 10, from_date: str = None, to_date: str = None, project_id: str = None, sort_order: str = 'desc') -> Dict[str, Any]:
        """
        Get paginated stories with test case information from both PostgreSQL and LanceDB
        Optionally filter by created_on date range and project_id.
        Sorted by test_case_created_time (most recent first by default).
        """
        try:
            # Get stories from LanceDB
            stories_table = self.lance_db.open_table(self.TABLE_NAME_LANCE)
            lance_stories = stories_table.to_pandas()

            # Filter by project_id if provided
            if project_id:
                lance_stories = lance_stories[lance_stories['project_id'] == project_id]

            # Get all stories with their test case creation times for sorting
            story_ids = lance_stories['storyID'].tolist()
            created_on_map = {}
            test_case_times_map = {}
            test_case_count_map = {}
            test_case_source_map = {}
            
            with psycopg2.connect(**self.postgres_config) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT story_id, created_on, total_test_cases, source
                        FROM test_cases 
                        WHERE story_id = ANY(%s)
                        ORDER BY created_on DESC NULLS LAST
                    """, (story_ids,))
                    for row in cur.fetchall():
                        story_id, created_on, total_test_cases, source = row
                        if story_id not in created_on_map:
                            created_on_map[story_id] = created_on
                            test_case_times_map[story_id] = created_on  # Use created_on as last updated time
                            test_case_count_map[story_id] = total_test_cases
                            test_case_source_map[story_id] = source

            # Add created_on and test_case_created_time to LanceDB data
            lance_stories['created_on'] = lance_stories['storyID'].map(created_on_map)
            lance_stories['test_case_created_time'] = lance_stories['storyID'].map(test_case_times_map)
            lance_stories['total_test_cases'] = lance_stories['storyID'].map(test_case_count_map)
            lance_stories['test_case_source'] = lance_stories['storyID'].map(test_case_source_map)

            # Filter by date range if provided
            if from_date:
                lance_stories = lance_stories[lance_stories['created_on'] >= from_date]
            if to_date:
                lance_stories = lance_stories[lance_stories['created_on'] <= to_date]

            # Sort by test_case_created_time based on sort_order
            ascending = sort_order.lower() == 'asc'
            lance_stories = lance_stories.sort_values(
                by=['test_case_created_time', 'storyID'], 
                ascending=[ascending, True], 
                na_position='last'
            )

            # Calculate pagination
            total_stories = len(lance_stories)
            total_pages = (total_stories + per_page - 1) // per_page
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page

            # Get paginated stories
            paginated_stories = lance_stories.iloc[start_idx:end_idx]

            stories = []
            for _, lance_story in paginated_stories.iterrows():
                story_id = lance_story['storyID']
                test_case_created_time = lance_story['test_case_created_time']
                test_case_count = lance_story.get('total_test_cases', 0)
                
                stories.append({
                    'id': story_id,
                    'description': lance_story['storyDescription'],
                    'document_content': lance_story.get('document_content', None),
                    'test_case_count': test_case_count if test_case_count is not None else 0,
                    'download_link': f'/api/stories/download/{story_id}',
                    'test_case_created_time': test_case_created_time.isoformat() if test_case_created_time else None,
                    'project_id': lance_story['project_id'],
                    'source': {
                        'story': lance_story.get('source', 'backend'),
                        'test_cases': lance_story.get('test_case_source', 'backend')
                    }
                })

            return {
                'stories': stories,
                'total': total_stories,
                'total_pages': total_pages,
                'current_page': page,
                'per_page': per_page
            }
        except Exception as e:
            print(f"Error getting recent stories: {str(e)}")
            return {
                'stories': [],
                'total': 0,
                'total_pages': 0,
                'current_page': page,
                'per_page': per_page
            }
        
    def get_story(self, story_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific story by ID from both LanceDB and PostgreSQL"""
        try:
            # Get story from LanceDB
            stories_table = self.lance_db.open_table(self.TABLE_NAME_LANCE)
            story_data = stories_table.to_pandas()
            lance_story = story_data[story_data['storyID'] == story_id]
            
            if lance_story.empty:
                print(f"Story not found in LanceDB: {story_id}")
                return None
            
            # Get the latest test case row for this story_id
            with psycopg2.connect(**self.postgres_config) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT total_test_cases, created_on, source
                        FROM test_cases
                        WHERE story_id = %s
                        ORDER BY created_on DESC NULLS LAST
                        LIMIT 1
                    """, (story_id,))
                    pg_result = cur.fetchone()
                
            # Get embedding_timestamp from LanceDB
            embedding_timestamp = None
            if 'embedding_timestamp' in lance_story.columns:
                ts = lance_story['embedding_timestamp'].iloc[0]
                if ts:
                    if hasattr(ts, 'isoformat'):
                        embedding_timestamp = ts.isoformat()
                    else:
                        from dateutil import parser
                        embedding_timestamp = parser.parse(ts).isoformat()
                    
            return {
                'id': story_id,
                'description': lance_story['storyDescription'].iloc[0],
                'document_content': lance_story['doc_content_text'].iloc[0] if 'doc_content_text' in lance_story.columns else None,
                'test_case_count': pg_result[0] if pg_result else 0,
                'download_link': f'/api/stories/download/{story_id}',
                'test_case_created_time': pg_result[1].isoformat() if pg_result and pg_result[1] else None,
                'embedding_timestamp': embedding_timestamp,
                'project_id': lance_story['project_id'].iloc[0] if 'project_id' in lance_story.columns else '',
                'source': {
                    'story': lance_story['source'].iloc[0] if 'source' in lance_story.columns else 'backend',
                    'test_cases': pg_result[2] if pg_result and len(pg_result) > 2 else 'backend'
                }
            }
        except Exception as e:
            print(f"Error getting story {story_id}: {str(e)}")
            return None
        
    def search_similar_stories(self, query: str, limit: int = 3) -> Dict[str, Any]:
        """
        Search for similar stories using vector similarity
        Args:
            query: Search query
            limit: Maximum number of results to return (default 3)
        Returns:
            Dictionary containing list of similar stories with similarity scores
        """
        try:
            if not query or not query.strip():
                return {'stories': [], 'error': 'Query cannot be empty'}

            # Get stories table from LanceDB
            stories_table = self.lance_db.open_table(self.TABLE_NAME_LANCE)
            
            # Get all data first to ensure we have complete story content
            lance_data = stories_table.to_pandas()
            
            # Encode the query using the embedding model
            query_vector = Config.EMBEDDING_MODEL.encode(query).tolist()

            # Use LanceDB vector search
            results = (
                stories_table.search(query_vector)
                .metric("cosine")
                .limit(limit)
                .to_list()
            )

            if not results:
                return {'stories': [], 'message': 'No matching stories found'}

            # Get PostgreSQL connection for fetching additional data
            with psycopg2.connect(**self.postgres_config) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    stories = []
                    for result in results:
                        story_id = result['storyID']
                        
                        # Get complete story data from LanceDB DataFrame
                        lance_story = lance_data[lance_data['storyID'] == story_id].iloc[0]
                        
                        # Get story content from multiple possible sources
                        story_content = (
                            lance_story.get('doc_content_text', '') or 
                            lance_story.get('storyDescription', '')
                        )
                        
                        # Fetch test case data and impacted test cases count
                        cur.execute("""
                            SELECT 
                                story_description,
                                test_case_json,
                                total_test_cases,
                                created_on,
                                source,
                                impacted_test_cases_count,
                                inputs
                            FROM test_cases 
                            WHERE story_id = %s
                        """, (story_id,))
                        pg_result = cur.fetchone()
                        
                        if pg_result:
                            # Get additional content from PostgreSQL inputs if available
                            pg_inputs = pg_result['inputs'] if pg_result['inputs'] else {}
                            if isinstance(pg_inputs, str):
                                import json
                                pg_inputs = json.loads(pg_inputs)
                            
                            # Use the most complete content available
                            content = (
                                story_content or 
                                pg_inputs.get('content', '') or 
                                pg_inputs.get('file_content', '') or 
                                pg_result['story_description']
                            )
                            
                            story_data = {
                                'id': story_id,
                                'description': pg_result['story_description'],
                                'document_content': content,  # Full story content
                                'story_content': content,     # Additional field for story content
                                'content': content,          # Another field for story content
                                'test_case_count': pg_result['total_test_cases'] or 0,
                                'impactedTestCases': pg_result['impacted_test_cases_count'] or 0,
                                'download_link': f'/api/stories/download/{story_id}',
                                'test_case_created_time': pg_result['created_on'].isoformat() if pg_result['created_on'] else None,
                                'test_case_json': pg_result['test_case_json'],
                                'similarity_score': result.get('_distance'),
                                'source': {
                                    'story': lance_story.get('source', 'backend'),
                                    'test_cases': pg_result['source'] or 'backend'
                                }
                            }
                            stories.append(story_data)

            return {'stories': stories}
        except Exception as e:
            print(f"Error searching stories: {str(e)}")
            return {'stories': [], 'error': str(e)}
        

def get_db_service() -> DatabaseService:
    """Get or create the singleton instance of DatabaseService"""
    if DatabaseService._instance is None:
        DatabaseService(
            postgres_config={
                'dbname': Config.POSTGRES_DB,
                'user': Config.POSTGRES_USER,
                'password': Config.POSTGRES_PASSWORD,
                'host': Config.POSTGRES_HOST,
                'port': Config.POSTGRES_PORT
            },
            lance_db_path=Config.LANCE_DB_PATH
        )
    return DatabaseService._instance
        
