import os
import re

path = "apps/backend/database.py"
with open(path, "r") as f:
    content = f.read()

# Make sure it defaults to 5437 and loads .env
content = content.replace("localhost:5435", "127.0.0.1:5437")

if "from dotenv import load_dotenv" not in content:
    content = "from dotenv import load_dotenv\nimport pathlib\nload_dotenv(pathlib.Path(__file__).parent / '.env')\n" + content

with open(path, "w") as f:
    f.write(content)
