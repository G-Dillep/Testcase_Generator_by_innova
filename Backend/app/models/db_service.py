import psycopg2
import lancedb
import json
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from app.config import Config

class DatabaseService:
    def __init__(self, postgres_config: Dict[str, Any], lance_db_path: str):
        """Initialize database connections"""
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
   
    def get_recent_stories(self, page: int = 1, per_page: int = 10, from_date: str = None, to_date: str = None) -> Dict[str, Any]:
        """
        Get paginated stories with test case information from both PostgreSQL and LanceDB
        Optionally filter by created_on date range.
        """
        try:
            # Get stories from LanceDB
            stories_table = self.lance_db.open_table(self.TABLE_NAME_LANCE)
            lance_stories = stories_table.to_pandas()

            # Add created_on from PostgreSQL for filtering
            if from_date or to_date:
                # Get all created_on values from PostgreSQL for all story IDs
                story_ids = lance_stories['storyID'].tolist()
                created_on_map = {}
                with psycopg2.connect(**self.postgres_config) as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT story_id, created_on FROM test_cases WHERE story_id = ANY(%s)
                        """, (story_ids,))
                        for row in cur.fetchall():
                            created_on_map[row[0]] = row[1]
                lance_stories['created_on'] = lance_stories['storyID'].map(created_on_map)
                if from_date:
                    lance_stories = lance_stories[lance_stories['created_on'] >= from_date]
                if to_date:
                    lance_stories = lance_stories[lance_stories['created_on'] <= to_date]

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
                # Get the latest test case row for this story_id
                with psycopg2.connect(**self.postgres_config) as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT total_test_cases, created_on
                            FROM test_cases
                            WHERE story_id = %s
                            ORDER BY created_on DESC NULLS LAST
                            LIMIT 1
                        """, (story_id,))
                        pg_result = cur.fetchone()
                stories.append({
                    'id': story_id,
                    'description': lance_story['storyDescription'],
                    'document_content': lance_story['doc_content_text'] if 'doc_content_text' in lance_story else None,
                    'test_case_count': pg_result[0] if pg_result else 0,
                    'download_link': f'/api/stories/download/{story_id}',
                    'test_case_created_time': pg_result[1].isoformat() if pg_result and pg_result[1] else None
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
                        SELECT total_test_cases, created_on
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
                'embedding_timestamp': embedding_timestamp
            }
        except Exception as e:
            print(f"Error getting story {story_id}: {str(e)}")
            return None
        
    def search_similar_stories(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Search for similar stories using vector similarity
        Args:
            query: Search query
            limit: Maximum number of results to return
        Returns:
            Dictionary containing list of similar stories with similarity scores
        """
        try:
            if not query or not query.strip():
                return {'stories': [], 'error': 'Query cannot be empty'}

            # Get stories table from LanceDB
            stories_table = self.lance_db.open_table(self.TABLE_NAME_LANCE)

            # Encode the query using the embedding model
            query_vector = Config.EMBEDDING_MODEL.encode(query).tolist()

            # Use LanceDB vector search
            results = (
                stories_table.search(query_vector)
                .metric("cosine")
                .limit(limit)
                .to_list()
            )

            print(f"[DEBUG] Vector search returned {len(results)} results for query: '{query}'")
            for result in results:
                print(f"[DEBUG] ID: {result['storyID']}, Score: {result.get('_distance', None)}")

            stories = []
            for result in results:
                story_id = result['storyID']
                story_data = self.get_story(story_id)
                if story_data:
                    story_data['similarity_score'] = result.get('_distance', None)
                    stories.append(story_data)

            return {'stories': stories}
        except Exception as e:
            print(f"Error searching stories: {str(e)}")
            return {'stories': [], 'error': str(e)}
        
