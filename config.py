import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # SQLite database file
    DATABASE_PATH = 'cineScope.db'
    
    # OMDB API Key
    OMDB_API_KEY = os.getenv('OMDB_API_KEY')
    
    # OpenRouter AI API Key
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    
    # OpenRouter Model (default: gpt-3.5-turbo, but can use others like claude, gemini, etc.)
    OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'openai/gpt-3.5-turbo')
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-123')
    
    @property
    def is_omdb_configured(self):
        return self.OMDB_API_KEY and self.OMDB_API_KEY != 'your_actual_api_key_here'
    
    @property
    def is_openrouter_configured(self):
        return self.OPENROUTER_API_KEY and self.OPENROUTER_API_KEY != 'your_openrouter_api_key_here'