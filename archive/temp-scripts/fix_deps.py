import os

path = "apps/backend/dependencies.py"
with open(path, "r") as f:
    content = f.read()

# Fix the internal session.exec error
if "session.exec" in content:
    content = content.replace("session.exec", "session.execute")

with open(path, "w") as f:
    f.write(content)
