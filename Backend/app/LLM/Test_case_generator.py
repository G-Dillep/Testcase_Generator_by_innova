import os
import json
import lancedb
import numpy as np
from dotenv import load_dotenv
from app.config import Config
from app.models.postgress_writer import (
    insert_test_case,
    get_test_case_json_by_story_id,
    get_all_generated_story_ids
)
import pandas as pd

load_dotenv()

# === CONFIGURATION ===
LANCE_DB_PATH = Config.LANCE_DB_PATH
TABLE_NAME = Config.TABLE_NAME_LANCE
TOP_K = 3
MAX_MAIN_TEXT_CHARS = 5000

# Load prompt
with open("Backend/app/LLM/test_case_prompt.txt", "r", encoding="utf-8") as f:
    INSTRUCTIONS = f.read()

def generate_test_case_for_story(story_id, llm_ref=Config.llm):
    db = lancedb.connect(Config.LANCE_DB_PATH)
    table = db.open_table(Config.TABLE_NAME_LANCE)
    all_rows = table.to_pandas()
    row_data = all_rows[all_rows['storyID'] == story_id]
    
    if row_data.empty:
        print(f"❌ Story ID '{story_id}' not found in LanceDB.")
        return
    
    row = row_data.iloc[0].to_dict()
    
    # Check if story has a vector
    vector_value = row.get("vector")
    if vector_value is None or (hasattr(vector_value, '__len__') and len(vector_value) == 0):
        print(f"❌ Story ID '{story_id}' is missing a vector and cannot be processed.")
        return

    story_description = row["storyDescription"]
    vector = np.array(row["vector"])
    main_text = row.get("doc_content_text", "").strip()

    if not main_text:
        print(f"❌ Skipping {story_id} — missing doc_content_text.")
        return

    print(f"🔍 Generating test case for: {story_id}")

    # Get similar docs using cosine similarity
    similar_docs = (
        table.search(vector)
        .metric("cosine")
        .limit(TOP_K + 5)
        .to_list()
    )

    context_parts = []
    for doc in similar_docs:
        ctx_story_id = doc["storyID"]
        if ctx_story_id == story_id:
            continue

        test_case_json = get_test_case_json_by_story_id(ctx_story_id)
        if test_case_json:
            context_parts.append(f"--- Context from {ctx_story_id} ---\n{json.dumps(test_case_json, indent=2)}")

        if len(context_parts) >= TOP_K:
            break

    context_text = "\n\n".join(context_parts)

    # Enhanced prompt to ensure JSON output
    full_prompt = (
        f"{INSTRUCTIONS.strip()}\n\n"
        f"IMPORTANT: You must respond with a valid JSON object containing test cases. Do not include any other text or formatting.\n\n"
        f"=======================\n"
        f"📄 USER STORY DOCUMENT ({story_id}):\n"
        f"{main_text}\n\n"
        f"=======================\n"
        f"📚 RELEVANT CONTEXT TEST CASES:\n"
        f"{context_text if context_text else '[No similar context found]'}\n\n"
        f"Remember to respond with ONLY a JSON object containing the test cases."
    )

    try:
        response = llm_ref.invoke(full_prompt)
        content = response.content.strip()

        # Clean up the response to ensure it's valid JSON
        content = content.replace("```json", "").replace("```", "").strip()
        
        # If the response starts with any non-JSON text, remove it
        if not content.startswith("{"):
            content = content[content.find("{"):]
        if not content.endswith("}"):
            content = content[:content.rfind("}")+1]

        try:
            testcases = json.loads(content)
            if not isinstance(testcases, dict):
                raise ValueError("Response is not a JSON object")
                
            # Ensure the test cases have the required structure
            if "test_cases" not in testcases:
                testcases = {"test_cases": testcases}
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode failed for {story_id}: {e}")
            print("Raw response:\n", content[:1000])
            return
        except ValueError as e:
            print(f"❌ Invalid response format for {story_id}: {e}")
            print("Raw response:\n", content[:1000])
            return

        insert_test_case(
            story_id=story_id,
            story_description=story_description,
            test_case_json=testcases
        )
        print(f"✅ Inserted test cases for {story_id} into Postgres.\n")

    except Exception as e:
        print(f"❌ LLM error for {story_id}: {e}")

# === Run for all unprocessed
def generate_test_cases_for_all_stories():
    db = lancedb.connect(Config.LANCE_DB_PATH)
    table = db.open_table(Config.TABLE_NAME_LANCE)

    generated_ids = set(get_all_generated_story_ids())
    all_rows = table.to_pandas()
    
    print(f"📊 Total stories in LanceDB: {len(all_rows)}")
    print(f"📊 Already generated stories: {len(generated_ids)}")
    
    # Check for missing vectors
    missing_vector_count = 0
    for index, row in all_rows.iterrows():
        vector_value = row.get("vector")
        if vector_value is None or (hasattr(vector_value, '__len__') and len(vector_value) == 0):
            print(f"Story {row['storyID']} is missing a vector and will not be processed.")
            missing_vector_count += 1
    
    print(f"📊 Stories missing vectors: {missing_vector_count}")
    
    # Get all story IDs and filter out already generated ones
    all_story_ids = all_rows['storyID'].tolist()
    records = [story_id for story_id in all_story_ids if story_id not in generated_ids]
    
    print(f"🟡 Found {len(records)} entries to process.\n")
    
    if len(records) == 0:
        print("✅ All stories with vectors have been processed!")
        return
        
    for story_id in records:
        generate_test_case_for_story(story_id)

def Chat_RAG(user_query, top_k=3):
    db = lancedb.connect(Config.LANCE_DB_PATH)
    table = db.open_table(Config.TABLE_NAME_LANCE)
    query_vector = Config.EMBEDDING_MODEL.encode(user_query).tolist()

    results = (
        table.search(query_vector)
        .metric("cosine")
        .limit(top_k)
        .to_list()
    )

    if not results:
        return {"error": "No relevant stories found."}

    response = []
    for result in results:
        story_id = result["storyID"]
        test_case_json = get_test_case_json_by_story_id(story_id)
        response.append({
            "story_id": story_id,
            "similarity_score": result["_distance"],
            "test_case_json": test_case_json or "[Test case not found]"
        })

    return response

if __name__ == "__main__":
    # Run RAG search on a sample query
    test_query = "What is the test case for login?"
    results = Chat_RAG(test_query)

    print("\n🎯 Results from Chat_RAG:")
    for res in results:
        print(f"\nStory ID: {res['story_id']}")
        print(f"Similarity Score: {res['similarity_score']:.4f}")
        print(f"Test Case JSON:\n{json.dumps(res['test_case_json'], indent=2)}\n")