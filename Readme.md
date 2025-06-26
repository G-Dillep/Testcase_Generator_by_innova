# Test Case Generator

A comprehensive test case generation system that processes user stories from Jira and uploaded documents to automatically generate test cases using LLM.

## 🏗️ Architecture

- **Backend**: Flask API with LanceDB (vector storage) and PostgreSQL (test case storage)
- **Frontend**: Next.js with TypeScript and Tailwind CSS
- **LLM Integration**: OpenAI GPT for test case generation
- **Jira Integration**: Fetches user stories and projects
- **Document Processing**: Supports PDF, DOCX, and TXT files

## 📁 Project Structure

```
Test-case-generator/
├── Backend/
│   ├── app/
│   │   ├── datapipeline/
│   │   │   ├── embedding_generator.py    # Project-based document processing
│   │   │   └── text_extractor.py         # Text extraction from documents
│   │   ├── LLM/
│   │   │   ├── Test_case_generator.py    # LLM test case generation
│   │   │   └── test_case_prompt.txt      # LLM prompts
│   │   ├── models/
│   │   │   ├── create_dbs.py             # Database setup
│   │   │   ├── db_service.py             # Database operations
│   │   │   └── postgress_writer.py       # PostgreSQL writer
│   │   ├── routes/
│   │   │   └── stories.py                # API endpoints
│   │   ├── services/
│   │   │   └── jira_integration.py       # Jira API integration
│   │   └── utils/
│   │       └── excel_util.py             # Excel utilities
│   ├── data/
│   │   ├── uploaded_docs/                # 📁 Project folders with documents
│   │   │   ├── Project1/                 # Each project folder contains documents
│   │   │   │   ├── story1.pdf
│   │   │   │   └── story2.docx
│   │   │   ├── Project2/
│   │   │   │   └── story3.txt
│   │   │   └── README.md                 # Upload structure guide
│   │   ├── success/                      # ✅ Successfully processed files
│   │   │   ├── Project1/
│   │   │   └── Project2/
│   │   ├── failure/                      # ❌ Failed processing files
│   │   │   ├── Project1/
│   │   │   └── Project2/
│   │   └── lance_db/                     # Vector database
│   ├── scheduler.py                      # Automated processing scheduler
│   ├── setup_project_folders.py          # Setup project structure
│   └── test_project_processing.py        # Test project processing
└── frontend/
    └── test-case-generator/              # Next.js frontend
```

## 🚀 Quick Start

### 1. Setup Project Structure

```bash
# Create the proper folder structure
python Backend/setup_project_folders.py
```

### 2. Install Dependencies

```bash
# Backend dependencies
cd Backend
pip install -r requirements.txt

# Frontend dependencies
cd frontend/test-case-generator
npm install
```

### 3. Configure Environment Variables

Create `.env` files in both Backend and frontend directories:

**Backend/.env:**
```env
OPENAI_API_KEY=your_openai_api_key
JIRA_URL=your_jira_url
JIRA_USERNAME=your_jira_username
JIRA_API_TOKEN=your_jira_api_token
POSTGRES_URL=your_postgres_connection_string
```

**Frontend/.env.local:**
```env
NEXT_PUBLIC_API_URL=http://localhost:5000
```

### 4. Setup Databases

```bash
cd Backend
python app/models/create_dbs.py
```

### 5. Upload Documents

Place your documents in project folders:

```
Backend/data/uploaded_docs/
├── ECommerce/
│   ├── user_login_story.pdf
│   └── checkout_process.docx
├── BankingApp/
│   ├── account_creation.txt
│   └── money_transfer.pdf
└── Healthcare/
    └── patient_registration.docx
```

### 6. Run the System

```bash
# Terminal 1: Start the scheduler (processes documents automatically)
cd Backend
python scheduler.py

# Terminal 2: Start the Flask backend
cd Backend
python run.py

# Terminal 3: Start the Next.js frontend
cd frontend/test-case-generator
npm run dev
```

## 📋 Workflow

### Document Processing Pipeline

