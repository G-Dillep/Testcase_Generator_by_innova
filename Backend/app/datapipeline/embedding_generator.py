from app.config import llm, EMBEDDING_MODEL, Config
import os
import shutil
from app.datapipeline.text_extractor import extract_text
from app.models.create_dbs import create_LanceDB
import lancedb
from datetime import datetime

UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "./data/uploaded_docs")
SUCCESS_FOLDER = os.getenv("SUCCESS_FOLDER", "./data/success")
FAILURE_FOLDER = os.getenv("FAILURE_FOLDER", "./data/failure")
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

def ensure_project_folders(project_name):
    """Ensure success and failure folders exist for the project"""
    project_success_folder = os.path.join(SUCCESS_FOLDER, project_name)
    project_failure_folder = os.path.join(FAILURE_FOLDER, project_name)
    
    # Create project folders if they don't exist
    os.makedirs(project_success_folder, exist_ok=True)
    os.makedirs(project_failure_folder, exist_ok=True)
    
    return project_success_folder, project_failure_folder

def process_project_folder(project_folder_path, project_name):
    """Process all files in a project folder"""
    files_processed = 0
    files_success = 0
    files_failed = 0
    
    print(f"📁 Processing project: {project_name}")
    
    # Ensure project-specific success/failure folders
    project_success_folder, project_failure_folder = ensure_project_folders(project_name)
    
    # Get all files in the project folder
    try:
        files = [f for f in os.listdir(project_folder_path) if os.path.isfile(os.path.join(project_folder_path, f))]
    except Exception as e:
        print(f"❌ Error reading project folder {project_name}: {e}")
        return 0, 0, 0
    
    for file in files:
        file_path = os.path.join(project_folder_path, file)
        files_processed += 1
        
        print(f"📄 Processing {file} in project {project_name}...")

        text = extract_text(file_path)

        if not text:
            print(f"❌ Skipping {file} — couldn't extract text.")
            shutil.move(file_path, os.path.join(project_failure_folder, file))
            files_failed += 1
            continue

        try:
            story_id = os.path.splitext(file)[0]

            if story_id_exists(table, story_id):
                print(f"⚠️ Skipping {file} — storyID '{story_id}' already exists.")
                shutil.move(file_path, os.path.join(project_failure_folder, file))
                files_failed += 1
                continue

            story_description = summarize_in_chunks(text)

            try:
                embedding = EMBEDDING_MODEL.encode(text).tolist()
            except Exception as e:
                print(f"❌ Embedding generation failed for {file}: {e}")
                shutil.move(file_path, os.path.join(project_failure_folder, file))
                files_failed += 1
                continue

            print(f"🔢 Vector length: {len(embedding)} for {file}")

            table.add([{
                "project_id": project_name,
                "vector": embedding,
                "storyID": story_id,
                "storyDescription": story_description,
                "test_case_content": "",
                "filename": file,
                "original_path": file_path,
                "doc_content_text": text,
                "embedding_timestamp": datetime.now(),
                "source": "file"
            }])

            shutil.move(file_path, os.path.join(project_success_folder, file))
            print(f"✅ Stored {file} in LanceDB and moved to {project_name}/success.")
            files_success += 1
        except Exception as e:
            print(f"❌ Error storing {file}: {e}")
            shutil.move(file_path, os.path.join(project_failure_folder, file))
            files_failed += 1
    
    print(f"📊 [Project {project_name}] Summary: {files_processed} files processed, {files_success} successful, {files_failed} failed")
    return files_processed, files_success, files_failed

def generate_embeddings():
    """Process all project folders in the upload directory"""
    total_files_processed = 0
    total_files_success = 0
    total_files_failed = 0
    projects_processed = 0
    
    print(f"🔍 Scanning upload folder: {UPLOAD_FOLDER}")
    
    # Ensure base success and failure folders exist
    os.makedirs(SUCCESS_FOLDER, exist_ok=True)
    os.makedirs(FAILURE_FOLDER, exist_ok=True)
    
    try:
        # Get all project folders in the upload directory
        project_folders = [f for f in os.listdir(UPLOAD_FOLDER) 
                          if os.path.isdir(os.path.join(UPLOAD_FOLDER, f))]
        
        if not project_folders:
            print("⚠️ No project folders found in upload directory")
            print(f"📁 Expected structure: {UPLOAD_FOLDER}/")
            print("   ├── Project1/")
            print("   │   ├── story1.pdf")
            print("   │   └── story2.docx")
            print("   ├── Project2/")
            print("   │   └── story3.txt")
            print("   └── ...")
            return
        
        print(f"📁 Found {len(project_folders)} project folders: {', '.join(project_folders)}")
        
        for project_folder in project_folders:
            project_path = os.path.join(UPLOAD_FOLDER, project_folder)
            
            # Process each project folder
            files_processed, files_success, files_failed = process_project_folder(project_path, project_folder)
            
            total_files_processed += files_processed
            total_files_success += files_success
            total_files_failed += files_failed
            projects_processed += 1
            
            print(f"✅ Completed project: {project_folder}")
            print("-" * 50)
        
        print(f"🎉 [Overall Summary] {projects_processed} projects processed")
        print(f"📊 Total files: {total_files_processed} processed, {total_files_success} successful, {total_files_failed} failed")
        
        if total_files_success > 0:
            print(f"🎉 {total_files_success} new stories added to LanceDB and ready for test case generation!")
        
        # Show folder structure
        print(f"\n📁 Success folders created:")
        for project in project_folders:
            print(f"   ✅ {SUCCESS_FOLDER}/{project}/")
        
        print(f"\n📁 Failure folders created:")
        for project in project_folders:
            print(f"   ❌ {FAILURE_FOLDER}/{project}/")
            
    except Exception as e:
        print(f"❌ Error processing upload folder: {e}")

if __name__ == "__main__":
    generate_embeddings()