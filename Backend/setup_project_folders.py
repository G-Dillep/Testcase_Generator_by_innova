import os
import sys

# Add the Backend directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, backend_dir)

def setup_project_folders():
    """Create the proper folder structure for project-based processing"""
    
    # Define base directories
    base_dirs = [
        "./data/uploaded_docs",
        "./data/success", 
        "./data/failure",
        "./data/lance_db"
    ]
    
    print("🚀 Setting up project folder structure...")
    
    # Create base directories
    for dir_path in base_dirs:
        os.makedirs(dir_path, exist_ok=True)
        print(f"✅ Created: {dir_path}")
    
    # Create example project folders
    example_projects = ["Project1", "Project2", "Project3"]
    
    for project in example_projects:
        project_upload_path = os.path.join("./data/uploaded_docs", project)
        project_success_path = os.path.join("./data/success", project)
        project_failure_path = os.path.join("./data/failure", project)
        
        os.makedirs(project_upload_path, exist_ok=True)
        os.makedirs(project_success_path, exist_ok=True)
        os.makedirs(project_failure_path, exist_ok=True)
        
        print(f"✅ Created project folders for: {project}")
    
    # Create a README file in the upload folder
    readme_content = """# Project Upload Structure

This folder contains project folders. Each project folder should contain the documents (PDF, DOCX, TXT) for that specific project.

## Expected Structure:
```
./data/uploaded_docs/
├── Project1/
│   ├── story1.pdf
│   ├── story2.docx
│   └── story3.txt
├── Project2/
│   ├── user_story_1.pdf
│   └── requirement_2.docx
└── Project3/
    └── feature_spec.txt
```

## Processing:
- Files will be processed by project
- Success files moved to: ./data/success/{project_name}/
- Failed files moved to: ./data/failure/{project_name}/
- Project name becomes the project_id in the database

## Supported File Types:
- PDF (.pdf)
- Word documents (.docx)
- Text files (.txt)

## Notes:
- Each file should have a unique name (used as story_id)
- Project folder names should be descriptive
- Files will be processed automatically by the scheduler
"""
    
    readme_path = os.path.join("./data/uploaded_docs", "README.md")
    with open(readme_path, 'w') as f:
        f.write(readme_content)
    
    print(f"✅ Created: {readme_path}")
    
    print("\n📁 Folder structure created successfully!")
    print("\n📋 Next steps:")
    print("1. Place your project documents in the appropriate project folders")
    print("2. Run the scheduler: python Backend/scheduler.py")
    print("3. Or run manually: python Backend/app/datapipeline/embedding_generator.py")
    print("\n📁 Current structure:")
    print_tree("./data")

def print_tree(path, prefix="", max_depth=3, current_depth=0):
    """Print a tree structure of directories"""
    if current_depth >= max_depth:
        return
    
    try:
        items = os.listdir(path)
        items.sort()
        
        for i, item in enumerate(items):
            item_path = os.path.join(path, item)
            is_last = i == len(items) - 1
            
            if os.path.isdir(item_path):
                print(f"{prefix}{'└── ' if is_last else '├── '}{item}/")
                new_prefix = prefix + ('    ' if is_last else '│   ')
                print_tree(item_path, new_prefix, max_depth, current_depth + 1)
            else:
                print(f"{prefix}{'└── ' if is_last else '├── '}{item}")
    except PermissionError:
        print(f"{prefix}└── [Permission Denied]")

if __name__ == "__main__":
    setup_project_folders() 