1. **Upload**: Documents are placed in project folders under `Backend/data/uploaded_docs/`
2. **Processing**: The scheduler processes each project folder:
   - Extracts text from documents (PDF, DOCX, TXT)
   - Generates embeddings using sentence-transformers
   - Stores in LanceDB with project_id
   - Moves files to success/failure folders by project
3. **Test Generation**: LLM generates test cases for processed stories
4. **Storage**: Test cases stored in PostgreSQL with project filtering

### Jira Integration

- Fetches user stories from configured Jira projects
- Supports project-based filtering
- Automatic test case generation for Jira stories

## 🧪 Testing

### Create Test Files

```bash
# Create sample project files for testing
python Backend/test_project_processing.py --create

# Run the embedding generator
python Backend/app/datapipeline/embedding_generator.py

# Clean up test files
python Backend/test_project_processing.py --clean
```

## 🔧 Configuration

### Project-Based Processing

The system now supports project-based document processing:

- **Project Folders**: Each project has its own folder in `uploaded_docs/`
- **Project ID**: Folder name becomes the project_id in databases
- **Success/Failure Tracking**: Files moved to project-specific success/failure folders
- **Frontend Filtering**: Filter test cases by project in the UI

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `UPLOAD_FOLDER` | Documents upload directory | `./data/uploaded_docs` |
| `SUCCESS_FOLDER` | Successfully processed files | `./data/success` |
| `FAILURE_FOLDER` | Failed processing files | `./data/failure` |
| `LANCE_DB_PATH` | LanceDB database path | `./data/lance_db` |

## 📊 Features

- ✅ **Project-based document processing**
- ✅ **Automatic text extraction** (PDF, DOCX, TXT)
- ✅ **Vector embeddings** with LanceDB
- ✅ **LLM test case generation**
- ✅ **Jira integration** with project filtering
- ✅ **PostgreSQL storage** with project support
- ✅ **Frontend filtering** by project
- ✅ **Automated scheduling** (every 5 minutes)
- ✅ **Success/failure tracking** by project
- ✅ **Excel export** functionality

## 🔄 API Endpoints

- `GET /api/stories` - Get all user stories with project filtering
- `GET /api/stories/{story_id}` - Get specific story with test cases
- `GET /api/projects` - Get list of available projects
- `POST /api/generate-test-cases` - Generate test cases for a story

## 🛠️ Development

### Adding New Document Types

1. Update `text_extractor.py` to support new file formats
2. Add file extension handling in `embedding_generator.py`

### Adding New LLM Providers

1. Update `config.py` with new LLM configuration
2. Modify `Test_case_generator.py` to use new provider

### Customizing Test Case Prompts

Edit `Backend/app/LLM/test_case_prompt.txt` to modify the LLM prompts for test case generation.

## 📝 Notes

- Each document filename becomes the story_id
- Project folder names should be descriptive and unique
- The scheduler runs every 5 minutes by default
- Files are automatically moved to success/failure folders after processing
- Project ID is preserved throughout the entire pipeline





this is my env


JIRA_BASE_URL=https://team-delta-innovasolutions.atlassian.net/
JIRA_EMAIL=kaushik24062004@gmail.com
JIRA_API_TOKEN=ATATT3xFfGF0a4KtL9RUftnvMUUAY3JaXH37_pl71TR9i-gOjycj7NoIfmZdVY0N3e3fQJFXZz7FlHToV70yHh8H_Vjpqk5-8ylbzNp6n8LgpK0JsVQTXFFvnvCgU-u_jEwHLQNpfx5os07dRQD2BZ9WLqiBJypvAMQ-yhICh_jQmWrk-fXVbO8=86642574
JIRA_PROJECT_KEY=TIS
JIRA_MAX_RESULTS=100
JIRA_BATCH_SIZE=50
JIRA_RATE_LIMIT_DELAY=1.0
JIRA_RETRY_ATTEMPTS=3
JIRA_RETRY_BACKOFF_FACTOR=2.0
JIRA_SYNC_ALL_PROJECTS=false
