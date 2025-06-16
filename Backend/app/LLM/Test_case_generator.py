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

load_dotenv()

# === CONFIGURATION ===
LANCE_DB_PATH = Config.LANCE_DB_PATH
TABLE_NAME = Config.TABLE_NAME_LANCE
TOP_K = 3
MAX_MAIN_TEXT_CHARS = 5000

# Load prompt
with open("Backend/app/LLM/test_case_prompt.txt", "r", encoding="utf-8") as f:
    INSTRUCTIONS = f.read()

# Connect to LanceDB
db = lancedb.connect(LANCE_DB_PATH)
table = db.open_table(TABLE_NAME)

def generate_test_case_for_story(story_id, table_ref=table, llm_ref=Config.llm):
    all_rows = table_ref.search().to_list()
    row = next((r for r in all_rows if r["storyID"] == story_id), None)

    if not row:
        print(f"❌ Story ID '{story_id}' not found in LanceDB.")
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
        table_ref.search(vector)
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
    generated_ids = set(get_all_generated_story_ids())
    records = [row for row in table.search().to_list() if row["storyID"] not in generated_ids]

    print(f"🟡 Found {len(records)} entries to process.\n")

    for row in records:
        generate_test_case_for_story(row["storyID"])

def Chat_RAG(user_query, table_ref=table, top_k=3):
    query_vector = Config.EMBEDDING_MODEL.encode(user_query).tolist()

    results = (
        table_ref.search(query_vector)
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