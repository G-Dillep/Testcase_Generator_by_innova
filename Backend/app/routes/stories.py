from flask import Blueprint, jsonify, request, current_app
from flask import send_file
import psycopg2
from app.utils.excel_util import generate_excel
import json
import lancedb
from app.config import Config
from dateutil import parser
import requests
import os
from app.LLM.Test_case_generator import Chat_RAG

stories_bp = Blueprint('stories', __name__)

# Get db_service from app context
def get_db_service():
    return current_app.config['DB_SERVICE']

@stories_bp.route('/', methods=['GET'])
def get_stories():
    """Get paginated stories, optionally filtered by date range"""
    try:
        # Get pagination parameters from query string
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        
        # Validate pagination parameters
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:  # Limit maximum items per page
            per_page = 10
            
        db_service = get_db_service()
        result = db_service.get_recent_stories(page=page, per_page=per_page, from_date=from_date, to_date=to_date)
        
        # Get embedding timestamps from LanceDB
        db = lancedb.connect(Config.LANCE_DB_PATH)
        table = db.open_table(Config.TABLE_NAME_LANCE)
        lance_data = table.to_pandas()
        
        # Create a mapping of story IDs to embedding timestamps
        embedding_timestamps = dict(zip(lance_data['storyID'], lance_data['embedding_timestamp']))
        
        # Add embedding timestamps to stories and ensure ISO format
        for story in result['stories']:
            ts = embedding_timestamps.get(story['id'])
            if ts:
                # If ts is a datetime object, use .isoformat()
                if hasattr(ts, 'isoformat'):
                    story['embedding_timestamp'] = ts.isoformat()
                else:
                    story['embedding_timestamp'] = parser.parse(ts).isoformat()
            else:
                story['embedding_timestamp'] = None
        
        return jsonify({
            'stories': result['stories'],
            'total_pages': result['total_pages'],
            'current_page': page
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@stories_bp.route('/<story_id>', methods=['GET'])
def get_story(story_id):
    """Get a specific story"""
    try:
        if not story_id:
            return jsonify({'error': 'Story ID is required'}), 400

        db_service = get_db_service()
        story = db_service.get_story(story_id)
        
        if story:
            return jsonify(story)
        return jsonify({'error': f'Story not found: {story_id}'}), 404
    except Exception as e:
        print(f"Error getting story {story_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@stories_bp.route('/search', methods=['POST'])
def search_stories():
    """Search for similar stories"""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'Query is required'}), 400
            
        query = data['query']
        limit = data.get('limit', 5)
        
        if not query.strip():
            return jsonify({'error': 'Query cannot be empty'}), 400
            
        if limit < 1:
            limit = 5
            
        db_service = get_db_service()
        results = db_service.search_similar_stories(query, limit)
        return jsonify(results)
    except Exception as e:
        print(f"Error searching stories: {str(e)}")
        return jsonify({'error': str(e)}), 500

@stories_bp.route('/testcases/download/<story_id>', methods=['GET'])
def download_test_cases(story_id):
    """Download test cases for a story as Excel file"""
    try:
        db_service = get_db_service()
        
        # Get story details from LanceDB
        story = db_service.get_story(story_id)
        if not story:
            return jsonify({
                'error': f'Story not found with ID: {story_id}'
            }), 404

        # Get test cases from PostgreSQL
        with psycopg2.connect(**db_service.postgres_config) as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT test_case_json, story_description 
                    FROM test_cases 
                    WHERE story_id = %s
                """, (story_id,))
                result = cursor.fetchone()

                if not result:
                    return jsonify({
                        'error': f'No test cases found for story ID: {story_id}'
                    }), 404

                # Parse the test cases JSON if it's a string
                test_case_json = result[0]
                if isinstance(test_case_json, str):
                    try:
                        test_case_json = json.loads(test_case_json)
                    except json.JSONDecodeError as e:
                        print(f"Error parsing test cases JSON: {str(e)}")
                        return jsonify({
                            'error': 'Invalid test cases data format'
                        }), 500

                # Prepare data for Excel generation
                test_case_json = {
                    'storyID': story_id,
                    'storyDescription': result[1],
                    'testcases': test_case_json['test_cases']
                }
                print(test_case_json)

                # Generate Excel file
                try:
                    excel_file = generate_excel(test_case_json)
                    return send_file(
                        excel_file,
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        as_attachment=True,
                        download_name=f'test_cases_{story_id}.xlsx'
                    )
                except Exception as e:
                    print(f"Error generating Excel file: {str(e)}")
                    return jsonify({
                        'error': 'Failed to generate Excel file',
                        'details': str(e)
                    }), 500

    except Exception as e:
        print(f"Error in download_test_cases: {str(e)}")
        return jsonify({
            'error': 'Failed to download test cases',
            'details': str(e)
        }), 500

@stories_bp.route('/<story_id>/testcases', methods=['GET'])
def get_story_testcases(story_id):
    """Get test cases for a specific story"""
    try:
        print(f"Fetching test cases for story: {story_id}")
        db_service = get_db_service()
        
        # Get test cases from PostgreSQL
        with psycopg2.connect(**db_service.postgres_config) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT test_case_json, story_description 
                    FROM test_cases 
                    WHERE story_id = %s
                """, (story_id,))
                result = cur.fetchone()

                if result and result[0]:
                    print("Raw database result:", result)
                    # Parse the test cases JSON if it's a string
                    test_case_json = result[0]
                    if isinstance(test_case_json, str):
                        try:
                            test_case_json = json.loads(test_case_json)
                            print("Parsed JSON from string:", test_case_json)
                        except json.JSONDecodeError as e:
                            print(f"Error parsing test cases JSON: {str(e)}")
                            return jsonify({
                                'error': 'Invalid test cases data format'
                            }), 500

                    print("Raw test case JSON:", test_case_json)

                    # Prepare data in the same format as the download endpoint
                    response_data = {
                        'storyID': story_id,
                        'storyDescription': result[1],
                        'testcases': test_case_json.get('test_cases', [])
                    }

                    print("Processed response data:", response_data)
                    print("Number of test cases:", len(response_data['testcases']))

                    return jsonify(response_data)
                
                print(f"No test cases found for story {story_id}")
                return jsonify({
                    'storyID': story_id,
                    'storyDescription': None,
                    'testcases': []
                })

    except Exception as e:
        print(f"Error getting test cases for story {story_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@stories_bp.route('/next-reload', methods=['GET'])
def get_next_reload():
    try:
        return send_file('E:\Srini Kosam\Test-Case-Generator\Backend\\next_reload.txt', mimetype='text/plain')
    except Exception as e:
        return "unknown", 200

@stories_bp.route('/trigger-reload', methods=['POST'])
def trigger_reload():
    """Trigger the scheduler to run immediately"""
    try:
        from scheduler import scheduled_job
        scheduled_job()
        return jsonify({'message': 'Scheduler triggered successfully'}), 200
    except Exception as e:
        print(f"Error triggering scheduler: {str(e)}")
        return jsonify({'error': str(e)}), 500

@stories_bp.route('/rag-chat', methods=['POST'])
def rag_chat():
    """RAG chatbot endpoint: retrieves similar test cases, sends them as context to Gemini, returns generated test cases."""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'Query is required'}), 400
        user_query = data['query']
        # 1. Retrieve similar stories and their test cases
        rag_results = Chat_RAG(user_query, top_k=3)
        context_cases = []
        for res in rag_results:
            tc_json = res.get('test_case_json')
            if tc_json and isinstance(tc_json, dict) and 'test_cases' in tc_json:
                context_cases.extend(tc_json['test_cases'])
        if not context_cases:
            return jsonify({'error': 'No relevant test cases found.'}), 404

        # 2. Build prompt for Gemini
        context_str = '\n'.join([
            f"Test Case {i+1}: {tc.get('title', '')}\nDescription: {tc.get('description', '')}\nSteps: {tc.get('steps', [])}\nExpected Result: {tc.get('expected_result', '')}\n" for i, tc in enumerate(context_cases)
        ])
        prompt = f"""
You are an experienced QA analyst. Here are test cases from similar stories:
{context_str}

Now, based on the following user story, generate new, comprehensive test cases in JSON format (fields: id, title, steps, expected_result, priority):
{user_query}
"""

        # 3. Call Gemini LLM using the configured object
        response = Config.llm.invoke(prompt)
        text = response.content.strip()
        print("LLM raw output:", repr(text))
        # Clean triple backticks and ```json
        cleaned = text.strip()
        if cleaned.startswith('```json'):
            cleaned = cleaned[7:]
        if cleaned.startswith('```'):
            cleaned = cleaned[3:]
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        import json
        try:
            parsed = json.loads(cleaned)
            # If it's a list of test cases, return as JSON
            if isinstance(parsed, list):
                return jsonify({'testCases': parsed})
            # If it's a dict with 'test_cases', return that
            if isinstance(parsed, dict) and 'test_cases' in parsed:
                return jsonify({'testCases': parsed['test_cases']})
            # Otherwise, return the parsed object
            return jsonify({'testCases': parsed})
        except Exception as e:
            print("Failed to parse LLM output as JSON:", e)
            return jsonify({'raw': cleaned, 'error': 'Failed to parse LLM output as JSON'}), 200
    except Exception as e:
        print(f"Error in rag_chat: {str(e)}")
        return jsonify({'error': str(e)}), 500 