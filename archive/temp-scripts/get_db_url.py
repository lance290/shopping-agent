import os
from dotenv import load_dotenv

load_dotenv("apps/backend/.env")
print("URL:", os.environ.get("DATABASE_URL"))
