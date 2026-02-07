"""
Configuration management for Nativity.ai
Loads environment variables for API keys and AWS settings
"""

import os
from pathlib import Path
from dotenv import load_dotenv

print("=" * 50)
print("🔧 NATIVITY.AI CONFIG INITIALIZATION")
print("=" * 50)

# Get the directory where this config file lives
config_dir = Path(__file__).resolve().parent
print(f"DEBUG: Config file location: {config_dir}")

# Define all possible .env locations to try
env_paths_to_try = [
    config_dir / '.env',                    # backend/.env
    config_dir.parent / '.env',             # project root (one level up from backend)
    config_dir.parent.parent / '.env',      # two levels up
    Path.cwd() / '.env',                    # current working directory
]

# 1. First, try default load_dotenv (checks CWD)
load_dotenv()
print(f"DEBUG: Current working directory: {Path.cwd()}")

# 2. Try each path explicitly
env_loaded = False
for env_path in env_paths_to_try:
    abs_path = env_path.resolve()
    print(f"DEBUG: Checking: {abs_path}")
    
    if abs_path.exists():
        print(f"✅ Found .env at: {abs_path}")
        
        # Read file to verify it's readable
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = [l for l in content.split('\n') if l.strip() and not l.strip().startswith('#')]
                print(f"DEBUG: .env has {len(lines)} non-empty, non-comment lines")
        except Exception as e:
            print(f"⚠️  WARNING: Could not read .env: {e}")
        
        # Load with string path (more compatible)
        load_dotenv(dotenv_path=str(abs_path), override=True)
        env_loaded = True
        break

if not env_loaded:
    print("❌ Could not find .env file in any expected location!")
    print("   Expected locations:")
    for p in env_paths_to_try:
        print(f"     - {p.resolve()}")

print("-" * 50)

# Verify critical keys loaded
if not os.getenv("GOOGLE_API_KEY"):
    print("⚠️  CRITICAL: GOOGLE_API_KEY is missing even after loading .env")
else:
    print(f"✅ GOOGLE_API_KEY loaded (length: {len(os.getenv('GOOGLE_API_KEY'))})")

if not os.getenv("AWS_ACCESS_KEY_ID"):
    print("⚠️  CRITICAL: AWS_ACCESS_KEY_ID is missing")
else:
    print(f"✅ AWS_ACCESS_KEY_ID loaded (starts with: {os.getenv('AWS_ACCESS_KEY_ID')[:4]}...)")

if not os.getenv("S3_BUCKET_NAME"):
    print("⚠️  CRITICAL: S3_BUCKET_NAME is missing")
else:
    print(f"✅ S3_BUCKET_NAME loaded: {os.getenv('S3_BUCKET_NAME')}")

print("=" * 50)


class Settings:
    """Application settings loaded from environment variables"""
    
    # Google Gemini API
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    
    # AWS Configuration
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "eu-north-1")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "")
    
    # Application Settings
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "./outputs")
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "500"))
    
    # Supported Languages
    SUPPORTED_LANGUAGES: list = ["hindi", "tamil", "bengali", "telugu", "marathi"]
    
    # Clerk Authentication
    CLERK_ISSUER_URL: str = os.getenv("CLERK_ISSUER_URL", "")
    
    def validate(self) -> dict:
        """Validate that required settings are configured"""
        issues = []
        if not self.GOOGLE_API_KEY:
            issues.append("GOOGLE_API_KEY is not set")
        if not self.AWS_ACCESS_KEY_ID:
            issues.append("AWS_ACCESS_KEY_ID is not set")
        if not self.S3_BUCKET_NAME:
            issues.append("S3_BUCKET_NAME is not set")
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }


settings = Settings()
