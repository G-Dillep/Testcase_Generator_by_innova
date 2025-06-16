from app import create_app
from app.datapipeline.embedding_generator import generate_embeddings
from app.LLM.Test_case_generator import generate_test_cases_for_all_stories

app = create_app()
if __name__ == '__main__':
    # Run data pipeline first
    print("🔄 Running data pipeline...")
    generate_embeddings()
    
    # Generate test cases
    print("🔄 Generating test cases...")
    generate_test_cases_for_all_stories()
    
    # Start Flask application
    print("🚀 Starting Flask application...")
    app.run(host='0.0.0.0', port=5000, debug=True)