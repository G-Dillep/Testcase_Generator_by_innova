from app.config import llm, EMBEDDING_MODEL, Config
import os
import shutil
from app.datapipeline.text_extractor import extract_text
from app.models.create_dbs import create_LanceDB
import lancedb
from datetime import datetime

UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER")
SUCCESS_FOLDER = os.getenv("SUCCESS_FOLDER")
FAILURE_FOLDER = os.getenv("FAILURE_FOLDER")
db = lancedb.connect(Config.LANCE_DB_PATH)

try:
    table=db.open_table(Config.TABLE_NAME_LANCE)
except Exception as e:
    print(f"❌ Error opening table: {e}")
    table=create_LanceDB()

def summarize_in_chunks(text, chunk_size=4000):
    try:
        chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
        summaries = []
        for chunk in chunks[:3]:  # Limit to 3 chunks for efficiency
            prompt = (
                "Summarize the following document section in 1 sentence:\n\n" + chunk
            )
            try:
                response = llm.invoke(prompt)
                summaries.append(response.content.strip())
            except Exception as e:
                summaries.append("[Summary failed for a chunk]")
                print(f"❌ LLM failed on a chunk: {e}")
        return " ".join(summaries)
    except Exception as e:
        print(f"❌ LLM summary failed: {e}")
        return "Summary could not be generated."
    
def story_id_exists(table, story_id):
    try:
        result = table.to_pandas().query(f"storyID == '{story_id}'")
        return not result.empty
    except Exception:
        return False

def generate_embeddings():
    files_processed = 0
    files_success = 0
    files_failed = 0
    
    for file in os.listdir(UPLOAD_FOLDER):
        file_path = os.path.join(UPLOAD_FOLDER, file)

        if os.path.isdir(file_path):
            continue

        files_processed += 1
        print(f"📄 Processing {file}...")

        text = extract_text(file_path)

        if not text:
            print(f"❌ Skipping {file} — couldn't extract text.")
            shutil.move(file_path, os.path.join(FAILURE_FOLDER, file))
            files_failed += 1
            continue

        try:
            story_id = os.path.splitext(file)[0]

            if story_id_exists(table, story_id):
                print(f"⚠️ Skipping {file} — storyID '{story_id}' already exists.")
                shutil.move(file_path, os.path.join(FAILURE_FOLDER, file))
                files_failed += 1
                continue

            story_description = summarize_in_chunks(text)

            try:
                embedding = EMBEDDING_MODEL.encode(text).tolist()
            except Exception as e:
                print(f"❌ Embedding generation failed for {file}: {e}")
                shutil.move(file_path, os.path.join(FAILURE_FOLDER, file))
                files_failed += 1
                continue

            print(f"🔢 Vector length: {len(embedding)} for {file}")

            table.add([{
                "vector": embedding,
                "storyID": story_id,
                "storyDescription": story_description,
                "test_case_content": "",
                "filename": file,
                "original_path": file_path,
                "doc_content_text": text,
                "embedding_timestamp": datetime.now().isoformat()
            }])

            shutil.move(file_path, os.path.join(SUCCESS_FOLDER, file))
            print(f"✅ Stored {file} in LanceDB and moved to success.")
            files_success += 1
        except Exception as e:
            print(f"❌ Error storing {file}: {e}")
            shutil.move(file_path, os.path.join(FAILURE_FOLDER, file))
            files_failed += 1
    
    print(f"📊 [Embedding Generation] Summary: {files_processed} files processed, {files_success} successful, {files_failed} failed")
    
    if files_success > 0:
        print(f"🎉 {files_success} new stories added to LanceDB and ready for test case generation!")

if __name__ == "__main__":
    generate_embeddings()