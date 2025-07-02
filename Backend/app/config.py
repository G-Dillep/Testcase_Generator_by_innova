import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from langchain_google_genai import ChatGoogleGenerativeAI
import psycopg2

load_dotenv()

EMBEDDING_MODEL = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

llm = ChatGoogleGenerativeAI(
    model="models/gemini-2.0-flash",
    temperature=0.3,
    google_api_key=os.environ["GOOGLE_API_KEY"]
)

class Config:
    # Database configurations
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'test_case_generator')
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'admin')
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
    
    LANCE_DB_PATH = os.getenv('LANCE_DB_PATH', './data/lance_db')
    TABLE_NAME_LANCE = os.getenv('TABLE_NAME_LANCE', 'user_stories')
    EMBEDDING_MODEL = EMBEDDING_MODEL

    # Original LLM instance
    llm = llm

    # Additional LLM for impact analysis
    llm_impact = ChatGoogleGenerativeAI(
        model="models/gemini-2.0-flash",
        temperature=0.3,
        google_api_key=os.environ.get("GOOGLE_API_KEY_IMPACT", os.environ["GOOGLE_API_KEY"])
    )

    # Test case generation configuration
    TEST_CASE_COUNTS = {
        "positive": int(os.getenv('TEST_CASE_COUNT_POSITIVE', '50')),  # Core functionality, happy paths
        "negative": int(os.getenv('TEST_CASE_COUNT_NEGATIVE', '30')),   # Error handling, invalid inputs
        "boundary": int(os.getenv('TEST_CASE_COUNT_BOUNDARY', '10')),   # Edge cases, limits
        "security": int(os.getenv('TEST_CASE_COUNT_SECURITY', '10')),   # Security tests
        "performance": int(os.getenv('TEST_CASE_COUNT_PERFORMANCE', '10'))  # Performance tests
    }
    
    @classmethod
    def get_postgres_connection(cls):
        return psycopg2.connect(
            dbname=cls.POSTGRES_DB,
            user=cls.POSTGRES_USER,
            password=cls.POSTGRES_PASSWORD,
            host=cls.POSTGRES_HOST,
            port=cls.POSTGRES_PORT
        )
    
    @classmethod
    def postgres_config(cls):
        return {
            'dbname': cls.POSTGRES_DB,
            'user': cls.POSTGRES_USER,
            'password': cls.POSTGRES_PASSWORD,
            'host': cls.POSTGRES_HOST,
            'port': cls.POSTGRES_PORT
        }

class DevelopmentConfig(Config):
    pass

class ProductionConfig(Config):
    pass

class TestingConfig(Config):
    TESTING = True
    POSTGRES_DB = 'test_db'
    LANCE_DB_PATH = './data/test_lance_db'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 