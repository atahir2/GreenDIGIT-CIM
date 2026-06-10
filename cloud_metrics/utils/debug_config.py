# debug_config.py - Run this to debug your configuration issue

import os
from pathlib import Path

print("=== DEBUGGING PYDANTIC SETTINGS ===")

# 1. Check current working directory
print(f"Current working directory: {os.getcwd()}")

# 2. Check where this script is located
script_location = Path(__file__).parent
print(f"Script location: {script_location.absolute()}")

# 3. Check for .env file in various locations
possible_env_locations = [
    Path.cwd() / ".env",  # Current working directory
    script_location / ".env",  # Same directory as this script
    script_location.parent / ".env",  # Parent directory
    script_location.parent.parent / ".env",  # Grandparent directory
    Path("Z:/GreenDIGIT_CIM_testing_v1/.env"),  # Your project root
]

print("\n=== CHECKING FOR .env FILES ===")
for env_path in possible_env_locations:
    if env_path.exists():
        print(f"✓ FOUND .env at: {env_path.absolute()}")
        try:
            with open(env_path, 'r') as f:
                content = f.read()
                print(f"Content preview (first 200 chars):\n{content[:200]}...")
        except Exception as e:
            print(f"Error reading file: {e}")
    else:
        print(f"✗ NOT FOUND: {env_path.absolute()}")

# 4. Check environment variables
print("\n=== ENVIRONMENT VARIABLES ===")
database_url_env = os.getenv('DATABASE_URL')
print(f"DATABASE_URL from os.environ: {database_url_env}")

# List all env vars that might be related
print("\nAll environment variables containing 'DATABASE' or 'URL':")
for key, value in os.environ.items():
    if 'DATABASE' in key.upper() or 'URL' in key.upper():
        print(f"  {key} = {value}")

# 5. Try creating a minimal .env file
print("\n=== CREATING TEST .env FILE ===")
test_env_path = Path.cwd() / ".env"
if not test_env_path.exists():
    try:
        with open(test_env_path, 'w') as f:
            f.write("DATABASE_URL=sqlite:///./test.db\n")
        print(f"✓ Created test .env file at: {test_env_path.absolute()}")
    except Exception as e:
        print(f"✗ Failed to create .env file: {e}")
else:
    print(f"✓ .env file already exists at: {test_env_path.absolute()}")

print("\n=== TESTING PYDANTIC SETTINGS ===")

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict


    class TestDBSettings(BaseSettings):
        model_config = SettingsConfigDict(env_file=".env", extra="ignore")
        DATABASE_URL: str = "postgresql:///./default.db"  # with default


    test_settings = TestDBSettings()
    print(f"✓ SUCCESS! DATABASE_URL loaded: {test_settings.DATABASE_URL}")

except Exception as e:
    print(f"✗ FAILED to load settings: {e}")
    print(f"Error type: {type(e).__name__}")

print("\n=== TESTING MANUAL ENV LOADING ===")
try:
    from dotenv import load_dotenv

    load_result = load_dotenv()
    print(f"dotenv load_dotenv() result: {load_result}")
    print(f"DATABASE_URL after dotenv: {os.getenv('DATABASE_URL')}")
except ImportError:
    print("python-dotenv not installed")
except Exception as e:
    print(f"Error with dotenv: {e}")