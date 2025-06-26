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
from app.LLM.impact_analyzer import analyze_test_case_impacts
import uuid

stories_bp = Blueprint('stories', __name__)

# Get db_service from app context
def get_db_service():
    return current_app.config['DB_SERVICE']

@stories_bp.route('/', methods=['GET'])
def get_stories():
    """Get paginated stories, optionally filtered by date range and project_id"""
    try:
        # Get pagination parameters from query string
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        project_id = request.args.get('project_id')
        sort_order = request.args.get('sort_order', 'desc')  # Default to desc (newest first)
        
        # Validate pagination parameters
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:  # Limit maximum items per page
            per_page = 10
            
        # Validate sort_order
        if sort_order not in ['asc', 'desc']:
            sort_order = 'desc'
            
        db_service = get_db_service()
        result = db_service.get_recent_stories(page=page, per_page=per_page, from_date=from_date, to_date=to_date, project_id=project_id, sort_order=sort_order)
        
        # Get embedding timestamps from LanceDB
        db = lancedb.connect(Config.LANCE_DB_PATH)
        table = db.open_table(Config.TABLE_NAME_LANCE)
        lance_data = table.to_pandas()
        
        # Create a mapping of story IDs to embedding timestamps
        embedding_timestamps = dict(zip(lance_data['storyID'], lance_data['embedding_timestamp']))
        
        # Get impact counts for all stories in one query
        with Config.get_postgres_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                story_ids = [story['id'] for story in result['stories']]
                if story_ids:
                    # Get counts where story is either original or new story
                    cursor.execute("""
                        SELECT 
                            story_id,
                            COUNT(*) as impact_count
                        FROM (
                            SELECT original_story_id as story_id
                            FROM test_case_impacts
                            WHERE original_story_id = ANY(%s)
                            UNION ALL
                            SELECT new_story_id as story_id
                            FROM test_case_impacts
                            WHERE new_story_id = ANY(%s)
                        ) impacts
                        GROUP BY story_id
                    """, (story_ids, story_ids))
                    
                    impact_counts = {row['story_id']: row['impact_count'] for row in cursor.fetchall()}
                else:
                    impact_counts = {}
        
        # Add embedding timestamps and impact counts to stories and ensure ISO format
        for story in result['stories']:
            # Add embedding timestamp
            ts = embedding_timestamps.get(story['id'])
            if ts:
                # If ts is a datetime object, use .isoformat()
                if hasattr(ts, 'isoformat'):
                    story['embedding_timestamp'] = ts.isoformat()
                else:
                    story['embedding_timestamp'] = parser.parse(ts).isoformat()
            else:
                story['embedding_timestamp'] = None
            
            # Add impact count
            story['impactedTestCases'] = impact_counts.get(story['id'], 0)
        
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
                    SELECT test_case_json, story_description, project_id
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
                        'project_id': result[2],
                        'testcases': test_case_json.get('test_cases', [])
                    }

                    print("Processed response data:", response_data)
                    print("Number of test cases:", len(response_data['testcases']))

                    return jsonify(response_data)
                
                print(f"No test cases found for story {story_id}")
                return jsonify({
                    'storyID': story_id,
                    'storyDescription': None,
                    'project_id': None,
                    'testcases': []
                })

    except Exception as e:
        print(f"Error getting test cases for story {story_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@stories_bp.route('/next-reload', methods=['GET'])
def get_next_reload():
    try:
        # Use dynamic path instead of hardcoded path
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        next_reload_file = os.path.join(base_dir, 'next_reload.txt')
        
        if os.path.exists(next_reload_file):
            with open(next_reload_file, 'r') as f:
                content = f.read().strip()
                return content, 200
        else:
            # If file doesn't exist, return current time + 5 minutes
            from datetime import datetime, timedelta
            next_time = datetime.now() + timedelta(minutes=5)
            return next_time.isoformat(), 200
    except Exception as e:
        print(f"Error reading next reload time: {str(e)}")
        # Return current time + 5 minutes as fallback
        from datetime import datetime, timedelta
        next_time = datetime.now() + timedelta(minutes=5)
        return next_time.isoformat(), 200

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

@stories_bp.route('/projects', methods=['GET'])
def get_projects():
    """Get unique project IDs"""
    try:
        db_service = get_db_service()
        
        # Get stories from LanceDB
        stories_table = db_service.lance_db.open_table(Config.TABLE_NAME_LANCE)
        lance_stories = stories_table.to_pandas()
        
        # Get unique project IDs
        project_ids = lance_stories['project_id'].dropna().unique().tolist()
        project_ids = [pid for pid in project_ids if pid and pid.strip()]
        
        return jsonify({
            'projects': project_ids
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@stories_bp.route('/upload', methods=['POST'])
def upload_story():
    """Upload a new user story with project ID, story ID, content, and optional file. Description will be AI-generated."""
    try:
        # Get form data
        project_id = request.form.get('project_id')
        story_id = request.form.get('story_id')
        content = request.form.get('content')  # Changed from description to content
        file = request.files.get('file')
        source = request.form.get('source', 'backend')  # Default to 'backend' if not provided

        # Validate required fields
        if not project_id or not story_id or (not content and not file):
            return jsonify({
                'error': 'Project ID, Story ID, and either Content or File are required'
            }), 400

        # Check if story already exists
        db_service = get_db_service()
        existing_story = db_service.get_story(story_id)
        if existing_story:
            return jsonify({
                'error': f'Story with ID "{story_id}" already exists'
            }), 409

        # Create project folder if it doesn't exist
        import os
        upload_dir = os.getenv("UPLOAD_FOLDER", "./data/uploaded_docs")
        project_dir = os.path.join(upload_dir, project_id)
        os.makedirs(project_dir, exist_ok=True)

        # Handle file upload if provided
        file_path = None
        file_content = None
        
        if file and file.filename:
            # Validate file type
            allowed_extensions = {'.pdf', '.docx', '.txt'}
            file_ext = os.path.splitext(file.filename)[1].lower()
            if file_ext not in allowed_extensions:
                return jsonify({
                    'error': f'File type {file_ext} not supported. Allowed: {", ".join(allowed_extensions)}'
                }), 400

            # Save file to project folder
            filename = f"{story_id}{file_ext}"
            file_path = os.path.join(project_dir, filename)
            file.save(file_path)
            
            # Extract text from file
            try:
                from app.datapipeline.text_extractor import extract_text
                file_content = extract_text(file_path)
                if not file_content:
                    return jsonify({
                        'error': 'Could not extract text from the uploaded file'
                    }), 400
            except Exception as e:
                return jsonify({
                    'error': f'Error extracting text from file: {str(e)}'
                }), 500

        # Create story content (use file content if available, otherwise use typed content)
        story_content = file_content if file_content else content

        # Generate AI description from content
        try:
            from app.LLM.Test_case_generator import Chat_RAG
            rag_instance = Chat_RAG()
            
            # Create a prompt to generate a concise description
            description_prompt = f"""
            Based on the following user story content, generate a concise, clear description that summarizes the key requirements and functionality. 
            The description should be professional and suitable for a test case generation system.
            
            User Story Content:
            {story_content}
            
            Please provide only the description without any additional formatting or explanations.
            """
            
            # Generate description using the LLM
            description_response = rag_instance.chat_with_rag(description_prompt)
            
            # Clean up the response to get just the description
            if description_response and isinstance(description_response, str):
                # Remove any markdown formatting or extra text
                description = description_response.strip()
                if description.startswith('```'):
                    lines = description.split('\n')
                    description = '\n'.join(lines[1:-1]) if len(lines) > 2 else description
                description = description.replace('```', '').strip()
                
                # Limit description length
                if len(description) > 500:
                    description = description[:497] + "..."
            else:
                # Fallback to a simple truncation of content
                description = story_content[:200] + "..." if len(story_content) > 200 else story_content
                
        except Exception as e:
            print(f"Error generating AI description: {str(e)}")
            # Fallback to a simple truncation of content
            description = story_content[:200] + "..." if len(story_content) > 200 else story_content

        # Add to LanceDB
        try:
            from app.config import EMBEDDING_MODEL
            from datetime import datetime
            import lancedb
            
            db = lancedb.connect(Config.LANCE_DB_PATH)
            table = db.open_table(Config.TABLE_NAME_LANCE)
            
            # Generate embedding
            embedding = EMBEDDING_MODEL.encode(story_content).tolist()
            
            # Add to LanceDB
            table.add([{
                "project_id": project_id,
                "vector": embedding,
                "storyID": story_id,
                "storyDescription": description,  # AI-generated description
                "test_case_content": "",
                "filename": filename if file else f"{story_id}.txt",
                "original_path": file_path if file else None,
                "doc_content_text": story_content,
                "embedding_timestamp": datetime.now(),
                "source": source  # Add source field
            }])
            
        except Exception as e:
            return jsonify({
                'error': f'Error adding story to database: {str(e)}'
            }), 500

        # Generate test cases
        try:
            from app.LLM.Test_case_generator import generate_test_case_for_story
            generate_test_case_for_story(story_id)
            
            # Check if test cases were generated successfully
            from app.models.postgress_writer import get_test_case_json_by_story_id
            test_cases_result = get_test_case_json_by_story_id(story_id)
            
            if test_cases_result:
                # Move file to success folder
                if file_path and os.path.exists(file_path):
                    success_dir = os.path.join(os.getenv("SUCCESS_FOLDER", "./data/success"), project_id)
                    os.makedirs(success_dir, exist_ok=True)
                    import shutil
                    shutil.move(file_path, os.path.join(success_dir, filename))
                
                return jsonify({
                    'message': 'Story uploaded and test cases generated successfully',
                    'story_id': story_id,
                    'project_id': project_id,
                    'description': description,  # Return the AI-generated description
                    'test_cases_generated': True,
                    'file_processed': file is not None,
                    'source': source
                }), 200
            else:
                # Move file to failure folder if test case generation failed
                if file_path and os.path.exists(file_path):
                    failure_dir = os.path.join(os.getenv("FAILURE_FOLDER", "./data/failure"), project_id)
                    os.makedirs(failure_dir, exist_ok=True)
                    import shutil
                    shutil.move(file_path, os.path.join(failure_dir, filename))
                
                return jsonify({
                    'message': 'Story uploaded but test case generation failed',
                    'story_id': story_id,
                    'project_id': project_id,
                    'description': description,  # Return the AI-generated description
                    'test_cases_generated': False,
                    'file_processed': file is not None,
                    'source': source
                }), 200
                
        except Exception as e:
            # Move file to failure folder
            if file_path and os.path.exists(file_path):
                failure_dir = os.path.join(os.getenv("FAILURE_FOLDER", "./data/failure"), project_id)
                os.makedirs(failure_dir, exist_ok=True)
                import shutil
                shutil.move(file_path, os.path.join(failure_dir, filename))
            
            return jsonify({
                'error': f'Error generating test cases: {str(e)}'
            }), 500

    except Exception as e:
        print(f"Error in upload_story: {str(e)}")
        return jsonify({
            'error': f'Internal server error: {str(e)}'
        }), 500

@stories_bp.route('/impacts/<project_id>', methods=['GET'])
def get_project_impacts(project_id):
    """Get all impact analyses for a project"""
    try:
        db_service = get_db_service()
        # Use Config's connection method with context managers
        with Config.get_postgres_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        tci.impact_id,
                        tci.new_story_id,
                        tci.original_story_id,
                        tci.original_test_case_id,
                        tci.modified_test_case_id,
                        tci.impact_created_on,
                        tci.similarity_score,
                        tci.impact_analysis_json,
                        tc.story_description as original_story_description
                    FROM test_case_impacts tci
                    JOIN test_cases tc ON tc.story_id = tci.original_story_id
                    WHERE tci.project_id = %s
                    ORDER BY tci.impact_created_on DESC
                """, (project_id,))
                
                impacts = cursor.fetchall()
                
                return jsonify({
                    'project_id': project_id,
                    'total_impacts': len(impacts),
                    'impacts': [dict(impact) for impact in impacts]
                }), 200
                
    except Exception as e:
        print(f"❌ Error fetching project impacts: {e}")
        return jsonify({'error': str(e)}), 500

@stories_bp.route('/impacts/story/<story_id>', methods=['GET'])
def get_story_impacts(story_id):
    """Get impacts where this story is either the source or target"""
    try:
        db_service = get_db_service()
        # Use Config's connection method with context managers
        with Config.get_postgres_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        tci.*,
                        tc_orig.story_description as impacted_story_description,
                        tc_new.story_description as new_story_description
                    FROM test_case_impacts tci
                    JOIN test_cases tc_orig ON tc_orig.story_id = tci.original_story_id
                    JOIN test_cases tc_new ON tc_new.story_id = tci.new_story_id
                    WHERE tci.original_story_id = %s OR tci.new_story_id = %s
                    ORDER BY tci.impact_created_on DESC
                """, (story_id, story_id))
                
                impacts = cursor.fetchall()
                
                # Organize impacts by role (source vs target)
                caused_impacts = []
                received_impacts = []
                
                for impact in impacts:
                    impact_dict = dict(impact)
                    if impact['new_story_id'] == story_id:
                        caused_impacts.append(impact_dict)
                    else:
                        received_impacts.append(impact_dict)
                
                return jsonify({
                    'story_id': story_id,
                    'total_impacts': len(impacts),
                    'caused_impacts': caused_impacts,
                    'received_impacts': received_impacts
                }), 200
                
    except Exception as e:
        print(f"❌ Error fetching story impacts: {e}")
        return jsonify({'error': str(e)}), 500

@stories_bp.route('/impacts/details/<impact_id>', methods=['GET'])
def get_impact_details(impact_id):
    """Get detailed view of a specific impact"""
    try:
        db_service = get_db_service()
        # Use Config's connection method with context managers
        with Config.get_postgres_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        tci.*,
                        tc_orig.story_description as original_story_description,
                        tc_orig.test_case_json as original_test_cases,
                        tc_new.story_description as new_story_description,
                        tc_new.test_case_json as new_test_cases
                    FROM test_case_impacts tci
                    JOIN test_cases tc_orig ON tc_orig.story_id = tci.original_story_id
                    JOIN test_cases tc_new ON tc_new.story_id = tci.new_story_id
                    WHERE tci.impact_id = %s
                """, (impact_id,))
                
                impact = cursor.fetchone()
                
                if not impact:
                    return jsonify({'error': 'Impact not found'}), 404
                    
                return jsonify(dict(impact)), 200
                
    except Exception as e:
        print(f"❌ Error fetching impact details: {e}")
        return jsonify({'error': str(e)}), 500

@stories_bp.route('/impacts/summary/<project_id>', methods=['GET'])
def get_project_impact_summary(project_id):
    """Get summary of impacts in a project"""
    try:
        db_service = get_db_service()
        cursor = db_service.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Get summary from our view
        cursor.execute("""
            SELECT * FROM test_case_impact_summary
            WHERE project_id = %s
            ORDER BY total_impacts DESC
        """, (project_id,))
        
        summaries = cursor.fetchall()
        cursor.close()
        
        return jsonify({
            'project_id': project_id,
            'total_stories': len(summaries),
            'stories_with_impacts': len([s for s in summaries if s['total_impacts'] > 0]),
            'summaries': [dict(summary) for summary in summaries]
        }), 200
        
    except Exception as e:
        print(f"❌ Error fetching impact summary: {e}")
        return jsonify({'error': str(e)}), 500

@stories_bp.route('/impacts/analyze', methods=['POST'])
async def trigger_impact_analysis():
    """Manually trigger impact analysis for a story"""
    try:
        data = request.get_json()
        story_id = data.get('story_id')
        project_id = data.get('project_id')
        
        if not story_id or not project_id:
            return jsonify({
                'error': 'Both story_id and project_id are required'
            }), 400
            
        # Run impact analysis
        await analyze_test_case_impacts(story_id, project_id)
        
        return jsonify({
            'message': 'Impact analysis triggered successfully',
            'story_id': story_id,
            'project_id': project_id
        }), 200
        
    except Exception as e:
        print(f"❌ Error triggering impact analysis: {e}")
        return jsonify({'error': str(e)}), 500

@stories_bp.route('/<story_id>/test-cases/<test_case_id>', methods=['GET'])
def get_test_case(story_id, test_case_id):
    """Get a specific test case from a story"""
    try:
        print(f"Fetching test case {test_case_id} from story {story_id}")
        db_service = get_db_service()
        
        # Get test cases from PostgreSQL
        with psycopg2.connect(**db_service.postgres_config) as conn:
            with conn.cursor() as cur:
                # Use a JSON path query to extract the specific test case
                cur.execute("""
                    WITH test_cases_array AS (
                        SELECT jsonb_array_elements(test_case_json->'test_cases') as test_case
                        FROM test_cases
                        WHERE story_id = %s
                    )
                    SELECT test_case
                    FROM test_cases_array
                    WHERE test_case->>'id' = %s
                    OR test_case->>'test_case_id' = %s
                    LIMIT 1
                """, (story_id, test_case_id, test_case_id))
                result = cur.fetchone()

                if not result:
                    return jsonify({
                        'error': f'Test case {test_case_id} not found in story {story_id}'
                    }), 404

                test_case = result[0]
                return jsonify({
                    'id': test_case.get('id') or test_case.get('test_case_id'),
                    'title': test_case.get('title'),
                    'test_steps': test_case.get('steps', []),
                    'expected_result': test_case.get('expected_result', ''),
                    'priority': test_case.get('priority', 'medium'),
                    'severity': test_case.get('severity', 'medium')
                })

    except Exception as e:
        print(f"Error getting test case {test_case_id} from story {story_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500 