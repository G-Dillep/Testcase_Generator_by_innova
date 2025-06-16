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
   
    def get_recent_stories(self, page: int = 1, per_page: int = 10) -> Dict[str, Any]:
        """
        Get paginated stories with test case information from both PostgreSQL and LanceDB
        
        Args:
            page: Page number (starts from 1)
            per_page: Number of items per page
            
        Returns:
            Dictionary containing:
            - stories: List of stories for the current page
            - total: Total number of stories
            - total_pages: Total number of pages
            - current_page: Current page number
            - per_page: Number of items per page
        """
        try:
            # Get stories from LanceDB
            stories_table = self.lance_db.open_table(self.TABLE_NAME_LANCE)
            lance_stories = stories_table.to_pandas()
            
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
                
                # Get test case count from PostgreSQL
                with psycopg2.connect(**self.postgres_config) as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT total_test_cases, created_on
                            FROM test_cases
                            WHERE story_id = %s
                        """, (story_id,))
                        pg_result = cur.fetchone()
                
                stories.append({
                    'id': story_id,
                    'description': lance_story['storyDescription'],
                    'num_test_cases': pg_result[0] if pg_result else 0,
                    'download_link': f'/api/stories/download/{story_id}',
                    'created_on': pg_result[1].isoformat() if pg_result and pg_result[1] else None
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
            
            # Get test case information from PostgreSQL
            with psycopg2.connect(**self.postgres_config) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT total_test_cases, created_on
                        FROM test_cases
                        WHERE story_id = %s
                    """, (story_id,))
                    pg_result = cur.fetchone()
            
            return {
                'id': story_id,
                'description': lance_story['storyDescription'].iloc[0],
                'num_test_cases': pg_result[0] if pg_result else 0,
                'download_link': f'/api/stories/download/{story_id}',
                'created_on': pg_result[1].isoformat() if pg_result and pg_result[1] else None
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

            # Get stories from LanceDB
            stories_table = self.lance_db.open_table(self.TABLE_NAME_LANCE)
            stories_df = stories_table.to_pandas()
            
            # Convert everything to lowercase for case-insensitive search
            query = query.lower()
            stories_df['description_lower'] = stories_df['storyDescription'].str.lower()
            
            # Find stories containing the query
            matching_stories = stories_df[stories_df['description_lower'].str.contains(query, na=False)]
            
            # Calculate a simple similarity score based on query length
            matching_stories['similarity_score'] = matching_stories['description_lower'].apply(
                lambda x: min(1.0, len(query) / len(x))
            )
            
            # Sort by similarity score and get top results
            results = matching_stories.nlargest(limit, 'similarity_score')
            
            # Format results
            stories = []
            for _, row in results.iterrows():
                stories.append({
                    'id': row['storyID'],
                    'description': row['storyDescription'],
                    'similarity_score': float(row['similarity_score'])
                })
            
            return {'stories': stories}
        except Exception as e:
            print(f"Error searching stories: {str(e)}")
            return {'stories': [], 'error': str(e)}
        
